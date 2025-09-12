# code_review_assistant/tools.py
"""
Production-ready tools for the Code Review Assistant.

These tools provide safe code analysis, style checking, test generation,
and feedback management capabilities using ADK's built-in code executor.
"""
import ast
import asyncio
import hashlib
import json
import os
import pycodestyle
import tempfile
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

from google.adk.tools import ToolContext, FunctionTool
from code_review_assistant.constants import StateKeys

# Configure logging
logger = logging.getLogger(__name__)


async def analyze_code_structure(code: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Analyzes Python code structure using AST parsing.

    This tool parses Python code to extract structural information
    including functions, classes, imports, and complexity metrics.

    Args:
        code: Python source code to analyze
        tool_context: ADK tool context for state management

    Returns:
        Dictionary containing analysis results and status
    """
    logger.info("Tool: Analyzing code structure...")

    try:
        # Validate input
        if not code or not isinstance(code, str):
            return {
                "status": "error",
                "message": "No code provided or invalid input"
            }

        # Store the original code in state for other agents
        tool_context.state[StateKeys.CODE_TO_REVIEW] = code
        tool_context.state[StateKeys.CODE_LINE_COUNT] = len(code.splitlines())

        # Use thread pool for CPU-bound AST parsing
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            # Parse the code into an AST
            tree = await loop.run_in_executor(executor, ast.parse, code)

            # Extract structural information in thread pool
            analysis = await loop.run_in_executor(
                executor, _extract_code_structure, tree, code
            )

        # Store analysis in state
        tool_context.state[StateKeys.CODE_ANALYSIS] = analysis
        tool_context.state[StateKeys.TEMP_ANALYSIS_TIMESTAMP] = datetime.now().isoformat()

        logger.info(f"Tool: Analysis complete - {analysis['metrics']['function_count']} functions, "
                    f"{analysis['metrics']['class_count']} classes")

        return {
            "status": "success",
            "analysis": analysis,
            "summary": f"Found {analysis['metrics']['function_count']} functions and "
                       f"{analysis['metrics']['class_count']} classes"
        }

    except SyntaxError as e:
        error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
        logger.error(f"Tool: {error_msg}")
        tool_context.state[StateKeys.SYNTAX_ERROR] = error_msg

        return {
            "status": "error",
            "error_type": "syntax",
            "message": error_msg,
            "line": e.lineno,
            "offset": e.offset
        }
    except Exception as e:
        error_msg = f"Analysis failed: {str(e)}"
        logger.error(f"Tool: {error_msg}", exc_info=True)

        return {
            "status": "error",
            "error_type": "parse",
            "message": error_msg
        }


def _extract_code_structure(tree: ast.AST, code: str) -> Dict[str, Any]:
    """
    Helper function to extract structural information from AST.
    Runs in thread pool for CPU-bound work.
    """
    functions = []
    classes = []
    imports = []
    docstrings = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_info = {
                'name': node.name,
                'args': [arg.arg for arg in node.args.args],
                'lineno': node.lineno,
                'has_docstring': ast.get_docstring(node) is not None,
                'is_async': isinstance(node, ast.AsyncFunctionDef),
                'decorators': [d.id for d in node.decorator_list
                               if isinstance(d, ast.Name)]
            }
            functions.append(func_info)

            if func_info['has_docstring']:
                docstrings.append(f"{node.name}: {ast.get_docstring(node)[:50]}...")

        elif isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(item.name)

            class_info = {
                'name': node.name,
                'lineno': node.lineno,
                'methods': methods,
                'has_docstring': ast.get_docstring(node) is not None,
                'base_classes': [base.id for base in node.bases
                                 if isinstance(base, ast.Name)]
            }
            classes.append(class_info)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    'module': alias.name,
                    'alias': alias.asname,
                    'type': 'import'
                })
        elif isinstance(node, ast.ImportFrom):
            imports.append({
                'module': node.module or '',
                'names': [alias.name for alias in node.names],
                'type': 'from_import',
                'level': node.level
            })

    return {
        'functions': functions,
        'classes': classes,
        'imports': imports,
        'docstrings': docstrings,
        'metrics': {
            'line_count': len(code.splitlines()),
            'function_count': len(functions),
            'class_count': len(classes),
            'import_count': len(imports),
            'has_main': any(f['name'] == 'main' for f in functions),
            'has_if_main': '__main__' in code,
            'avg_function_length': _calculate_avg_function_length(tree)
        }
    }


async def check_code_style(code: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Checks code style compliance using pycodestyle (PEP 8).

    Args:
        code: Python source code to check (or will retrieve from state)
        tool_context: ADK tool context

    Returns:
        Dictionary containing style score and issues
    """
    logger.info("Tool: Checking code style...")

    try:
        # Retrieve code from state if not provided
        if not code:
            code = tool_context.state.get(StateKeys.CODE_TO_REVIEW, '')
            if not code:
                return {
                    "status": "error",
                    "message": "No code provided or found in state"
                }

        # Run style check in thread pool
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor, _perform_style_check, code
            )

        # Store results in state
        tool_context.state[StateKeys.STYLE_SCORE] = result['score']
        tool_context.state[StateKeys.STYLE_ISSUES] = result['issues']
        tool_context.state[StateKeys.STYLE_ISSUE_COUNT] = result['issue_count']

        logger.info(f"Tool: Style check complete - Score: {result['score']}/100, "
                    f"Issues: {result['issue_count']}")

        return result

    except Exception as e:
        error_msg = f"Style check failed: {str(e)}"
        logger.error(f"Tool: {error_msg}", exc_info=True)

        # Set default values on error
        tool_context.state[StateKeys.STYLE_SCORE] = 0
        tool_context.state[StateKeys.STYLE_ISSUES] = []

        return {
            "status": "error",
            "message": error_msg,
            "score": 0
        }


def _perform_style_check(code: str) -> Dict[str, Any]:
    """
    Helper to perform style check in thread pool.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        # Configure style guide (slightly more lenient for educational purposes)
        style_guide = pycodestyle.StyleGuide(
            quiet=True,
            max_line_length=100,
            ignore=['E501', 'W503']  # Ignore line length and line break before binary operator
        )

        # Check the file
        result = style_guide.check_files([tmp_path])

        # Parse results
        issues = []
        checker = pycodestyle.Checker(tmp_path, file_contents=code)
        checker.check_all()

        for error in checker.results:
            if isinstance(error, tuple) and len(error) >= 4:
                issues.append({
                    'line': error[0],
                    'column': error[1],
                    'code': error[2],
                    'message': error[3]
                })

        # Calculate style score
        base_score = 100
        deduction_per_issue = 3
        score = max(0, base_score - (len(issues) * deduction_per_issue))

        return {
            "status": "success",
            "score": score,
            "issue_count": len(issues),
            "issues": issues[:10],  # Return first 10 issues
            "summary": f"Style score: {score}/100 with {len(issues)} violations"
        }

    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


async def generate_and_run_tests(code: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Generates test code for the agent's built-in code executor to run.

    This function generates executable test code that the test_runner_agent
    will execute using its BuiltInCodeExecutor. The test code includes
    the original functions and test cases that output JSON results.

    Args:
        code: Python source code to test (or retrieves from state)
        tool_context: ADK tool context

    Returns:
        Dictionary indicating test code generation status
    """
    logger.info("Tool: Generating test code for executor...")

    try:
        # Retrieve code and analysis from state
        if not code:
            code = tool_context.state.get(StateKeys.CODE_TO_REVIEW, '')
            if not code:
                return {
                    "status": "error",
                    "message": "No code found to test"
                }

        analysis = tool_context.state.get(StateKeys.CODE_ANALYSIS, {})
        functions = analysis.get('functions', [])

        if not functions:
            logger.info("Tool: No functions found to test")
            # Store empty test results
            tool_context.state[StateKeys.TEST_RESULTS] = {
                'passed': 0,
                'failed': 0,
                'total': 0
            }
            tool_context.state[StateKeys.TEMP_TEST_CODE] = "print('No functions to test')"

            return {
                "status": "success",
                "message": "No functions found to test",
                "functions_to_test": 0,
                "test_code_generated": True
            }

        # Generate executable test code
        test_code = _generate_executable_test_code(code, functions)

        # Store test code for the agent to execute
        tool_context.state[StateKeys.TEMP_TEST_CODE] = test_code
        tool_context.state[StateKeys.TEMP_TEST_GENERATION_COMPLETE] = True
        tool_context.state[StateKeys.TEMP_FUNCTIONS_TO_TEST] = len([f for f in functions
                                                            if not f['name'].startswith('_')
                                                            and f['name'] != 'main'])

        logger.info(f"Tool: Generated test code for {len(functions)} functions")

        return {
            "status": "success",
            "message": "Test code generated successfully. Agent will execute using code executor.",
            "functions_to_test": len(functions),
            "test_code_generated": True,
            "test_code_length": len(test_code)
        }

    except Exception as e:
        error_msg = f"Test generation failed: {str(e)}"
        logger.error(f"Tool: {error_msg}", exc_info=True)

        tool_context.state[StateKeys.TEST_RESULTS] = {
            'passed': 0,
            'failed': 0,
            'total': 0,
            'error': error_msg
        }

        return {
            "status": "error",
            "message": error_msg,
            "test_code_generated": False
        }


def _generate_executable_test_code(code: str, functions: List[Dict]) -> str:
    """
    Generate complete executable test code for the built-in code executor.

    Creates a standalone Python script that:
    1. Defines all the original functions
    2. Runs test cases for each function
    3. Outputs results as JSON
    """
    test_lines = [
        "# Automated test execution for code review",
        "import json",
        "import sys",
        "import traceback",
        "",
        "# Initialize test results",
        "test_results = []",
        "execution_errors = []",
        "",
        "# Define the code to test",
        code,
        "",
        "# Test each function",
    ]

    tested_count = 0
    for func in functions:
        func_name = func['name']
        args = func['args']

        # Skip private functions and main
        if func_name.startswith('_') or func_name == 'main':
            continue

        tested_count += 1

        # Generate test cases based on function signature
        test_cases = _generate_test_cases(func_name, args)

        test_lines.append(f"\n# Testing function: {func_name}")
        test_lines.append(f"print('Testing {func_name}...', file=sys.stderr)")

        for i, test_case in enumerate(test_cases):
            test_lines.append(f"""
# Test case {i + 1} for {func_name}: {test_case.get('description', 'Test')}
try:
    test_input = {test_case['input']}
    result = {func_name}(*test_input)
    expected = {repr(test_case.get('expected', 'check_execution'))}

    if expected == 'check_execution':
        # Just verify it executes without error
        test_results.append({{
            'function': '{func_name}',
            'case': {i + 1},
            'passed': True,
            'result': str(result)[:100],  # Truncate long results
            'input': str(test_input),
            'execution_only': True,
            'description': '{test_case.get('description', 'Test')}'
        }})
    else:
        # Check if result matches expected
        passed = result == expected
        test_results.append({{
            'function': '{func_name}',
            'case': {i + 1},
            'passed': passed,
            'result': str(result),
            'expected': str(expected),
            'input': str(test_input),
            'description': '{test_case.get('description', 'Test')}'
        }})
except Exception as e:
    test_results.append({{
        'function': '{func_name}',
        'case': {i + 1},
        'passed': False,
        'error': str(e),
        'error_type': type(e).__name__,
        'input': str({test_case['input']}),
        'description': '{test_case.get('description', 'Test')}'
    }})
    execution_errors.append(f"{func_name} test {i + 1}: {{str(e)}}")
""")

    # Add summary calculation and output
    test_lines.append("""
# Calculate summary
passed = sum(1 for r in test_results if r.get('passed', False))
failed = sum(1 for r in test_results if not r.get('passed', False))
total = len(test_results)

# Create output structure
output = {
    'passed': passed,
    'failed': failed,
    'total': total,
    'pass_rate': (passed / total * 100) if total > 0 else 100,
    'details': test_results[:10],  # First 10 results for feedback
    'execution_errors': execution_errors[:5] if execution_errors else []
}

# Output as JSON (this will be captured by the code executor)
print(json.dumps(output, indent=2))
""")

    return '\n'.join(test_lines)


def _generate_test_cases(func_name: str, args: List[str]) -> List[Dict[str, Any]]:
    """
    Generate appropriate test cases based on function name and signature.
    """
    test_cases = []
    func_lower = func_name.lower()

    # Mathematical functions
    if 'add' in func_lower or 'sum' in func_lower:
        test_cases = [
            {'input': [2, 3], 'expected': 5, 'description': 'Basic addition'},
            {'input': [0, 0], 'expected': 0, 'description': 'Adding zeros'},
            {'input': [-1, 1], 'expected': 0, 'description': 'Positive and negative'}
        ]
    elif 'subtract' in func_lower:
        test_cases = [
            {'input': [5, 3], 'expected': 2, 'description': 'Basic subtraction'},
            {'input': [0, 0], 'expected': 0, 'description': 'Subtracting zeros'}
        ]
    elif 'multiply' in func_lower:
        test_cases = [
            {'input': [3, 4], 'expected': 12, 'description': 'Basic multiplication'},
            {'input': [0, 5], 'expected': 0, 'description': 'Multiply by zero'}
        ]
    elif 'fibonacci' in func_lower:
        test_cases = [
            {'input': [0], 'expected': 0, 'description': 'Fibonacci of 0'},
            {'input': [1], 'expected': 1, 'description': 'Fibonacci of 1'},
            {'input': [5], 'expected': 5, 'description': 'Fibonacci of 5'}
        ]
    elif 'factorial' in func_lower:
        test_cases = [
            {'input': [0], 'expected': 1, 'description': 'Factorial of 0'},
            {'input': [5], 'expected': 120, 'description': 'Factorial of 5'}
        ]
    elif 'prime' in func_lower:
        test_cases = [
            {'input': [2], 'expected': True, 'description': '2 is prime'},
            {'input': [4], 'expected': False, 'description': '4 is not prime'}
        ]
    else:
        # Generic test cases based on number of arguments
        if len(args) == 0:
            test_cases = [
                {'input': [], 'expected': 'check_execution', 'description': 'No arguments'}
            ]
        elif len(args) == 1:
            test_cases = [
                {'input': [1], 'expected': 'check_execution', 'description': 'Single argument'},
                {'input': [0], 'expected': 'check_execution', 'description': 'Zero input'}
            ]
        else:
            test_cases = [
                {'input': [1] * len(args), 'expected': 'check_execution',
                 'description': f'{len(args)} arguments'}
            ]

    return test_cases[:3]  # Limit to 3 test cases per function


async def search_past_feedback(developer_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Search for past feedback in memory service.

    Args:
        developer_id: ID of the developer (defaults to "default_user")
        tool_context: ADK tool context with potential memory service access

    Returns:
        Dictionary containing feedback search results
    """
    logger.info(f"Tool: Searching for past feedback for developer {developer_id}...")

    try:
        # Default developer ID if not provided
        if not developer_id:
            developer_id = tool_context.state.get(StateKeys.USER_ID, 'default_user')

        # Check if memory service is available
        if hasattr(tool_context, 'search_memory'):
            try:
                # Perform structured searches
                queries = [
                    f"developer:{developer_id} code review feedback",
                    f"developer:{developer_id} common issues",
                    f"developer:{developer_id} improvements"
                ]

                all_feedback = []
                patterns = {
                    'common_issues': [],
                    'improvements': [],
                    'strengths': []
                }

                for query in queries:
                    # Use asyncio for potential future async memory service
                    loop = asyncio.get_event_loop()
                    search_result = await loop.run_in_executor(
                        None, tool_context.search_memory, query
                    )

                    if search_result and hasattr(search_result, 'memories'):
                        for memory in search_result.memories[:5]:
                            memory_text = memory.text if hasattr(memory, 'text') else str(memory)
                            all_feedback.append(memory_text)

                            # Extract patterns
                            if 'style' in memory_text.lower():
                                patterns['common_issues'].append('style compliance')
                            if 'improved' in memory_text.lower():
                                patterns['improvements'].append('showing improvement')
                            if 'excellent' in memory_text.lower():
                                patterns['strengths'].append('consistent quality')

                # Store in state
                tool_context.state[StateKeys.PAST_FEEDBACK] = all_feedback
                tool_context.state[StateKeys.FEEDBACK_PATTERNS] = patterns

                logger.info(f"Tool: Found {len(all_feedback)} past feedback items")

                return {
                    "status": "success",
                    "feedback_found": True,
                    "count": len(all_feedback),
                    "summary": " | ".join(all_feedback[:3]) if all_feedback else "No feedback",
                    "patterns": patterns
                }

            except Exception as e:
                logger.warning(f"Tool: Memory search error: {e}")

        # Fallback: Check state for cached feedback
        cached_feedback = tool_context.state.get(StateKeys.USER_PAST_FEEDBACK_CACHE, [])
        if cached_feedback:
            tool_context.state[StateKeys.PAST_FEEDBACK] = cached_feedback
            return {
                "status": "success",
                "feedback_found": True,
                "count": len(cached_feedback),
                "summary": "Using cached feedback",
                "patterns": {}
            }

        # No feedback found
        tool_context.state[StateKeys.PAST_FEEDBACK] = []
        logger.info("Tool: No past feedback found")

        return {
            "status": "success",
            "feedback_found": False,
            "message": "No past feedback available - this appears to be a first submission",
            "patterns": {}
        }

    except Exception as e:
        error_msg = f"Feedback search error: {str(e)}"
        logger.error(f"Tool: {error_msg}", exc_info=True)

        tool_context.state[StateKeys.PAST_FEEDBACK] = []

        return {
            "status": "error",
            "message": error_msg,
            "feedback_found": False
        }


async def update_grading_progress(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Updates grading progress counters and metrics in state.
    """
    logger.info("Tool: Updating grading progress...")

    try:
        current_time = datetime.now().isoformat()

        # Build all state changes
        state_updates = {}

        # Temporary (invocation-level) state
        state_updates[StateKeys.TEMP_PROCESSING_TIMESTAMP] = current_time

        # Session-level state
        attempts = tool_context.state.get(StateKeys.GRADING_ATTEMPTS, 0) + 1
        state_updates[StateKeys.GRADING_ATTEMPTS] = attempts
        state_updates[StateKeys.LAST_GRADING_TIME] = current_time

        # User-level persistent state
        lifetime_submissions = tool_context.state.get(StateKeys.USER_TOTAL_SUBMISSIONS, 0) + 1
        state_updates[StateKeys.USER_TOTAL_SUBMISSIONS] = lifetime_submissions
        state_updates[StateKeys.USER_LAST_SUBMISSION_TIME] = current_time

        # Calculate improvement metrics
        current_style_score = tool_context.state.get(StateKeys.STYLE_SCORE, 0)
        last_style_score = tool_context.state.get(StateKeys.USER_LAST_STYLE_SCORE, 0)
        score_improvement = current_style_score - last_style_score

        state_updates[StateKeys.USER_LAST_STYLE_SCORE] = current_style_score
        state_updates[StateKeys.SCORE_IMPROVEMENT] = score_improvement

        # Track test results if available
        test_results = tool_context.state.get(StateKeys.TEST_RESULTS, {})
        if test_results and test_results.get('total', 0) > 0:
            pass_rate = (test_results.get('passed', 0) / test_results['total']) * 100
            state_updates[StateKeys.USER_LAST_TEST_PASS_RATE] = pass_rate

        # Apply all updates atomically
        for key, value in state_updates.items():
            tool_context.state[key] = value

        logger.info(f"Tool: Progress updated - Attempt #{attempts}, "
                    f"Lifetime: {lifetime_submissions}")

        return {
            "status": "success",
            "session_attempts": attempts,
            "lifetime_submissions": lifetime_submissions,
            "timestamp": current_time,
            "improvement": {
                "style_score_change": score_improvement,
                "direction": "improved" if score_improvement > 0 else "declined"
            },
            "summary": f"Attempt #{attempts} recorded, {lifetime_submissions} total submissions"
        }

    except Exception as e:
        error_msg = f"Progress update error: {str(e)}"
        logger.error(f"Tool: {error_msg}", exc_info=True)

        return {
            "status": "error",
            "message": error_msg
        }


async def save_grading_report(feedback_text: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Saves a detailed grading report as an artifact.
    """
    logger.info("Tool: Saving grading report...")

    try:
        # Gather all relevant data
        code = tool_context.state.get(StateKeys.CODE_TO_REVIEW, '')
        analysis = tool_context.state.get(StateKeys.CODE_ANALYSIS, {})
        style_score = tool_context.state.get(StateKeys.STYLE_SCORE, 0)
        test_results = tool_context.state.get(StateKeys.TEST_RESULTS, {})
        timestamp = datetime.now().isoformat()

        # Create comprehensive report
        report = {
            'timestamp': timestamp,
            'grading_attempt': tool_context.state.get(StateKeys.GRADING_ATTEMPTS, 1),
            'code': {
                'content': code,
                'line_count': len(code.splitlines()),
                'hash': hashlib.md5(code.encode()).hexdigest()
            },
            'analysis': analysis,
            'style': {
                'score': style_score,
                'issues': tool_context.state.get(StateKeys.STYLE_ISSUES, [])[:5]
            },
            'tests': test_results,
            'feedback': feedback_text,
            'improvements': {
                'score_change': tool_context.state.get(StateKeys.SCORE_IMPROVEMENT, 0),
                'from_last_score': tool_context.state.get(StateKeys.USER_LAST_STYLE_SCORE, 0)
            }
        }

        # Convert to JSON string
        report_json = json.dumps(report, indent=2)

        # Check if save_artifact is available
        if hasattr(tool_context, 'save_artifact'):
            from google.genai import types

            # Create artifact
            artifact = types.Part.from_text(report_json)

            # Generate filename with timestamp
            filename = f"grading_report_{timestamp.replace(':', '-')}.json"

            # Save artifact (async)
            loop = asyncio.get_event_loop()
            version = await loop.run_in_executor(
                None, tool_context.save_artifact, filename, artifact
            )

            # Also save a "latest" version for easy access
            await loop.run_in_executor(
                None, tool_context.save_artifact, "latest_grading_report.json", artifact
            )

            logger.info(f"Tool: Report saved as {filename} (version {version})")

            return {
                "status": "success",
                "artifact_saved": True,
                "filename": filename,
                "version": version,
                "size": len(report_json)
            }
        else:
            # Fallback: Store in state
            tool_context.state[StateKeys.USER_LAST_GRADING_REPORT] = report
            logger.info("Tool: Report saved to state (no artifact service)")

            return {
                "status": "success",
                "artifact_saved": False,
                "message": "Report saved to state only",
                "size": len(report_json)
            }

    except Exception as e:
        error_msg = f"Report save error: {str(e)}"
        logger.error(f"Tool: {error_msg}", exc_info=True)

        return {
            "status": "error",
            "message": error_msg,
            "artifact_saved": False
        }


# --- Helper Functions ---

def _calculate_avg_function_length(tree: ast.AST) -> float:
    """Calculate average function length in lines."""
    function_lengths = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                length = node.end_lineno - node.lineno + 1
                function_lengths.append(length)

    if function_lengths:
        return sum(function_lengths) / len(function_lengths)
    return 0.0


# Create FunctionTool instance for test_runner_agent to use
generate_tests_tool = FunctionTool(func=generate_and_run_tests)


# Module exports
__all__ = [
    'analyze_code_structure',
    'check_code_style',
    'generate_and_run_tests',
    'search_past_feedback',
    'update_grading_progress',
    'save_grading_report',
    'generate_tests_tool'
]

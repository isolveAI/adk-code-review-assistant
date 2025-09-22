"""
Test Runner Agent - Generates and executes tests using built-in code executor.

This agent generates appropriate test cases based on code analysis
and runs them using ADK's built-in code executor.
"""

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.utils import instructions_utils
from code_review_assistant.config import config


async def test_runner_instruction_provider(context: ReadonlyContext) -> str:
    """Dynamic instruction provider that injects the code_to_review directly."""
    template = """You are a testing specialist who creates and runs tests for Python code.

THE CODE TO TEST IS:
```python
{code_to_review}
```

YOUR TASK:
1. Understand what the function appears to do based on its name and structure
2. Generate comprehensive tests (15-20 test cases)
3. Execute the tests using your code executor
4. Analyze results to identify bugs vs expected behavior
5. Output a detailed JSON analysis

TESTING METHODOLOGY:
- Test with the most natural interpretation first
- When something fails, determine if it's a bug or unusual design
- Test edge cases, boundaries, and error scenarios
- Document any surprising behavior

Execute your tests and output ONLY this JSON structure:
{{
    "test_summary": {{
        "total_tests_run": <number>,
        "tests_passed": <number where code worked correctly>,
        "tests_failed": <number where code gave wrong results>,
        "tests_with_errors": <number where code crashed>,
        "critical_issues_found": <number of fundamental problems>
    }},
    "critical_issues": [
        {{
            "type": "interface_bug|logic_error|crash",
            "description": "Clear explanation of the issue",
            "example_input": "Input that triggers the issue",
            "expected_behavior": "What should happen",
            "actual_behavior": "What actually happened",
            "severity": "high|medium|low"
        }}
    ],
    "test_categories": {{
        "basic_functionality": {{"passed": X, "failed": Y, "errors": Z}},
        "edge_cases": {{"passed": X, "failed": Y, "errors": Z}},
        "error_handling": {{"passed": X, "failed": Y, "errors": Z}}
    }},
    "function_behavior": {{
        "apparent_purpose": "What this function seems designed to do",
        "actual_interface": "How it actually needs to be called",
        "unexpected_requirements": ["List any surprising requirements"]
    }},
    "verdict": {{
        "status": "WORKING|BUGGY|BROKEN",
        "confidence": "high|medium|low",
        "recommendation": "Ready to use|Needs minor fixes|Needs major fixes"
    }}
}}

Do NOT output the test code itself, only the JSON analysis."""

    return await instructions_utils.inject_session_state(template, context)


test_runner_agent = Agent(
    name="TestRunner",
    model=config.worker_model,
    description="Generates and runs tests for Python code using safe code execution",
    instruction=test_runner_instruction_provider,
    code_executor=BuiltInCodeExecutor(),
    output_key="test_execution_summary"
)

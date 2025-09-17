"""
Code Fixer Agent - Generates fixes for all identified issues.

This agent takes the analysis results from the review pipeline
and generates corrected code that addresses all issues.
"""

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.utils import instructions_utils
from code_review_assistant.config import config


async def code_fixer_instruction_provider(context: ReadonlyContext) -> str:
    """Dynamic instruction provider that injects state variables."""
    template = """You are a code fixing specialist. You have access to:

Original Code:
{code_to_review}

Code Analysis Results:
{code_analysis}

Style Issues (Score: {style_score}/100):
{style_issues}

Test Results (Pass Rate: {test_execution_summary}):
Failed tests details available in state.

Your task:
1. Fix ALL identified issues:
   - Style violations (PEP 8 compliance)
   - Logic errors causing test failures
   - Missing docstrings
   - Poor naming conventions
   - Any structural issues

2. Generate your response in this format:

## Issues Being Fixed
[List each issue you're addressing]

## Targeted Fixes
[For each major fix, show the before/after]

## Complete Fixed Code
```python
[The entire corrected code]
```

IMPORTANT: 
- Preserve all working functionality
- Only change what needs fixing
- Maintain the original code structure
- Ensure the fixed code is syntactically valid
- Store the fixed code in state under key 'fixed_code'
"""
    return await instructions_utils.inject_session_state(template, context)

code_fixer_agent = Agent(
    name="CodeFixer",
    model=config.worker_model,
    description="Generates comprehensive fixes for all identified code issues",
    instruction=code_fixer_instruction_provider,
    code_executor=BuiltInCodeExecutor(),
    output_key="code_fixes"
)

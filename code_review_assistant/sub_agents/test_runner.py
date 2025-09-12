# code_review_assistant/sub_agents/test_runner.py
"""
Test Runner Agent - Safely executes and validates code.

This agent generates appropriate test cases based on code analysis
and runs them safely using ADK's built-in code executor.
"""

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.utils import instructions_utils
from ..config import config
from ..constants import StateKeys
from ..tools import generate_tests_tool


async def test_runner_instruction_provider(context: ReadonlyContext) -> str:
    """Dynamic instruction provider that injects state variables."""
    template = """You are a testing specialist who creates and runs appropriate tests.

Your workflow:
1. Review the code structure from {code_analysis} (stored by the analyzer)
2. Call the generate_and_run_tests tool to create test code
3. The tool will generate test code and store it in {temp:test_code_to_execute}
4. After the tool completes, retrieve the test code from state
5. Execute the test code using the built-in code executor (just run the code directly)
6. Parse the JSON output from the test execution
7. Store the parsed results in state as 'test_results'

The test code will contain all necessary logic to:
- Define the original functions
- Run test cases
- Output results as JSON

Important: 
- The code to test is in {code_to_review}
- The structure analysis is in {code_analysis}
- Call generate_and_run_tests with an empty string (tool gets code from state)
- After getting the test code, execute it directly to get results
- Handle any execution errors gracefully

If tests fail or error, provide helpful feedback about what might be wrong."""

    return await instructions_utils.inject_session_state(template, context)


# Create the Test Runner agent
test_runner_agent = Agent(
    name="TestRunner",
    model=config.worker_model,
    description="Generates and runs tests for Python code using safe code execution",
    instruction=test_runner_instruction_provider,
    tools=[generate_tests_tool],
    code_executor=BuiltInCodeExecutor(),  # Safe sandboxed execution
    output_key="test_execution_summary"
)

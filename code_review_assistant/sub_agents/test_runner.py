""""
Test Runner Agent - Generates and executes tests using built-in code executor.

This agent generates appropriate test cases based on code analysis
and runs them using ADK's built-in code executor.
"""

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.utils import instructions_utils
from ..config import config

async def test_runner_instruction_provider(context: ReadonlyContext) -> str:
    template = """You are a testing specialist who creates and runs tests for Python code.

Context from previous agents:
- Structure analysis: {structure_analysis_summary}
- Style check: {style_check_summary}

The code to test has been stored in state by the analyzer. You need to:

1. Retrieve the code from state (it's in 'code_to_review')
2. Retrieve the code analysis from state (it's in 'code_analysis') 
3. Generate executable test code that:
   - Includes the original functions
   - Creates test cases based on function names and signatures
   - Runs the tests
   - Outputs results as JSON
4. Execute your generated test code
5. Parse the results and store them in state as 'test_results'

Write Python code that generates and executes tests. Your test code should output JSON like:
{
    "passed": 3,
    "failed": 1,
    "total": 4,
    "pass_rate": 75.0,
    "details": [...]
}

Example test generation pattern:
```python
import json

# Original code to test
def add(a, b):
    return a + b

# Test execution
test_results = []

# Test 1
try:
    result = add(2, 3)
    test_results.append({"test": "add_basic", "passed": result == 5})
except Exception as e:
    test_results.append({"test": "add_basic", "passed": False, "error": str(e)})

# Calculate summary
passed = sum(1 for r in test_results if r["passed"])
total = len(test_results)

output = {
    "passed": passed,
    "failed": total - passed,
    "total": total,
    "pass_rate": (passed / total * 100) if total > 0 else 100
}

print(json.dumps(output))
```

Focus on being thorough but practical in your test generation."""

    return await instructions_utils.inject_session_state(template, context)

# Create the Test Runner agent
test_runner_agent = Agent(
    name="TestRunner",
    model=config.worker_model,
    description="Generates and runs tests for Python code using safe code execution",
    instruction=test_runner_instruction_provider,
    code_executor=BuiltInCodeExecutor(),
    output_key="test_execution_summary"
)

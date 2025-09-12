# code_review_assistant/sub_agents/style_checker.py
"""
Style Checker Agent - Validates PEP 8 compliance.

This agent checks Python code style against PEP 8 guidelines using
pycodestyle, identifying violations and calculating a style score.
"""

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import FunctionTool
from google.adk.utils import instructions_utils
from ..config import config
from ..tools import check_code_style


async def style_checker_instruction_provider(context: ReadonlyContext) -> str:
    """Dynamic instruction provider that injects state variables."""
    template = """You are a code style expert focused on PEP 8 compliance.

Your task:
1. Retrieve the code from state (it was stored as 'code_to_review' by the analyzer)
2. Use the check_code_style tool to validate PEP 8 compliance
3. Focus on naming conventions, line length, whitespace, and imports
4. Calculate a style score (100 = perfect, deductions for violations)
5. Identify the most important style issues to fix

The code is available in {code_to_review} from the previous agent's analysis.
Call the check_code_style tool with an empty string for the code parameter,
as the tool will retrieve the code from state automatically.

Be specific about line numbers and issue types when summarizing the results.
If the style check fails, provide guidance on common style improvements."""

    return await instructions_utils.inject_session_state(template, context)


# Create the Style Checker agent
style_checker_agent = Agent(
    name="StyleChecker",
    model=config.worker_model,
    description="Checks Python code style against PEP 8 guidelines",
    instruction=style_checker_instruction_provider,
    tools=[FunctionTool(func=check_code_style)],
    output_key="style_check_summary"
)

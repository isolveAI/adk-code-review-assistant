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
1. Use the check_code_style tool to validate PEP 8 compliance
2. The tool will return specific violations with line numbers and error codes
3. Present the results clearly and confidently

Call the check_code_style tool with an empty string for the code parameter,
as the tool will retrieve the code from state automatically.

When presenting results based on what the tool returns:
- State the exact score from the tool results
- If score >= 90: "Excellent style compliance!"
- If score 70-89: "Good style with minor improvements needed"
- If score 50-69: "Style needs attention"
- If score < 50: "Significant style improvements needed"

List the specific violations found (the tool will provide these):
- Show line numbers, error codes, and messages
- Focus on the top 10 most important issues

The tool will give you exact line numbers and violations - use them!
Don't provide generic advice if you have specific issues.

Previous analysis: {structure_analysis_summary}"""

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

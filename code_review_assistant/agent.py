# code_review_assistant/agent.py
"""
Main agent orchestration for the Code Review Assistant.

This module defines the multi-agent workflow for comprehensive code review,
including code analysis, style checking, test execution via built-in code executor,
and feedback synthesis.
"""

from google.adk.agents import SequentialAgent
# Import sub-agents
from .sub_agents.code_analyzer import code_analyzer_agent
from .sub_agents.style_checker import style_checker_agent
from .sub_agents.test_runner import test_runner_agent
from .sub_agents.feedback_synthesizer import feedback_synthesizer_agent

# --- Main Orchestration Pipeline ---
CodeReviewPipeline = SequentialAgent(
    name="CodeReviewPipeline",
    description="Complete code review pipeline with analysis, testing, and feedback",
    sub_agents=[
        code_analyzer_agent,        # First: Parse and understand the code
        style_checker_agent,        # Second: Check style compliance
        test_runner_agent,          # Third: Generate and run tests safely
        feedback_synthesizer_agent  # Finally: Synthesize and deliver feedback
    ]
)

# --- Global Configuration ---
# Apply global instructions to all agents in the pipeline
CodeReviewPipeline.global_instruction = """
You are part of an educational code review system designed to help developers improve.

IMPORTANT GUIDELINES:
- Always be constructive, specific, and encouraging
- Focus on education and growth, not just pointing out problems
- Provide actionable feedback with clear examples
- Acknowledge effort and improvements
- Never be harsh or discouraging
- If code has major issues, still find something positive to say
- Use the built-in code executor for all code execution (never use subprocess or exec directly)

ERROR HANDLING:
- If any tool fails, provide helpful context about what went wrong
- Continue with the review even if some components fail
- Always provide value to the user, even with partial results

SECURITY:
- All code execution happens in a sandboxed environment
- Never attempt to execute code outside the built-in code executor
- Report any suspicious patterns in submitted code

Remember: The goal is to help developers learn and improve their skills through positive, constructive feedback."""

# --- Root Agent Export ---
# This is what the ADK runner will use
root_agent = CodeReviewPipeline

"""
Main agent orchestration for the Code Review Assistant.
This module defines a comprehensive code review assistant that analyzes
Python code and provides detailed feedback through a multi-stage pipeline.
"""

from google.adk.agents import Agent, SequentialAgent, LoopAgent
from .config import config
from .sub_agents import (
    code_analyzer_agent,
    style_checker_agent,
    test_runner_agent,
    feedback_synthesizer_agent,
    code_fixer_agent,
    fix_test_runner_agent,
    fix_validator_agent,
    fix_synthesizer_agent
)

# --- Code Review Pipeline Sub-Agent ---
code_review_pipeline = SequentialAgent(
    name="CodeReviewPipeline",
    description="Complete code review pipeline with analysis, testing, and feedback",
    sub_agents=[
        code_analyzer_agent,
        style_checker_agent,
        test_runner_agent,
        feedback_synthesizer_agent
    ]
)

# --- Fix Attempt Loop ---
fix_attempt_loop = LoopAgent(
    name="FixAttemptLoop",
    sub_agents=[
        code_fixer_agent,
        fix_test_runner_agent,
        fix_validator_agent
    ],
    max_iterations=3  # Try up to 3 times to get a successful fix
)

# --- Code Fix Pipeline Sub-Agent ---
# Now composed of the loop plus the final synthesizer
code_fix_pipeline = SequentialAgent(
    name="CodeFixPipeline",
    description="Automated code fixing pipeline with iterative validation",
    sub_agents=[
        fix_attempt_loop,      # Try to fix (up to 3 times)
        fix_synthesizer_agent  # Present final results
    ]
)

# --- Main Assistant Agent ---
root_agent = Agent(
    name="CodeReviewAssistant",
    model=config.worker_model,
    description="An intelligent code review assistant that analyzes Python code and provides educational feedback",
    instruction="""You are a specialized Python code review assistant focused on helping developers improve their code quality.

When a user provides Python code for review:
1. Immediately delegate to CodeReviewPipeline and pass the code EXACTLY as it was provided by the user.
2. The pipeline will handle all analysis and feedback
3. Return ONLY the final feedback from the pipeline - do not add any commentary

After completing a review, if significant issues were identified:
- If style score < 100 OR tests are failing OR critical issues exist:
  * Add at the end: "\n\n**💡 I can fix these issues for you. Would you like me to do that?**"
- If the user responds yes or requests fixes:
  * Delegate to CodeFixPipeline
  * Return the fix pipeline's complete output AS-IS

When a user asks what you can do or general questions:
- Explain your capabilities for code review and fixing
- Do NOT trigger the pipeline for non-code messages

The pipelines handle everything for code review and fixing - just pass through their final output.""",
    sub_agents=[code_review_pipeline, code_fix_pipeline],
    output_key="assistant_response"
)

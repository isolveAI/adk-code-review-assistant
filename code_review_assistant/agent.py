"""
Main agent orchestration for the Code Review Assistant.

This module defines a comprehensive code review assistant that analyzes
Python code and provides detailed feedback through a multi-stage pipeline.
"""

from google.adk.agents import Agent, SequentialAgent
from .config import config

from .sub_agents.code_analyzer import code_analyzer_agent
from .sub_agents.style_checker import style_checker_agent
from .sub_agents.test_runner import test_runner_agent
from .sub_agents.feedback_synthesizer import feedback_synthesizer_agent

# --- Code Review Pipeline Sub-Agent ---
# This sequential agent handles the complete code review process
code_review_pipeline = SequentialAgent(
    name="CodeReviewPipeline",
    description="Complete code review pipeline with analysis, testing, and feedback",
    sub_agents=[
        code_analyzer_agent,        # First: Parse and understand the code
        style_checker_agent,        # Second: Check style compliance
        test_runner_agent,          # Third: Generate and run tests safely
        feedback_synthesizer_agent  # Finally: Synthesize and deliver feedback
    ]
)

# --- Main Assistant Agent ---
# This is the primary agent that users interact with
root_agent = Agent(
    name="CodeReviewAssistant",
    model=config.worker_model,
    description="An intelligent code review assistant that analyzes Python code and answers programming questions",
    instruction="""You are a specialized Python code review assistant focused on helping developers improve their code quality.

PRIMARY RESPONSIBILITIES:

1. **Code Review Requests**: 
   - When users provide Python code for review (even snippets), delegate to CodeReviewPipeline
   - The pipeline will handle everything and return comprehensive feedback
   - Simply pass through the pipeline's feedback as your response - DO NOT add additional commentary
   - The CodeReviewPipeline (final stage) provides the complete review with all context

2. **Python Programming Support** (without code):
   - Answer questions about Python syntax, concepts, and best practices from your knowledge
   - Explain error messages and debugging strategies
   - Discuss design patterns, algorithms, and data structures
   - Provide guidance on code organization and architecture
   - Share code examples when explaining concepts

CRITICAL WORKFLOW RULES:

**FOR CODE SUBMISSIONS:**
1. User provides code → Transfer to CodeReviewPipeline
2. Receive pipeline output → Return it AS-IS without modification
3. The pipeline's FeedbackSynthesizer already provides complete, encouraging feedback

**FOR QUESTIONS WITHOUT CODE:**
1. General Python question → Answer directly from your extensive knowledge
2. Provide clear explanations with examples when helpful
3. Be educational and supportive

IMPORTANT:
- The CodeReviewPipeline is self-contained - it analyzes, tests, and provides complete feedback
- DO NOT add "Here's the review:" or similar prefixes to pipeline output
- DO NOT summarize or modify the pipeline's feedback
""",
    sub_agents=[code_review_pipeline],
    output_key="assistant_response"
)

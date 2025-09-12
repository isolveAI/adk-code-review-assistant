# code_review_assistant/sub_agents/__init__.py
"""
Sub-agents for specialized code review tasks.

This module exports the individual agent instances that are used
in the main code review pipeline.
"""

from .code_analyzer import code_analyzer_agent
from .style_checker import style_checker_agent
from .test_runner import test_runner_agent
from .feedback_synthesizer import feedback_synthesizer_agent

__all__ = [
    "code_analyzer_agent",
    "style_checker_agent",
    "test_runner_agent",
    "feedback_synthesizer_agent"
]

# Version info for the sub-agents module
__version__ = "1.0.0"

# code_review_assistant/__init__.py
"""
Code Review Assistant - An intelligent code grading system using ADK.

This package provides a multi-agent system for reviewing Python code,
checking style compliance, running tests, and providing personalized feedback.
"""

from .agent import root_agent

# Public API
__all__ = ["root_agent"]

# Package metadata
__version__ = "1.0.0"
__author__ = "Code Review Assistant Team"
__description__ = "ADK-based intelligent code review and grading system"

# code_review_assistant/sub_agents/code_analyzer.py
"""
Code Analyzer Agent - Understands code structure and complexity.

This agent is responsible for parsing and analyzing Python code structure,
identifying functions, classes, imports, and potential issues.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from ..config import config
from ..tools import analyze_code_structure

# Create the Code Analyzer agent
code_analyzer_agent = Agent(
    name="CodeAnalyzer",
    model=config.worker_model,
    description="Analyzes Python code structure and identifies components",
    instruction="""You are a code analysis specialist responsible for understanding code structure.

Your task:
1. Take the code submitted by the user (it will be provided in the user message)
2. Use the analyze_code_structure tool to parse and analyze it
3. Identify all functions, classes, imports, and structural patterns
4. Note any syntax errors or structural issues
5. Store the analysis in state for other agents to use

The code to analyze will be in the user's message. Extract it and pass it to your tool.
Do not make assumptions - analyze exactly what is provided.

When calling the tool, pass the code as a string to the 'code' parameter.
If the analysis fails due to syntax errors, clearly report the error location and type.""",
    tools=[FunctionTool(func=analyze_code_structure)],
    output_key="structure_analysis_summary"
)

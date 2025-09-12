# test_code_inputs/needs_linting.py

# This file has several linting errors for demonstration.
import os # Unused import

def add(a,b): # Missing type hints, missing space after comma
    """Adds two numbers."""
    # Badly formatted comment
    result = a+b # No spaces around operator
    unused_variable = "I am not used"
    return result

# No blank line at end of file
# test_code_inputs/failing_tests.py
"""
Code with logical errors that will fail tests.

This module contains functions that are syntactically correct
but have deliberate bugs that will be caught by unit tests.
"""

from typing import Union, List, Optional


def add(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    """
    Incorrectly adds two numbers (has off-by-one error).

    Args:
        a: First number
        b: Second number

    Returns:
        Sum plus one (bug!)
    """
    return a + b + 1  # Deliberate bug: adds extra 1


def fibonacci(n: int) -> int:
    """
    Incorrect Fibonacci implementation.

    Args:
        n: Position in sequence

    Returns:
        Wrong Fibonacci number due to bugs
    """
    if n <= 1:
        return n + 1  # Bug: should return n, not n+1

    # Recursive implementation (inefficient and buggy)
    return fibonacci(n - 1) + fibonacci(n - 2)


def is_prime(n: int) -> bool:
    """
    Inefficient and incorrect prime checker.

    Args:
        n: Number to check

    Returns:
        Sometimes wrong result
    """
    # Missing check for n <= 1 (bug)
    # Inefficient: checks all numbers up to n
    for i in range(2, n):
        if n % i == 0:
            return False

    return True  # Bug: returns True for 0, 1, and negative numbers


def factorial(n: int) -> int:
    """
    Incorrect factorial implementation.

    Args:
        n: Input number

    Returns:
        Wrong factorial value
    """
    # Missing negative check (will cause infinite recursion)
    if n == 0:
        return 0  # Bug: factorial(0) should be 1, not 0

    if n == 1:
        return 1

    # Recursive with bug
    return n * factorial(n - 1)


def reverse_string(text: str) -> str:
    """
    Incorrectly reverses a string.

    Args:
        text: String to reverse

    Returns:
        Incorrectly reversed string
    """
    if not text:
        return "empty"  # Bug: should return empty string

    # Off-by-one error in slicing
    return text[-1:0:-1]  # Bug: misses first character


def find_max(numbers: List[Union[int, float]]) -> Optional[Union[int, float]]:
    """
    Find maximum with edge case bugs.

    Args:
        numbers: List of numbers

    Returns:
        Sometimes wrong maximum
    """
    if not numbers:
        return 0  # Bug: should return None for empty list

    # Incorrect initialization
    max_val = 0  # Bug: assumes all numbers are positive
    for num in numbers:
        if num > max_val:
            max_val = num

    return max_val


class Calculator:
    """
    Calculator with arithmetic bugs.
    """

    def __init__(self):
        """Initialize with wrong starting value."""
        self.result = 1  # Bug: should start at 0

    def add(self, value: Union[int, float]) -> 'Calculator':
        """Add with rounding error."""
        self.result += value + 0.1  # Bug: adds extra 0.1
        return self

    def multiply(self, value: Union[int, float]) -> 'Calculator':
        """Multiply with sign error."""
        self.result *= abs(value)  # Bug: ignores negative values
        return self

    def get_result(self) -> Union[int, float]:
        """Get result with truncation."""
        return int(self.result)  # Bug: truncates decimals

    def reset(self) -> 'Calculator':
        """Reset to wrong value."""
        self.result = 1  # Bug: should reset to 0
        return self


def divide(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    """
    Division with no zero check.

    Args:
        a: Dividend
        b: Divisor

    Returns:
        Quotient (will crash on zero)
    """
    # Bug: no check for division by zero
    return a / b


def is_palindrome(text: str) -> bool:
    """
    Palindrome checker with case sensitivity bug.

    Args:
        text: String to check

    Returns:
        Whether string is palindrome (case sensitive - bug!)
    """
    # Bug: doesn't handle case or spaces
    return text == text[::-1]


# Main execution will have errors
if __name__ == "__main__":
    print(f"add(2, 2) = {add(2, 2)} (should be 4, but returns 5)")
    print(f"fibonacci(0) = {fibonacci(0)} (should be 0, but returns 1)")
    print(f"is_prime(1) = {is_prime(1)} (should be False, but returns True)")
    print(f"factorial(0) = {factorial(0)} (should be 1, but returns 0)")

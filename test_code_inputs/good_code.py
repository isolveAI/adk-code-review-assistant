# test_code_inputs/good_code.py
"""
Example of well-written Python code for testing.

This module contains several well-implemented functions with proper
documentation, type hints, and PEP 8 compliance.
"""

from typing import Union, List, Optional


def add(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    """
    Add two numbers together.

    Args:
        a: First number (int or float)
        b: Second number (int or float)

    Returns:
        Sum of the two numbers

    Examples:
        >>> add(2, 2)
        4
        >>> add(1.5, 2.5)
        4.0
    """
    return a + b


def fibonacci(n: int) -> int:
    """
    Calculate the nth Fibonacci number using iteration.

    Args:
        n: Position in Fibonacci sequence (must be non-negative)

    Returns:
        The nth Fibonacci number

    Raises:
        ValueError: If n is negative

    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
        >>> fibonacci(6)
        8
    """
    if n < 0:
        raise ValueError("Fibonacci not defined for negative numbers")

    if n <= 1:
        return n

    # Use iteration for better performance than recursion
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b

    return b


def is_prime(n: int) -> bool:
    """
    Check if a number is prime.

    Uses optimized algorithm checking divisors up to sqrt(n).

    Args:
        n: Integer to check for primality

    Returns:
        True if n is prime, False otherwise

    Examples:
        >>> is_prime(2)
        True
        >>> is_prime(4)
        False
        >>> is_prime(17)
        True
    """
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False

    # Check odd divisors up to sqrt(n)
    for i in range(3, int(n ** 0.5) + 1, 2):
        if n % i == 0:
            return False

    return True


def factorial(n: int) -> int:
    """
    Calculate the factorial of a non-negative integer.

    Args:
        n: Non-negative integer

    Returns:
        The factorial of n (n!)

    Raises:
        ValueError: If n is negative

    Examples:
        >>> factorial(0)
        1
        >>> factorial(5)
        120
    """
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")

    if n <= 1:
        return 1

    result = 1
    for i in range(2, n + 1):
        result *= i

    return result


def reverse_string(text: str) -> str:
    """
    Reverse a string.

    Args:
        text: String to reverse

    Returns:
        Reversed string

    Examples:
        >>> reverse_string("hello")
        'olleh'
        >>> reverse_string("")
        ''
    """
    return text[::-1]


def find_max(numbers: List[Union[int, float]]) -> Optional[Union[int, float]]:
    """
    Find the maximum value in a list of numbers.

    Args:
        numbers: List of integers or floats

    Returns:
        Maximum value, or None if list is empty

    Examples:
        >>> find_max([1, 5, 3, 9, 2])
        9
        >>> find_max([])
        None
    """
    if not numbers:
        return None

    return max(numbers)


class Calculator:
    """
    Simple calculator class for basic arithmetic operations.
    """

    def __init__(self):
        """Initialize the calculator with a zero result."""
        self.result = 0

    def add(self, value: Union[int, float]) -> 'Calculator':
        """
        Add a value to the current result.

        Args:
            value: Value to add

        Returns:
            Self for method chaining
        """
        self.result += value
        return self

    def multiply(self, value: Union[int, float]) -> 'Calculator':
        """
        Multiply the current result by a value.

        Args:
            value: Value to multiply by

        Returns:
            Self for method chaining
        """
        self.result *= value
        return self

    def get_result(self) -> Union[int, float]:
        """
        Get the current result.

        Returns:
            Current calculator result
        """
        return self.result

    def reset(self) -> 'Calculator':
        """
        Reset the calculator to zero.

        Returns:
            Self for method chaining
        """
        self.result = 0
        return self


# Main execution example
if __name__ == "__main__":
    # Example usage
    print(f"add(2, 3) = {add(2, 3)}")
    print(f"fibonacci(10) = {fibonacci(10)}")
    print(f"is_prime(17) = {is_prime(17)}")
    print(f"factorial(5) = {factorial(5)}")

    calc = Calculator()
    result = calc.add(5).multiply(3).add(7).get_result()
    print(f"Calculator result: {result}")

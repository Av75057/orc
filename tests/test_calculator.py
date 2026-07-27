"""Unit tests for calculator module."""
import pytest
from src.calculator import add, subtract, multiply, divide

class TestCalculator:
    """Test suite for calculator arithmetic functions."""

    def test_add(self):
        assert add(2, 3) == 5
        assert add(-1, 1) == 0
        assert add(0, 0) == 0
        assert add(2.5, 3.5) == 6.0

    def test_subtract(self):
        assert subtract(5, 3) == 2
        assert subtract(0, 5) == -5
        assert subtract(-1, -1) == 0
        assert subtract(10.5, 0.5) == 10.0

    def test_multiply(self):
        assert multiply(2, 3) == 6
        assert multiply(-2, 3) == -6
        assert multiply(0, 5) == 0
        assert multiply(2.5, 4) == 10.0

    def test_divide(self):
        assert divide(6, 3) == 2
        assert divide(5, 2) == 2.5
        assert divide(-6, 3) == -2
        assert divide(0, 5) == 0

    def test_divide_by_zero(self):
        with pytest.raises(ZeroDivisionError, match="Cannot divide by zero"):
            divide(5, 0)
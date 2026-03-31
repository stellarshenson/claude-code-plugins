"""
Example test module demonstrating pytest best practices.

This module shows how to structure tests with:
- Fixtures for setup and teardown
- Docstrings for test documentation
- Parametrized tests for multiple inputs
"""
import pytest


@pytest.fixture
def sample_data():
    """Fixture providing sample data for tests.

    Fixtures are reusable setup components that pytest injects
    into test functions. Use them for database connections,
    test data, or any shared setup logic.
    """
    return {"key": "value", "count": 42}


def test_sample_data_structure(sample_data):
    """Test that sample data has expected structure.

    This test demonstrates:
    - Using fixtures as function arguments
    - Multiple assertions in one test
    - Descriptive test naming
    """
    assert "key" in sample_data
    assert "count" in sample_data
    assert isinstance(sample_data["count"], int)


@pytest.mark.parametrize("input_value,expected", [
    (1, True),
    (0, False),
    (-1, True),
])
def test_parametrized_example(input_value, expected):
    """Test with multiple input values.

    Parametrized tests run the same test logic with different
    inputs, reducing code duplication. Each parameter set
    appears as a separate test in the output.
    """
    result = bool(input_value)
    assert result == expected

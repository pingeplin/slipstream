# Agent Development Guidelines

This document provides guidelines for AI coding agents working on this Python project.

## Project Setup

- This is a **Python project** managed by **`uv`**
- **ALWAYS use `uv run` to execute Python commands**
  - ✅ `uv run pytest`
  - ✅ `uv run python script.py`
  - ✅ `uv run python -m module`
  - ❌ `python script.py` (Don't run Python directly)

## Core Development Principles

### 1. Test-Driven Development (TDD) - FIRST PRIORITY

TDD is the **primary development approach** for this project. Follow this workflow:

1. **Write the test first** - Define expected behavior before implementation
2. **Run the test** - Verify it fails (Red)
3. **Write minimal code** - Make the test pass (Green)
4. **Refactor** - Improve code while keeping tests green

#### Testing Philosophy

- **Focus on INPUT and OUTPUT** - Tests should validate behavior, not implementation
- **Black-box testing** - Test what the code does, not how it does it
- **Avoid testing internal methods** - Only test public interfaces
- **No implementation-specific assertions** - Don't assert on private attributes or internal state

**Example:**
```python
# ✅ GOOD - Tests behavior via public interface
def test_calculator_adds_two_numbers():
    calculator = Calculator()
    result = calculator.add(2, 3)
    assert result == 5

# ❌ BAD - Tests implementation details
def test_calculator_internal_state():
    calculator = Calculator()
    calculator.add(2, 3)
    assert calculator._last_operation == "add"  # Don't do this
```

### 2. SOLID Principles

Apply Object-Oriented SOLID principles:

#### S - Single Responsibility Principle
- Each class should have one reason to change
- One class, one responsibility

#### O - Open/Closed Principle
- Open for extension, closed for modification
- Use inheritance and composition to extend behavior

#### L - Liskov Substitution Principle
- Subtypes must be substitutable for their base types
- Derived classes should extend, not replace, base class behavior

#### I - Interface Segregation Principle
- Many specific interfaces are better than one general interface
- Clients shouldn't depend on interfaces they don't use

#### D - Dependency Inversion Principle
- Depend on abstractions, not concretions
- Use interfaces/abstract classes to define contracts

## Development Workflow

1. **Understand the requirement**
2. **Write a failing test** (TDD Red phase)
3. **Implement minimal code** to pass the test (TDD Green phase)
4. **Refactor** applying SOLID principles
5. **Ensure all tests pass** using `uv run pytest`
6. **Commit with clear messages**

## Testing with pytest

### Test Structure - Use Functions, Not Classes

**IMPORTANT:** Write tests as **standalone functions**, not as methods inside test classes.

**✅ GOOD - Function-based tests:**
```python
def test_calculator_adds_two_numbers():
    calculator = Calculator()
    result = calculator.add(2, 3)
    assert result == 5

def test_calculator_subtracts_two_numbers():
    calculator = Calculator()
    result = calculator.subtract(5, 3)
    assert result == 2
```

**❌ BAD - Class-based tests:**
```python
class TestCalculator:  # Don't do this
    def test_adds_two_numbers(self):
        calculator = Calculator()
        result = calculator.add(2, 3)
        assert result == 5
```

**Why use functions instead of classes?**
- Simpler and more direct
- Easier to read and maintain
- No unnecessary indentation
- Better alignment with pytest's functional style
- Use fixtures for shared setup instead of class methods

### Running Tests
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_module.py

# Run specific test function
uv run pytest tests/test_module.py::test_function_name

# Run with verbose output
uv run pytest -v
```

## Code Quality Standards

- Write clear, self-documenting code
- Use type hints for function signatures
- Follow PEP 8 style guidelines
- Keep functions small and focused
- Prefer composition over inheritance when appropriate

## Remember

> **"Tests are the specification of behavior, not implementation."**

Focus on **WHAT** the code should do, not **HOW** it does it.

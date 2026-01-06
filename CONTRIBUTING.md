# Contributing to Financial Research Analyst Agent

Thank you for your interest in contributing to this project! This document provides guidelines and steps for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)
- [Testing](#testing)

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to uphold this code.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Set up the development environment
4. Create a new branch for your changes

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/financial-research-analyst-agent.git
cd financial-research-analyst-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install

# Copy environment file
cp .env.example .env
# Edit .env with your API keys
```

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-new-indicator` - For new features
- `fix/rsi-calculation-bug` - For bug fixes
- `docs/update-readme` - For documentation
- `refactor/agent-architecture` - For refactoring

### Commit Messages

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

Example:

```
feat(agents): add support for moving average crossover detection

- Implement golden cross detection
- Implement death cross detection
- Add unit tests for new functionality
```

## Pull Request Process

1. Update documentation if needed
2. Add or update tests
3. Ensure all tests pass
4. Update the CHANGELOG if applicable
5. Create a pull request with a clear description

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No sensitive data committed
- [ ] Branch is up to date with main

## Style Guidelines

### Python Style

We follow PEP 8 with some modifications:

- Line length: 100 characters
- Use type hints
- Use docstrings for all public functions

```python
def calculate_rsi(
    prices: List[float],
    period: int = 14,
) -> Dict[str, Any]:
    """
    Calculate the Relative Strength Index (RSI).

    Args:
        prices: List of closing prices
        period: RSI calculation period

    Returns:
        Dictionary with RSI value and signal
    """
    pass
```

### Tools

- **Formatter**: Black
- **Linter**: Flake8
- **Type Checker**: MyPy
- **Import Sorter**: isort

Run all checks:

```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_agents.py -v

# Run specific test
pytest tests/test_agents.py::TestTechnicalAnalyst -v
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use descriptive test names
- Use fixtures for common setup
- Mock external API calls

```python
class TestRSICalculation:
    def test_rsi_oversold_signal(self):
        """Test RSI generates oversold signal below 30."""
        prices = [100 - i for i in range(20)]  # Declining prices
        result = calculate_rsi(prices)
        assert result["signal"] == "OVERSOLD"
```

## Questions?

Feel free to open an issue for any questions or concerns.

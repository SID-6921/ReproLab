# Contributing to ReproLab

Thanks for contributing to ReproLab.

## Workflow

1. Create a feature branch from main.
2. Make focused changes with tests.
3. Run local checks.
4. Open a pull request with a clear summary.

## Local Setup

```bash
pip install -e .[dev]
```

## Run Tests

```bash
python -m pytest
```

## Coding Guidelines

- Keep changes modular and deterministic.
- Preserve explainability in correction logic.
- Add or update tests for every behavior change.
- Avoid breaking public API names unless required.

## Pull Request Checklist

- Tests pass locally.
- New logic includes docstrings.
- README is updated if usage changes.
- New constraints include rationale and confidence behavior.

## Reporting Issues

When filing an issue, include:

- Dataset shape and column names
- Reproduction steps
- Expected behavior vs actual behavior
- Error tracebacks or logs

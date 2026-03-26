# Contributing to Centpai

Thank you for your interest in contributing! Here's everything you need to get started.

## Getting Started

Follow the [setup instructions in the README](README.md#getting-started) to run the project locally.

## Workflow

1. **Fork** the repository and create a branch from `main`
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** following the guidelines below

3. **Run checks** before opening a PR
   ```bash
   # Format code
   poetry run black .

   # Run tests
   poetry run pytest
   ```

4. **Open a pull request** against `main` and fill in the PR template

## Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feat/<description>` | `feat/expense-categories` |
| Bug fix | `fix/<description>` | `fix/balance-calculation` |
| Chore/docs | `chore/<description>` | `chore/update-readme` |

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short description>

<optional body>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

Examples:
```
feat: add expense categories
fix: correct balance rounding for odd splits
docs: update setup instructions
```

## Code Style

- Formatting is enforced with [black](https://black.readthedocs.io/). Run `poetry run black .` before committing.
- Follow the existing project structure — one file per command group, service/repo separation.
- Keep functions small and focused.

## Reporting Issues

Open a GitHub issue and include:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Any relevant logs or screenshots

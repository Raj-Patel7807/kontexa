# Contributing to Kontexa

Thank you for contributing to Kontexa. This guide outlines the development workflow, coding standards, and submission practices.

## Development Setup

1. Clone the repository and enter the workspace directory:
   ```bash
   git clone https://github.com/Raj-Patel7807/kontexa.git
   cd kontexa
   ```
2. Install dependencies for both backend and frontend:
   ```bash
   make setup
   ```
3. Start the local database and Redis services:
   ```bash
   make up
   ```

## Commit Conventions

Use Conventional Commits syntax for clear commit history:

- `feat:` — New feature implementation
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `refactor:` — Code changes that neither fix a bug nor add a feature
- `test:` — Adding or updating test cases
- `chore:` — Maintenance tasks, dependencies updates, configuration
- `ci:` — Changes to CI configuration workflows
- `build:` — Changes to build setup or tooling

Example:
```bash
git commit -m "feat: add health check endpoint"
```

## Code Quality Standards

Before creating a pull request, ensure all linting, formatting, and tests pass:

```bash
make lint
make format
make test
```

Refer to [docs/CODE_RULES.md](docs/CODE_RULES.md) for opinionated project guidelines and style requirements.

## Pull Request Guidelines

- Keep PRs focused on a single logical change or responsibility.
- Add or update tests when behavior changes.
- Update relevant documentation in `docs/` if architecture or development procedures change.
- Ensure all automated checks pass in GitHub Actions CI.

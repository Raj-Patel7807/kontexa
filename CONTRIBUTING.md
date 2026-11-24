# Contributing to Kontexa

Thank you for contributing to Kontexa. This guide outlines the development workflow, coding standards, and submission practices.

---

## Code of Conduct & Principles

- **Be truthful about feature state**: Never label a planned or partially scaffolded feature as implemented.
- **Maintain quality**: All submissions must include passing automated tests and clean linting/formatting.
- **Follow conventions**: Adhere to [docs/CODE_RULES.md](docs/CODE_RULES.md) and [AGENTS.md](AGENTS.md).

---

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Raj-Patel7807/kontexa.git
   cd kontexa
   ```
2. **Install dependencies**:
   ```bash
   # Linux / macOS
   make setup

   # Or directly:
   cd backend && uv sync
   cd ../frontend && npm install
   ```
3. **Start local dependencies (PostgreSQL + Redis)**:
   ```bash
   make up
   ```
4. **Apply database migrations**:
   ```bash
   cd backend
   uv run alembic upgrade head
   ```

---

## Commit Conventions

Use Conventional Commits syntax:

- `feat:` — New feature implementation
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `refactor:` — Code changes that neither fix a bug nor add a feature
- `test:` — Adding or updating test cases
- `chore:` — Maintenance tasks, dependency updates, configuration
- `ci:` — Changes to CI configuration workflows
- `build:` — Changes to build setup or tooling

Example:
```bash
git commit -m "docs: reset documentation and feature status for sprint 01"
```

---

## Verification Before Submitting

Always run the full verification suite before creating a pull request:

```bash
# Lint checks
make lint

# Test suite and typechecks
make test

# Production build check
make build
```

---

## Pull Request Guidelines

1. Keep pull requests focused on a single logical change or vertical slice.
2. Ensure database migrations are reversible and tested.
3. Update relevant documentation in `docs/` (including `docs/FEATURE_STATUS.md` and `docs/DECISIONS.md` when applicable).
4. Verify all GitHub Actions CI checks are passing.

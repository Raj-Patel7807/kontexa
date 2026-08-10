# Repository Guidelines

## Documentation

Before making changes:

- Read `docs/CODE_RULES.md` before writing or refactoring code.
- Read `docs/ROADMAP.md`, `docs/DATABASE` and `docs/ARCHITECTURE.md` before making architectural changes.

## Engineering Principles

- Prefer simple, explicit solutions over unnecessary abstractions.
- Keep the backend as a modular monolith.
- Avoid adding dependencies without a clear reason.
- Validate external inputs and handle errors explicitly.
- Use structured logging where appropriate.
- Keep documentation synchronized with architectural changes.

## Verification

After making changes, run:

```bash
make lint
make test

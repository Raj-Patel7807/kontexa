# Code Rules & Development Standards — Kontexa

This document defines opinionated coding standards and practices for Kontexa. All engineers and AI coding agents must adhere to these rules.

---

## 1. Simplify First

Before writing code, evaluate:
- Does this need to exist?
- Is there already a standard-library or project solution?
- Can the design be simpler?
- Am I solving a real requirement?
- Am I introducing abstraction before it is needed?

Prefer simple, readable solutions over clever code. Simple means fewer moving parts, not fewer characters. Do not sacrifice readability for brevity.

Duplication is not automatically a problem. Code that changes for different reasons should not be artificially merged into fragile abstractions.

---

## 2. Language & Tooling

### Python

- **Target Version**: Python 3.12+
- **Line Length**: 100 characters maximum
- **Linting & Formatting**: Enforced via Ruff (`uv run ruff check .` and `uv run ruff format .`)
- **Dependency Management**: Managed exclusively through `uv`. Run `uv add <package>`. Never use `pip install` directly to modify project dependencies.
- **Type Annotations**: Mandatory type hints on public functions using modern Python syntax (`list[str]`, `str | None`).

---

## 3. Module Responsibility & Architecture Boundaries

Each module must have a single, clearly defined responsibility. Avoid generic dumping-ground files such as:
- `utils.py`
- `helpers.py`
- `common.py`
- `misc.py`

Do not create abstractions merely to make code look architectural.

### Layer Boundaries

- **Configuration Layer**: Environment and application configuration belong strictly in `kontexa.core.config`.
- **Database Layer**: Data access logic belongs strictly in `kontexa.database`.
- **API Handlers**: HTTP endpoints must parse requests, delegate work, and return responses without containing complex business logic.
- **Retrieval Logic**: Context and knowledge retrieval operations must remain read-only.
- **LLM/Vendor Isolation**: Third-party provider SDKs (OpenAI, Anthropic, etc.) must be isolated behind domain interfaces. Vendor-specific details must not leak into business logic.
- **Frontend & Backend**: Frontend communicates with backend through explicitly defined RESTful API schemas.

---

## 4. Error Handling & Logging

- **Policy**: Tolerant at clearly defined external-input boundaries, strict internally.
- **Validation**: Validate all incoming payload parameters at the API edge using Pydantic models.
- **No Swallowed Exceptions**: Never silently catch exceptions. Never use:
  ```python
  except Exception:
      pass
  ```
- **Logging**: Use standard Python `logging` module. Never use `print()` for runtime diagnostics.

---

## 5. Comments & Docstrings

- Comments must explain **why** something was done, not **what** the code does.
- Bad:
  ```python
  # Increment counter
  counter += 1
  ```
- Good:
  ```python
  # Count rejected records so ingestion reports data loss explicitly.
  rejected += 1
  ```
- **No Planning References**: Never reference temporary planning identifiers in source code (e.g., `Phase 3`, `Task 7`, `Sprint 2`, `D12`). Code must remain self-explanatory regardless of project management history.
- **Docstrings**: Public functions and classes must have concise docstrings detailing purpose, key parameters, return values, side effects, and constraints. Avoid repeating function names verbatim.

---

## 6. Security

- **Secrets**: Never hardcode API keys, database credentials, or tokens in source code. Use environment variables.
- **SQL Queries**: Always use parameterized queries or SQLAlchemy ORM abstractions. Never construct SQL queries via string formatting or concatenation.
- **Logging Safety**: Never log sensitive data, auth tokens, passwords, or personal credentials.

---

## 7. Naming Conventions

- **Python**: `snake_case` for variables, functions, and modules.
- **Classes**: `PascalCase` for Python classes and TypeScript interfaces/components.
- **Constants**: `SCREAMING_SNAKE_CASE` for global constants.
- **TypeScript**: `camelCase` for variables, functions, and properties.
- **Tests**: Descriptive test names that explain expected behavior (e.g., `test_invalid_project_id_is_rejected`).

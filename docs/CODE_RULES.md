# Code Rules & Engineering Standards

This document defines mandatory coding standards and practices for Kontexa. All engineers and AI coding agents must adhere to these rules.

---

## 1. Simplify First

Before writing code, ask:
- Does this need to exist?
- Is there already a standard-library or project solution?
- Can the design be simpler with fewer moving parts?
- Am I solving a real requirement or adding speculative abstraction?

Prefer simple, readable solutions over clever code. Duplication is preferable to premature or wrong abstraction.

---

## 2. Python Standards & Tooling

- **Target Runtime**: Python 3.12+
- **Line Length**: 100 characters maximum.
- **Linting & Formatting**: Enforced via Ruff (`uv run ruff check .` and `uv run ruff format .`).
- **Dependency Management**: Managed exclusively through `uv`. Never use raw `pip install` to modify project dependencies.
- **Type Annotations**: Mandatory type hints on all public functions, arguments, and return types using modern syntax (`list[str]`, `str | None`).
- **Pydantic**: Use Pydantic v2 schemas for all external inputs and API responses.

---

## 3. TypeScript & Next.js Standards

- **Target Runtime**: Node.js 20+, Next.js 16 App Router, React 19, TypeScript 5.
- **Linting & Type Checking**: Enforced via ESLint (`npm run lint`) and TypeScript (`npm run typecheck`).
- **Formatting**: 2-space indentation.
- **Components**: Functional components with explicit TypeScript interfaces for props. Keep components focused; separate data fetching from presentation.
- **Secrets**: Never prefix internal secrets or API tokens with `NEXT_PUBLIC_`.

---

## 4. Module Boundaries & Layer Responsibilities

Each module must have a single, clearly defined responsibility. Avoid generic dumping-ground files (`utils.py`, `helpers.py`, `common.py`).

- **Configuration Layer**: Environment and settings belong strictly in `kontexa.core.config`.
- **Database Layer**: SQLAlchemy models, sessions, and data access belong in `kontexa.database`.
- **API Handlers**: Route handlers parse requests, enforce auth dependencies, delegate to services, and return schemas. Handlers must not contain complex business logic.
- **AI/LLM Boundary**: Third-party provider SDKs (OpenAI, Anthropic, Gemini) must remain behind the internal `AIGateway` interface. Vendor-specific types must not leak into domain logic.
- **Retrieval Logic**: Knowledge and code retrieval operations must remain strictly read-only.

---

## 5. Error Handling & Logging

- **Validation at the Edge**: Validate all incoming parameters with Pydantic schemas.
- **No Swallowed Exceptions**: Never use bare `except:` or `except Exception: pass`. Catch specific exceptions and log or raise.
- **Structured Logging**: Use Python's standard `logging` module. Never use `print()` for runtime diagnostics.
- **Information Hiding**: Do not leak raw database exception details, credentials, or internal IPs to API clients.

---

## 6. Comments, Docstrings & Planning References

- **Explain Why, Not What**: Comments must explain the reasoning or constraint, not recite what the code does.
- **Docstrings**: Public functions and classes must have concise docstrings detailing purpose, parameters, return values, and side effects.
- **No Planning References in Code**: Never reference temporary sprint or phase identifiers in source code (e.g., `Sprint 1`, `Phase 3`, `Task 4`). Code must remain evergreen and self-explanatory regardless of sprint history.

---

## 7. Security Rules

- **Secrets**: Never commit `.env` files, API keys, database credentials, or tokens.
- **SQL Queries**: Always use parameterized queries or SQLAlchemy ORM abstractions. Never construct SQL via string concatenation or formatting.
- **External Data**: Always treat retrieved code or document content as untrusted input.

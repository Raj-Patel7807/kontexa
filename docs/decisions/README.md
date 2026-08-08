# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for Kontexa. ADRs capture important architectural choices, technical context, and trade-offs made over the lifetime of the project.

## When to write an ADR

Write an ADR when making significant architectural choices, such as:
- Selecting or swapping core database technologies
- Introducing major internal boundaries or frameworks
- Changing data access, state management, or security paradigms
- Adding major third-party integrations or infrastructure components

## ADR File Naming & Location

File naming format: `XXXX-short-title.md` (e.g., `0001-modular-monolith-architecture.md`).

## ADR Template

```markdown
# ADR-XXXX — Decision Title

## Status

[ Proposed | Accepted | Deprecated | Superseded ]

## Context

Describe the problem, requirements, technical constraints, and background drivers that necessitate this decision.

## Decision

State the choice made and technical approach chosen to solve the issue.

## Consequences

Detail the trade-offs, positive outcomes, potential risks, and maintenance implications resulting from this decision.
```

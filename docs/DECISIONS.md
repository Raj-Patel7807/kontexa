# Architecture Decisions

This document records the project's current architectural decisions. It is intentionally concise,
but each entry explains the choice and its practical effect. Update it when a material decision
changes.

## Modular monolith backend

Kontexa keeps its backend domains in one FastAPI application rather than splitting into services.
This keeps deployment and local development simple while requiring clear internal module boundaries.
Separate services should be considered only when a concrete scaling, isolation, or operational need
appears.

## PostgreSQL with pgvector

PostgreSQL is the primary persistent store for relational data. pgvector is used for the planned
document-embedding and retrieval capability, which keeps structured and vector data in one database.
Alembic remains the schema evolution source of truth; the Aiven SQL file is only for bootstrapping a
new empty database.

## Targeted Redis usage

Redis is reserved for short-lived responsibilities such as caching, sessions, rate limiting, or
queues when a feature justifies it. PostgreSQL remains the persistent system of record. Currently,
Redis is used only by the readiness check.

## Monorepo and local Docker Compose

The Next.js frontend and FastAPI backend live in one repository because they currently evolve
together. Docker Compose provides the local full stack: PostgreSQL, Redis, backend, and frontend.
This does not make a hosted deployment choice for the project.

## Provider-independent AI boundary

Future AI features must use an internal provider boundary instead of calling vendor SDKs directly
from product logic. This keeps the product independent of a specific AI vendor and makes provider
changes easier. It does not imply that AI provider, streaming, or tool features are implemented.

See [ARCHITECTURE.md](ARCHITECTURE.md), [DATABASE.md](DATABASE.md), and [ROADMAP.md](ROADMAP.md)
for the corresponding current behavior and planned direction.

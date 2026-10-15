# Delivery Roadmap

## Milestone 1: Foundations
- Core system architecture and blackbox harness.

## Shipped (migrated from legacy `.claude_docs/`)
- PRD-0001 Amazon Prime Watch History Import (TASK-0002 – TASK-0007)
- PRD-0002 Manual Movie Search in Import Wizard
- PRD-0003 Auto-Logout on 401 Unauthorized
- PRD-0004 MovieCard Layout Redesign

## Wave 1: Foundations (proposed, TASK-0008 to TASK-0027)
- PRD-0006 Platform Foundations: frontend lint/type/mock gates (TASK-0008 to TASK-0010), dead code and token cleanup (TASK-0011 to TASK-0013), backend duplication fixes (TASK-0014 to TASK-0017), PostgreSQL in CI per ADR-0007 (TASK-0018, TASK-0021, TASK-0022), datetime conversion per ADR-0010 (TASK-0019, TASK-0020), movie identity (TASK-0023, TASK-0024), persisted import sessions (TASK-0025).
- PRD-0008 Rewatch History (shaped): watches table and write path per ADR-0011 (TASK-0026, TASK-0027).
- Migration order is serialized through task dependencies: 007 genres drop (TASK-0011), 008 datetime (TASK-0020), 009 movie dedupe (TASK-0024), 010 import_sessions (TASK-0025), 011 watches (TASK-0026).

## Wave 2: Safety and operations (proposed, TASK-0028 to TASK-0047)
- PRD-0007 Operational Safety: redirect allowlist (TASK-0028), secrets in SSM per ADR-0008 (TASK-0029 to TASK-0031), CI-gated deploys with migrations and infrastructure in the pipeline per ADR-0009 (TASK-0032 to TASK-0034), throttling (TASK-0035, TASK-0036), observability (TASK-0037 to TASK-0039), dependency pinning and scanning (TASK-0040, TASK-0041), httpOnly cookie sessions per ADR-0013 (TASK-0045 to TASK-0047).
- PRD-0006 (continued): OpenAPI-generated TypeScript types per ADR-0012 (TASK-0042 to TASK-0044).

Later waves (not yet planned): BDD/e2e expansion (ADR-0006), product features (Import v2, export, notes and tags), UI refresh.

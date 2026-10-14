# Implement Feature or Task

Route implementation work to the appropriate domain expertise and execute.

## What to Implement

$ARGUMENTS

## Instructions

1. **Identify Context**

   Check if this is:
   - A task from `docs/project/backlog/{proposed,refined}/NNNN-{slug}-{name}.md`
   - A feature from `docs/project/product/*/prd-NNNN-{slug}.md`
   - A direct implementation request

2. **Determine Domain**

   | Domain | Indicators | Focus |
   |--------|------------|-------|
   | **Backend** | Models, APIs, FastAPI, services | `backend-implementation` patterns |
   | **Frontend** | React, components, state, UI | `frontend-implementation` patterns |
   | **Infrastructure** | AWS, CDK, Lambda, infrastructure | `infrastructure-implementation` patterns |
   | **Migrations** | Schema changes, data backfill | Alembic migrations in `alembic/` (see `app/CLAUDE.md`) |
   | **Testing** | Test coverage, fixtures | `test-coverage` patterns |
   | **Security** | Auth, permissions, sensitive data | `security-review` review |

3. **Load Context**

   If implementing a documented task:
   - Read the task file for scope and acceptance criteria
   - Read related FRD sections
   - Check refinement notes for implementation guidance

4. **Execute Implementation**

   Follow domain-specific patterns from the appropriate agent:

   **Backend (FastAPI)**:
   - Use Pydantic models for validation
   - SQLAlchemy models with proper relationships
   - Business logic in services, not route handlers
   - Dependency injection for auth and DB sessions

   **Frontend (React)**:
   - Functional components with hooks
   - TypeScript interfaces for props
   - State management with React Context (no Redux)
   - React Testing Library for tests

   **DevOps (AWS CDK)**:
   - Infrastructure as code
   - Least privilege IAM policies
   - Proper resource tagging

5. **Verify Implementation**

   Run appropriate checks:
   ```bash
   # Backend (repo root)
   venv/bin/pytest <path> -x

   # Frontend (inside frontend/)
   npm run lint
   npm run test:run

   # SpecOps invariants (file length < 500 lines, PRIORITY.md sync)
   spec-ops health
   ```

6. **Update Task Status**

   If implementing a tracked task:
   - Do not edit `docs/project/backlog/` on a feature branch (ADR-0005); the move to `complete/` and the `PRIORITY.md` update happen on integration (`spec-ops queue complete <task-id>`)
   - Note any handoff requirements for next task

7. **Report Completion**
   - List files created/modified
   - Note any issues encountered
   - Identify next steps or handoffs

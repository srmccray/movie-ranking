---
name: frd-creator
description: Create FRDs or Quick Sketches for feature requests. Use after triage to document requirements before implementation.
model: inherit
color: green
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Bash
---

# FRD Creator Agent

**Purpose:** Creates feature requirements at the appropriate depth based on the tier assigned by Request Triage. In this project, an "FRD" or "Quick Sketch" is a SpecOps PRD (`PRD-NNNN`) stored under `docs/project/product/`; the tier controls how much technical detail goes into it.

## When Invoked

- **SMALL tier:** Create a Quick Sketch (a short PRD)
- **MEDIUM tier:** Create a standard PRD with a Technical Approach section
- **LARGE tier:** Create a comprehensive PRD with extended sections
- **TRIVIAL tier:** No document; go straight to implementation

---

## Artifact Locations

All artifacts go under `docs/project/` (SpecOps layout; see root CLAUDE.md "Documentation Structure"):

```
docs/project/                          # SpecOps project-management-as-code tree
├── product/                           # PRDs (create with `spec-ops prd create`)
│   ├── idea/ shaped/ accepted/        #   lifecycle stages
│   ├── shipped/                       #   delivered features
│   └── REGISTRY.md
│       # prd-NNNN-{feature-slug}.md: YAML frontmatter + Who/Cannot-do-today/
│       # What-good-looks-like/Non-goals/Checkable Outcomes; refinement notes
│       # go in a `## Refinement Notes` section of the same PRD
├── backlog/                           # Tasks (TASK-NNNN), frontmatter `governing_prds`
│   ├── proposed/ refined/ complete/   #   NNNN-{feature-slug}-{name}.md (refactors: TASK-REFACTOR-*.md)
│   ├── PRIORITY.md                    #   execution order (replaces tasks/_index.md)
│   └── ROADMAP.md
├── user_stories/                      # Personas + Gherkin user stories (US-NNNN)
│   ├── PERSONAS.md  REGISTRY.md
│   └── accepted/us-NNNN-{slug}.md
├── adrs/                              # Architecture Decision Records
│   ├── accepted/adr-NNNN-{slug}.md
│   └── REGISTRY.md
└── archive/                           # Completed/legacy documentation
    ├── plans/                         # Legacy plans (read-only history)
    └── docs/                          # Legacy docs (read-only history)
```

---

## Creating the PRD

All tiers start the same way. Do not hand-allocate IDs; let the CLI do it.

```bash
spec-ops prd create --title "{Title}" --persona "{Persona}" --component "{component}" \
  --summary "{one-line problem statement}" --stage {idea|shaped|accepted}
spec-ops prd lint docs/project/product/{stage}/prd-NNNN-{slug}.md
```

- Personas are defined in `docs/project/user_stories/PERSONAS.md` (e.g. Casey, the movie enthusiast, for end-user features).
- Components come from `specops.toml`: `backend`, `frontend`, `infra` (existing PRDs also use bounded-context names such as `import`, `auth`, `rankings`).
- Every PRD must have the mandatory sections below with falsifiable Checkable Outcomes (observable through a public frontdoor: an HTTP endpoint response or rendered UI, per ADR-0003).
- Each PRD also needs at least one Gherkin user story (ADR-0006): `spec-ops story create --title "..." --prd PRD-NNNN --persona "..."` creates `docs/project/user_stories/accepted/us-NNNN-{slug}.md`.
- Check available flags with `spec-ops <command> --help` if a command differs from the above.

### Mandatory PRD sections (all tiers)

```markdown
---
id: 'NNNN'
title: {Title}
status: Idea | Shaped | Accepted | Shipped
created: {YYYY-MM-DD}
target_persona: {Persona}
component: {component}
---

# PRD-NNNN — {Title}

## Who this is for
## What the person cannot do today
## What good looks like
## What this does not do
## Checkable Outcomes
1. {Falsifiable, observable outcome}
## Linked User Stories
- [US-NNNN: {title}](../../user_stories/accepted/us-NNNN-{slug}.md)
```

The CLI scaffold is authoritative if it differs from this sketch.

---

## SMALL Tier: Quick Sketch

For low-complexity, low-risk work. Use the mandatory sections only, plus a short technical note:

```markdown
## Technical Note
- **Approach:** {2-4 steps}
- **Files likely affected:** `{app/routers/...py}`, `{frontend/src/components/...tsx}`
- **Considerations:** {risks, edge cases}
```

Keep Checkable Outcomes to 2-4 items. Triage scores (Complexity X/10, Risk X/10) may be recorded in the PRD body.

---

## MEDIUM Tier: Standard PRD

For moderate complexity or risk. Mandatory sections plus:

```markdown
## Proposed Solution
### Overview
### User Experience

## Technical Approach
### Backend Changes
- Models (`app/models/`), schemas (`app/schemas/`), routers (`app/routers/`), services (`app/services/`)
- API contract: method, path (trailing slash), request/response schema
### Frontend Changes
- Components (`frontend/src/components/`), pages, hooks, API client (`frontend/src/api/client.ts`), types (`frontend/src/types/`)
### Data Model
- New tables/columns (primary keys are UUIDs), Alembic migration in `alembic/versions/`

## Implementation Notes
### Dependencies
### Integration Points

## Testing Strategy
- Backend: pytest through the HTTP API (`tests/`)
- Frontend: Vitest + React Testing Library + MSW (co-located `*.test.tsx`)
- Manual scenarios

## Rollback Plan

## Open Questions
- [ ] {Question}
```

The project has no feature-flag system; do not propose flags unless the feature requires introducing one.

---

## LARGE Tier: Comprehensive PRD

For high-complexity or high-risk work. Everything in the MEDIUM tier, plus the following sections as relevant:

- **Executive Summary**: 2-3 paragraphs for stakeholders.
- **Problem Statement**: current state, pain points, impact, success metrics.
- **Design Principles** and **Alternatives Considered** (table: alternative, pros, cons, why not chosen). Architecture-level decisions should also become an ADR in `docs/project/adrs/accepted/`.
- **Technical Design**: architecture overview; backend models, endpoints table (`| Method | Endpoint | Description |`, all `/api/v1/...` with trailing slashes), services; frontend components and state (React Context, not Redux); database changes with migrations and any data backfill; infrastructure changes (CDK in `infra/lib/`, deployed via GitHub Actions).
- **Risk Assessment**: technical risks (likelihood, impact, mitigation), business risks, security considerations (auth, ownership checks).
- **Implementation Plan**: phases and dependency graph. Phases map to backlog tasks created later by `frd-task-breakdown`.
- **Testing Strategy**: unit, integration, end-to-end (Playwright for UI scenarios per ADR-0006), manual test plan.
- **Deployment Plan**: rollback steps and any new monitoring.
- **Documentation Updates**: affected CLAUDE.md guides and API docs.
- **Open Questions** and **Appendix** (glossary, references).

---

## Process Notes

### Creating the PRD

1. **Start with the problem**, not the solution
2. **Gather context** before writing - search codebase, read related code
3. **Fill sections incrementally** - don't try to complete everything at once
4. **Mark unknowns explicitly** - use `TBD` or add to Open Questions
5. **Respect SpecOps invariants** when scoping: files under 500 lines (ADR-0002), blackbox frontdoor verification (ADR-0003), backlog isolation on feature branches (ADR-0005)
6. **Run `spec-ops prd lint`** on the result

### Naming Conventions

- **Feature slug:** lowercase, hyphenated (e.g., `user-notification-preferences`)
- **PRD:** `docs/project/product/{stage}/prd-NNNN-{slug}.md` (ID allocated by `spec-ops prd create`); refinement notes go in a `## Refinement Notes` section of the same PRD
- **Stories:** `docs/project/user_stories/accepted/us-NNNN-{slug}.md`
- **Tasks:** `docs/project/backlog/proposed/NNNN-{slug}-{name}.md` with frontmatter `governing_prds: [PRD-NNNN]` (created later by `frd-task-breakdown`)
- Do not use the removed `.claude_docs/` paths (`sketch.md`, `frd.md`, `refinement.md`, `task-NN-*.md`)

### Handoff - Next Agent to Invoke

After creating the PRD:
1. Set PRD status to match its stage (`idea`/`shaped` while drafting, `accepted` when ready for refinement or implementation)
2. **End your output with the "Next Agent to Invoke" section** - this is mandatory

**Output format to use:**
```markdown
---

## Next Agent to Invoke

**Agent:** `{agent-name}`

**Context to provide:**
- Feature slug: `{slug}`
- Tier: {SMALL|MEDIUM|LARGE}
- PRD location: `docs/project/product/{stage}/prd-NNNN-{slug}.md`
- {Any key context for the next agent}

**After that agent completes:**
{What to expect from that agent}
```

### Next Agent Selection by Tier

| Tier | Next Agent | Notes |
|------|------------|-------|
| SMALL | `backend-implementation` or `frontend-implementation` | Quick Sketch is sufficient, go directly to implementation |
| MEDIUM | `frd-refiner` | Light refinement before implementation |
| LARGE | `frd-refiner` | Thorough refinement required, then `frd-task-breakdown` |

The parent session invokes the recommended agent, continuing the workflow chain.

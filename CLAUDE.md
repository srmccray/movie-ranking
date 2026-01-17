# Movie Ranking Project

This document defines project-wide conventions that apply across the entire codebase. For domain-specific guidance, see the detailed guides in each directory.

## Detailed Guides

| Guide | Purpose |
|-------|---------|
| [`frontend/CLAUDE.md`](frontend/CLAUDE.md) | React/TypeScript development, components, hooks, styling |
| [`app/CLAUDE.md`](app/CLAUDE.md) | FastAPI backend, models, schemas, routers, migrations |
| [`infra/CLAUDE.md`](infra/CLAUDE.md) | AWS CDK infrastructure, CloudFront, Lambda, deployment |

## Critical Conventions

### Trailing Slashes (MUST FOLLOW)

**All API endpoints use trailing slashes.** This is critical for FastAPI's redirect behavior and CORS compatibility.

```python
# Backend - Correct
@router.post("/")
@router.delete("/{ranking_id}/")

# Backend - Wrong (causes 404/redirect errors)
@router.delete("/{ranking_id}")
```

```typescript
// Frontend - Correct
await fetch(`/api/v1/rankings/${id}/`, { method: 'DELETE' });

// Frontend - Wrong
await fetch(`/api/v1/rankings/${id}`, { method: 'DELETE' });
```

### DateTime Handling

**Strategy: Naive UTC.** The database uses `TIMESTAMP WITHOUT TIME ZONE`. All datetimes are stored as naive UTC.

| Layer | Format |
|-------|--------|
| Frontend sends | ISO 8601 with timezone: `new Date().toISOString()` |
| Backend converts | Naive UTC before storage |
| Database stores | `TIMESTAMP WITHOUT TIME ZONE` |

```python
# Backend conversion (app/routers/*.py)
def to_naive_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
```

### HTTP Status Codes

| Code | Usage |
|------|-------|
| `200` | Successful update/read |
| `201` | Successful creation |
| `204` | Successful deletion (no content) |
| `401` | Not authenticated |
| `403` | Not authorized (wrong user) |
| `404` | Resource not found |
| `422` | Validation error |

## API Contract Verification

**Critical:** Frontend and backend types must match exactly. Runtime errors occur when they don't.

### Common Pitfall

```typescript
// Backend returns: { results: [...], query: "...", year: null }

// WRONG - Frontend assumes raw array
async searchMovies(): Promise<SearchResult[]> {
  return this.request<SearchResult[]>('/search/');  // Runtime error!
}

// CORRECT - Frontend matches backend wrapper
async searchMovies(): Promise<SearchResult[]> {
  const response = await this.request<SearchResponse>('/search/');
  return response.results;
}
```

### Verification Checklist

- [ ] Read backend schema (`app/schemas/*.py`) before implementing frontend types
- [ ] Check `response_model=` in router to see exact response shape
- [ ] Wrapper responses (`*ListResponse`, `*SearchResponse`) contain data in a field like `items` or `results`
- [ ] Field names use `snake_case` (matching Python/JSON convention)

For detailed patterns, see:
- `frontend/CLAUDE.md` - "API Contract Verification" section
- `app/CLAUDE.md` - "Frontend API Contract Documentation" section

## Documentation Structure

All project documentation is stored in `.claude_docs/`:

```
.claude_docs/
├── features/                    # Feature Requirements Documents (FRDs)
│   └── {feature-slug}/
│       ├── sketch.md            # SMALL tier (quick sketch)
│       ├── frd.md               # MEDIUM/LARGE tier (full FRD)
│       └── refinement.md        # Refinement notes
├── tasks/                       # Task breakdowns for features
│   └── {feature-slug}/
│       ├── _index.md            # Master task list with dependencies
│       └── task-{n}-{name}.md   # Individual tasks
├── decisions/                   # Architecture Decision Records
│   └── ADR-{n}-{slug}.md
└── archive/                     # Completed/legacy documentation
    ├── plans/                   # Old .claude/plans/ content
    └── docs/                    # Old docs/ content
```

## Agent Workflow

Specialized agents handle different aspects of development. See `.claude/agents/` for agent definitions.

### Feature Development Tiers

| Tier | Process |
|------|---------|
| TRIVIAL | Direct implementation |
| SMALL | Quick Sketch -> Implementation |
| MEDIUM | FRD -> Light Refinement -> Implementation |
| LARGE | FRD -> Thorough Refinement -> Task Breakdown -> Implementation |

### Key Agents

| Agent | Purpose |
|-------|---------|
| `request-triage` | Categorizes requests and determines workflow |
| `frd-creator` | Creates Feature Requirements Documents |
| `frd-refiner` | Refines FRDs against codebase patterns |
| `frd-task-breakdown` | Breaks features into implementable tasks |
| `backend-implementation` | Implements backend features |
| `frontend-implementation` | Implements frontend features |
| `test-coverage` | Adds/improves test coverage |
| `documentation-writer` | Creates/updates documentation |

## Git Conventions

- Do NOT include "Co-Authored-By: Claude" or any Claude attribution in commit messages
- Keep commit messages concise and descriptive
- Use present tense ("Add feature" not "Added feature")

## Before Implementing New Features

### Checklist

- [ ] Examine 3+ similar implementations in the codebase
- [ ] Review the relevant detailed guide (`frontend/CLAUDE.md` or `app/CLAUDE.md`)
- [ ] Verify trailing slash convention matches existing endpoints
- [ ] Match datetime handling patterns (naive UTC conversion)
- [ ] Plan API contracts before implementing (check both frontend types and backend schemas)
- [ ] Write integration tests with realistic frontend requests

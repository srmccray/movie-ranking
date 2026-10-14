# Feature Status Report

Check the status of a feature or all in-flight features.

## Feature to Check

$ARGUMENTS

## Instructions

1. **Locate Feature Artifacts**

   If a specific feature slug is provided:
   - Check `docs/project/product/*/prd-NNNN-{slug}.md` for FRD/sketch
   - Check `docs/project/backlog/{proposed,refined,complete}/` for tasks with `governing_prds: [PRD-NNNN]` in their frontmatter (task breakdown)
   - Report what exists and current state

   If no slug provided:
   - Scan `docs/project/product/` for all features
   - Report summary of all in-flight work

2. **Determine Current Phase**

   | Phase | Indicators |
   |-------|------------|
   | Triage | No artifacts yet |
   | FRD | PRD exists in `docs/project/product/{idea,shaped,accepted}/`, no `## Refinement Notes` section |
   | Refinement | PRD has a `## Refinement Notes` section, or refinement is in progress |
   | Breakdown | Tasks citing the PRD exist in `docs/project/backlog/` (`proposed/` or `refined/`) |
   | Implementation | Task work is in progress on a `feat/` branch or worktree |
   | Complete | All tasks are in `docs/project/backlog/complete/` (PRD in `shipped/`) |

3. **Generate Status Report**

   ```markdown
   ## Status: {Feature Name}

   **Tier:** {TRIVIAL|SMALL|MEDIUM|LARGE}
   **Phase:** {triage|frd|refinement|breakdown|implementation|complete}
   **Health:** On Track | At Risk | Blocked

   ### Artifacts
   - [ ] Triage complete
   - [x] FRD/Sketch created: `docs/project/product/accepted/prd-NNNN-{slug}.md`
   - [ ] Refinement complete
   - [ ] Task breakdown complete
   - [ ] Implementation complete

   ### Task Progress (if applicable)
   | # | Task | Status |
   |---|------|--------|
   | 01 | {task} | Complete |
   | 02 | {task} | In Progress |
   | 03 | {task} | Blocked by 02 |

   ### Blockers
   - {Any blocking issues}

   ### Next Actions
   1. {Recommended next step}
   ```

4. **For Multiple Features**

   ```markdown
   ## In-Flight Features

   | Feature | Tier | Phase | Health |
   |---------|------|-------|--------|
   | {name} | MEDIUM | Implementation | On Track |
   | {name} | LARGE | Refinement | At Risk |

   ### Recommended Focus
   {Which feature to prioritize and why}
   ```

# Project Management as Code (PMaC)

movie-ranking uses SpecOps to version-lock all project specifications directly in git.

## Why Specification as Code?
1. **Zero Context Drift**: Specifications, user stories, and tasks live in the exact same git commit history as implementation code.
2. **Thin Vertical Slicing**: Features are built through single-pass vertical slices rather than speculative horizontal layers.
3. **Hard Invariants**: Source files remain strictly under 500 lines to prevent monolithic file rot. Files that already exceeded the limit when SpecOps was adopted are grandfathered in `specops.toml` and `.specops/grandfathered_debt.json`, and tracked for decomposition in `docs/project/backlog/`.

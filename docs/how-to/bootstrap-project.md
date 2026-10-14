# How-To: Bootstrap a SpecOps Project

This recipe walks you through bootstrapping a new project with opinionated PMaC invariants and Diataxis documentation. movie-ranking itself was brought under SpecOps with `spec-ops adopt` (existing oversized files are grandfathered in `specops.toml`), so you do not need to run this here.

## Running Init
```bash
spec-ops init --name "MySystem" --diataxis
```

## Adopting an Existing Codebase
```bash
spec-ops adopt --name "MySystem" --grandfather-debt
```

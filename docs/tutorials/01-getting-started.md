# Getting Started with movie-ranking

Welcome to movie-ranking! This tutorial guides you through setting up your environment and verifying project health with SpecOps.

## Prerequisites
- Python 3.11+ (CI uses 3.13)
- Node.js and npm (for `frontend/`)
- Git
- The `spec-ops` CLI. CI installs it pinned from GitHub, and you can do the same locally with [uv](https://docs.astral.sh/uv/):
  ```bash
  uv tool install "git+https://github.com/tyevans/spec-ops@9745c40"
  ```

## Step 1: Install Dependencies
Backend (from the repository root):
```bash
python3 -m venv venv
venv/bin/pip install -r requirements-dev.txt
```

Frontend:
```bash
cd frontend && npm install
```

## Step 2: Run the Tests
```bash
venv/bin/pytest
cd frontend && npm run test:run
```

## Step 3: Verify System Health
Run the SpecOps invariant scanner:
```bash
spec-ops health
```

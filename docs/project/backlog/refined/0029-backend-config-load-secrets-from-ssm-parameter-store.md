---
id: 0029
title: 'app/config.py: load secrets from SSM Parameter Store at cold start when SSM_PARAMETER_PREFIX
  is set'
status: Refined
governing_adrs:
- ADR-0008
- ADR-0003
governing_prds:
- PRD-0007
governing_stories:
- US-0009
target_bc: backend
---

# TASK-0029: app/config.py: load secrets from SSM Parameter Store at cold start when SSM_PARAMETER_PREFIX is set

## Summary
ADR-0008 moves production secrets out of the Lambda environment. The application side comes first and is backward compatible: when `SSM_PARAMETER_PREFIX` is set, `Settings` reads `DATABASE_URL`, `SECRET_KEY`, `TMDB_API_KEY`, `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from SSM; environment variables and `.env` keep taking precedence, so nothing changes until infrastructure (TASK-0030) sets the prefix.

Priority: P1. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- `app/config.py:6-47`: `class Settings(BaseSettings)` with `model_config = SettingsConfigDict(env_file=".env", ...)` and a module-level `settings = Settings()` at line 47. `DATABASE_URL`, `SECRET_KEY` and `TMDB_API_KEY` have no defaults, so a missing value fails at import.
- Add a custom settings source via `settings_customise_sources` that, if `os.environ.get("SSM_PARAMETER_PREFIX")` is set, calls SSM `get_parameters_by_path(Path=prefix, WithDecryption=True, Recursive=False)` once (paginated) and returns `{name_without_prefix: value}`. Source order (highest first): init kwargs, environment, `.env`, SSM, field defaults. Import `boto3` lazily inside the source so local runs, tests and Docker never import it.
- Fail loudly: if the prefix is set and a required field is still missing, the existing pydantic validation error must be preceded by a log line naming the prefix and the missing keys; if SSM itself fails, raise a `RuntimeError` that names the prefix (do not fall back silently).
- Cold-start cost is one SSM call, cached because `settings` is a module-level singleton (Mangum reuses the module across invocations in a warm container).
- Tests: use an injectable client factory (a module-level function `_ssm_client()` that the test replaces) so the SSM network boundary is stubbed without patching internals; cover precedence (env beats SSM), missing parameter error, pagination (two pages) and 'prefix unset never imports boto3'.
- Dependencies: `boto3` is provided by the Lambda Python runtime, so do not add it to `requirements.txt` (it would add about 70 MB to the zip). Add it to the `dev` extras in `pyproject.toml` and to the `pip install` line in `.github/workflows/ci.yml` so tests can import it, and add a `boto3` entry (Apache-2.0) to `docs/project/compliance/licenses.json` for the dependency audit.

## Notes and Risks
- Parameter names are the setting names (`/movie-ranking/prod/DATABASE_URL`, ...). `GOOGLE_REDIRECT_URI` and `CORS_ORIGIN` are not secrets and stay in the function environment.
- `lifespan="off"` in `lambda_handler.py` is unaffected; configuration loads at import time.
- Never log parameter values.

## Definition of Done
- [ ] With `SSM_PARAMETER_PREFIX` unset the full test suite behaves exactly as before and `boto3` is not imported (asserted by a test).
- [ ] With a stubbed SSM returning the five parameters, `Settings()` populates them; an environment variable of the same name wins.
- [ ] A missing required parameter produces an error that names the prefix and the missing key without printing any value.
- [ ] `docs/project/compliance/licenses.json` contains a `boto3` entry and `spec-ops audit dependencies` passes.

```gherkin
Scenario: Secrets come from SSM when a prefix is configured
  Given SSM_PARAMETER_PREFIX is /movie-ranking/prod/ and SSM holds SECRET_KEY and DATABASE_URL
  And no SECRET_KEY environment variable is set
  When the application starts
  Then settings.SECRET_KEY equals the SSM value
  And an environment variable SECRET_KEY would override it
```

## INVEST Criteria
- **Independent**: No task dependencies; executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Lets production run without plaintext secrets in function configuration; ADR-0008, PRD-0007 outcome 1, US-0009.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: Behavior verified by starting settings with a stubbed SSM boundary (ADR-0003 allows stubbing external network services).

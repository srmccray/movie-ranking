"""Export the FastAPI OpenAPI document without a server or database (ADR-0012)."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Dummy settings so app.main imports; the engine is built but never connects.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "openapi-export-dummy-secret")
os.environ.setdefault("TMDB_API_KEY", "openapi-export-dummy-key")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / "frontend" / "openapi.json"))
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))
    from app.main import app

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

"""Export the FastAPI OpenAPI schema without starting a server."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from hmde.main import app


def build_openapi() -> dict[str, Any]:
    return app.openapi()


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the HMDE OpenAPI schema.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("../openapi.json"),
        help="Destination path for the generated schema.",
    )
    args = parser.parse_args()

    schema = build_openapi()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    print(f"Wrote OpenAPI schema to {args.output}")


if __name__ == "__main__":
    main()

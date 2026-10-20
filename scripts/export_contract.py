#!/usr/bin/env python
"""Export OpenAPI contract and generate TypeScript types"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from drf_spectacular.generators import SchemaGenerator  # noqa: E402


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    contract_dir = project_root / "contract"
    contract_dir.mkdir(parents=True, exist_ok=True)

    # Generate OpenAPI schema
    print("Generating OpenAPI schema...")
    generator = SchemaGenerator()
    schema = generator.get_schema(request=None, public=True)

    openapi_file = contract_dir / "openapi.json"
    with openapi_file.open("w") as f:
        json.dump(schema, f, indent=2)

    print(f"OpenAPI schema written to {openapi_file}")

    # Generate TypeScript types using openapi-typescript
    print("Generating TypeScript types...")
    web_contract_dir = project_root.parent / "web" / "src" / "contract"
    web_contract_dir.mkdir(parents=True, exist_ok=True)

    ts_output = web_contract_dir / "api.ts"

    try:
        result = subprocess.run(
            [
                "pnpm",
                "exec",
                "openapi-typescript",
                str(openapi_file),
                "--output",
                str(ts_output),
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=project_root.parent / "web",
        )
        print(f"TypeScript types written to {ts_output}")
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error generating TypeScript types: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)

    # Create contract.lock with schema hash
    import hashlib

    schema_hash = hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()[:16]
    lock_file = contract_dir / "contract.lock"
    lock_data = {"schema_hash": schema_hash, "version": "1.0.0"}
    with lock_file.open("w") as f:
        json.dump(lock_data, f, indent=2)

    print(f"Contract lock written to {lock_file}")
    print("Contract export complete!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Export permissions to contract/fixtures/permissions.json"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

import django

django.setup()

from apps.shops.domain.permissions import export_permissions_json  # noqa: E402


def main() -> None:
    output_dir = Path(__file__).resolve().parent.parent / "contract" / "fixtures"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "permissions.json"
    data = export_permissions_json()

    with output_file.open("w") as f:
        json.dump(data, f, indent=2)

    print(f"Exported permissions to {output_file}")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()

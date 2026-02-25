#!/usr/bin/env python3

import os
import re
import sys
from pathlib import Path


def main() -> int:
    ref = os.getenv("GITHUB_REF_NAME", "")
    m = re.fullmatch(r"v(\d+\.\d+\.\d+)", ref)
    if not m:
        print(f"Skip: not a semver tag: {ref}")
        return 0

    version = m.group(1)

    root = Path(__file__).resolve().parents[1]
    files = {
        "README.md": root / "README.md",
        "PRIVACY_POLICY.md": root / "PRIVACY_POLICY.md",
        "CHANGELOG.md": root / "CHANGELOG.md",
        "webapp/api.py": root / "webapp" / "api.py",
    }

    missing = []
    for name, path in files.items():
        if not path.exists():
            missing.append(f"{name}: not found")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if version not in text:
            missing.append(f"{name}: does not contain {version}")

    if missing:
        print("Version check failed:")
        for item in missing:
            print("-", item)
        return 1

    print(f"OK: version {version} present in ключових файлах")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

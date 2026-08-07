#!/usr/bin/env python3
"""Version consistency check.

`docs/architecture/versioning.md` is the single source of truth for release identity. This script
reads the declared `Release` value from that table and verifies every component source reports the
same product version. Exit 0 if all match, 1 otherwise.

Run:  python scripts/check_versions.py
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

def read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")

# --- source of truth: the "| Release | X.Y.Z |" row in versioning.md ---
VERSIONING = "docs/architecture/versioning.md"
m = re.search(r"^\|\s*Release\s*\|\s*([0-9]+\.[0-9]+\.[0-9]+)\s*\|", read(VERSIONING), re.M)
if not m:
    print(f"FAIL: could not find the declared Release version in {VERSIONING}")
    sys.exit(1)
EXPECTED = m.group(1)

# --- component sources: (label, path, regex capturing the version) ---
CHECKS = [
    ("backend FastAPI app",     "backend/app.py",
        r'FastAPI\([^)]*version\s*=\s*"([0-9.]+)"'),
    ("backend RUNTIME_VERSION",  "backend/routes/mobile.py",
        r'RUNTIME_VERSION",\s*"([0-9.]+)"'),
    ("desktop package.json",     "bridge/bridge-zero/package.json",
        r'"version":\s*"([0-9.]+)"'),
    ("desktop releaseMetadata",  "bridge/bridge-zero/app/releaseMetadata.js",
        r'VITE_ARCH_VERSION\s*\|\|\s*"([0-9.]+)"'),
    ("frontend package.json",    "frontend/package.json",
        r'"version":\s*"([0-9.]+)"'),
    ("iOS MARKETING_VERSION",    "bridge/bridge-zero-ios/project.yml",
        r'MARKETING_VERSION:\s*([0-9.]+)'),
    ("iOS MobileVersion.current","bridge/bridge-zero-ios/Sources/Models.swift",
        r'static let current\s*=\s*"([0-9.]+)"'),
    ("Android versionName",      "bridge/bridge-zero-android/app/build.gradle.kts",
        r'versionName\s*=\s*"([0-9.]+)"'),
    ("Android MobileVersion",    "bridge/bridge-zero-android/app/src/main/java/arc/omega/bridgezero/Models.kt",
        r'const val CURRENT\s*=\s*"([0-9.]+)"'),
    ("shared OpenAPI",           "bridge/shared/mobile/openapi.yaml",
        r'version:\s*([0-9.]+)'),
    ("shared design-tokens",     "bridge/shared/mobile/design-tokens.json",
        r'"version":\s*"([0-9.]+)"'),
]

print(f"Declared release ({VERSIONING}): {EXPECTED}\n")
failures = 0
for label, rel, pat in CHECKS:
    path = REPO / rel
    if not path.exists():
        print(f"  FAIL  {label:26} - missing file: {rel}")
        failures += 1
        continue
    found = re.search(pat, path.read_text(encoding="utf-8"))
    if not found:
        print(f"  FAIL  {label:26} - no version found in {rel}")
        failures += 1
    elif found.group(1) != EXPECTED:
        print(f"  FAIL  {label:26} - {found.group(1)} (expected {EXPECTED}) in {rel}")
        failures += 1
    else:
        print(f"  ok    {label:26} - {found.group(1)}")

print()
if failures:
    print(f"{failures} component(s) disagree with the declared release {EXPECTED}.")
    sys.exit(1)
print(f"All components report {EXPECTED}.")

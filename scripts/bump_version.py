#!/usr/bin/env python3
"""
Bump the SheepCat version number across all project files.

Usage:
    python scripts/bump_version.py <new_version>

Example:
    python scripts/bump_version.py 1.2.0

Files updated:
    - VERSION
    - installer/SheepCat.iss   (#define MyAppVersion)
    - SheepCat.spec            (not currently versioned — left for future)
"""
import argparse
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VERSION_FILE = os.path.join(REPO_ROOT, "VERSION")
ISS_FILE = os.path.join(REPO_ROOT, "installer", "SheepCat.iss")


def read_current_version() -> str:
    """Read the current version from the VERSION file."""
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def validate_semver(version: str) -> bool:
    """Basic semver validation (major.minor.patch with optional pre-release)."""
    return bool(re.match(r"^\d+\.\d+\.\d+(-[\w.]+)?$", version))


def update_version_file(new_version: str) -> None:
    """Write the new version to the VERSION file."""
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(new_version + "\n")
    print(f"  ✓ VERSION → {new_version}")


def update_iss_file(new_version: str) -> None:
    """Update #define MyAppVersion in the Inno Setup script."""
    with open(ISS_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r'(#define\s+MyAppVersion\s+)"[^"]*"'
    new_content, count = re.subn(pattern, rf'\1"{new_version}"', content)

    if count == 0:
        print(f"  ✗ Could not find MyAppVersion in {ISS_FILE}", file=sys.stderr)
        sys.exit(1)

    with open(ISS_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"  ✓ installer/SheepCat.iss → {new_version}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bump SheepCat version number")
    parser.add_argument("version", help="New version string (e.g. 1.2.0)")
    args = parser.parse_args()

    new_version = args.version.lstrip("v")  # allow "v1.2.0" input

    if not validate_semver(new_version):
        print(f"Error: '{new_version}' is not a valid semver version.", file=sys.stderr)
        sys.exit(1)

    current = read_current_version()
    print(f"Bumping version: {current} → {new_version}\n")

    update_version_file(new_version)
    update_iss_file(new_version)

    print(f"\nDone! Version is now {new_version}")


if __name__ == "__main__":
    main()

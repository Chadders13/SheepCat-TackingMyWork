#!/usr/bin/env python3
"""
Generate release notes from git log.

Usage:
    python scripts/generate_release_notes.py --version 1.2.0 --output RELEASE_NOTES.md

Collects commits since the previous tag and groups them by conventional
commit type (feat, fix, docs, etc.).  Falls back to a flat list if commits
don't follow conventional format.
"""
import argparse
import subprocess
import re
import sys
from datetime import date


# Mapping of conventional commit prefixes → human-readable section titles
SECTIONS = {
    "feat":     "🚀 New Features",
    "fix":      "🐛 Bug Fixes",
    "docs":     "📝 Documentation",
    "style":    "🎨 Style",
    "refactor": "♻️ Refactoring",
    "perf":     "⚡ Performance",
    "test":     "🧪 Tests",
    "build":    "📦 Build",
    "ci":       "📦 CI",
    "chore":    "🔧 Chores",
}

CONVENTIONAL_RE = re.compile(
    r"^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore)"
    r"(?:\((?P<scope>[^)]*)\))?"
    r"!?:\s*(?P<desc>.+)$",
    re.IGNORECASE,
)


def get_previous_tag() -> str | None:
    """Return the tag before the current HEAD tag, or None if there isn't one."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0", "HEAD^"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_commits(since_tag: str | None) -> list[str]:
    """Get commit subject lines since the given tag (or all commits)."""
    if since_tag:
        cmd = ["git", "log", f"{since_tag}..HEAD", "--pretty=format:%s"]
    else:
        cmd = ["git", "log", "--pretty=format:%s"]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return [line for line in result.stdout.strip().splitlines() if line]


def categorise(commits: list[str]) -> dict[str, list[str]]:
    """Group commits by conventional commit type."""
    grouped: dict[str, list[str]] = {}
    uncategorised: list[str] = []

    for msg in commits:
        m = CONVENTIONAL_RE.match(msg)
        if m:
            ctype = m.group("type").lower()
            section = SECTIONS.get(ctype, "🔧 Other")
            scope = m.group("scope")
            desc = m.group("desc").strip()
            entry = f"**{scope}:** {desc}" if scope else desc
            grouped.setdefault(section, []).append(entry)
        else:
            uncategorised.append(msg)

    if uncategorised:
        grouped.setdefault("📋 Other Changes", []).extend(uncategorised)

    return grouped


def render_markdown(version: str, grouped: dict[str, list[str]]) -> str:
    """Render the categorised commits as Markdown."""
    lines = [
        f"# SheepCat v{version}",
        "",
        f"**Released:** {date.today().isoformat()}",
        "",
    ]

    if not grouped:
        lines.append("_No notable changes._")
        return "\n".join(lines)

    # Render in a stable order: features first, then fixes, then the rest
    priority = list(SECTIONS.values())
    seen = set()

    for section in priority:
        if section in grouped and section not in seen:
            seen.add(section)
            lines.append(f"## {section}")
            lines.append("")
            for entry in grouped[section]:
                lines.append(f"- {entry}")
            lines.append("")

    for section, entries in grouped.items():
        if section not in seen:
            lines.append(f"## {section}")
            lines.append("")
            for entry in entries:
                lines.append(f"- {entry}")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("**Full Changelog:** See the commit history for details.")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate release notes")
    parser.add_argument("--version", required=True, help="Release version (e.g. 1.2.0)")
    parser.add_argument("--output", default="RELEASE_NOTES.md", help="Output file")
    args = parser.parse_args()

    version = args.version.lstrip("v")

    prev_tag = get_previous_tag()
    if prev_tag:
        print(f"Collecting commits since {prev_tag}...")
    else:
        print("No previous tag found — collecting all commits...")

    commits = get_commits(prev_tag)
    print(f"Found {len(commits)} commit(s)")

    grouped = categorise(commits)
    markdown = render_markdown(version, grouped)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"Release notes written to {args.output}")


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
#
# Local build & test script for SheepCat (Linux / macOS / Git Bash on Windows)
# Mirrors the GitHub Actions pipeline so you can verify changes locally.
#
# Usage:
#   ./scripts/local_build.sh                # Run everything (tests + lint)
#   ./scripts/local_build.sh test           # Just tests
#   ./scripts/local_build.sh lint           # Just lint
#   ./scripts/local_build.sh all            # Tests + lint (no installer on Linux)
#
# Note: PyInstaller & Inno Setup build steps are Windows-only.
#       This script focuses on test + lint for Linux/macOS contributors.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

STAGE="${1:-all}"
VERSION="$(cat VERSION | tr -d '[:space:]')"

# ── Helpers ──────────────────────────────────────────────────────────────────
header()  { echo -e "\n\033[36m$(printf '=%.0s' {1..70})\n  $1\n$(printf '=%.0s' {1..70})\033[0m\n"; }
success() { echo -e "  \033[32m✓ $1\033[0m"; }
fail()    { echo -e "  \033[31m✗ $1\033[0m"; exit 1; }

# ── Prerequisites ────────────────────────────────────────────────────────────
header "Checking prerequisites"

command -v python3 >/dev/null 2>&1 || fail "python3 not found — install Python 3.11+"
success "python3 found: $(command -v python3)"

echo "  Installing dependencies..."
python3 -m pip install --upgrade pip --quiet
python3 -m pip install -r requirements.txt --quiet

if [[ "$STAGE" == "lint" || "$STAGE" == "all" ]]; then
    python3 -m pip install flake8 --quiet
    success "flake8 installed"
fi

success "Dependencies installed"

# ── Lint ─────────────────────────────────────────────────────────────────────
if [[ "$STAGE" == "lint" || "$STAGE" == "all" ]]; then
    header "Linting (flake8)"

    echo "  Checking for syntax errors and undefined names..."
    python3 -m flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
    success "No syntax errors or undefined names"

    echo ""
    echo "  Style warnings (informational):"
    python3 -m flake8 src/ --count --exit-zero --max-complexity=10 --max-line-length=120 --statistics
    success "Lint complete"
fi

# ── Tests ────────────────────────────────────────────────────────────────────
if [[ "$STAGE" == "test" || "$STAGE" == "all" ]]; then
    header "Running unit tests"

    echo "  test_data_repository..."
    python3 -m unittest test_data_repository -v

    echo ""
    echo "  test_onboarding..."
    python3 -m unittest test_onboarding -v

    success "All tests passed"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "\033[32m$(printf '=%.0s' {1..70})"
echo "  All stages completed successfully! ✓"
echo -e "$(printf '=%.0s' {1..70})\033[0m"
echo ""
echo "  Note: PyInstaller + Inno Setup build is Windows-only."
echo "  Use scripts/local_build.ps1 on Windows for the full pipeline."
echo ""

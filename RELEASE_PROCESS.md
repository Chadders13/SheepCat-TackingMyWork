# Release Process

## Overview

SheepCat uses GitHub Actions for CI/CD. The pipeline runs tests on every PR,
and produces a Windows installer automatically when a release is published.

## Branches

| Branch    | Purpose                                                           |
|-----------|-------------------------------------------------------------------|
| `main`    | Active development. PRs are merged here.                          |
| `release` | **Protected.** Updated automatically by the release workflow.     |
|           | Contains the version-bumped source + built installer executables. |

## How to Cut a Release

### 1. Make sure `main` is green

All tests and lint checks on the `main` branch should be passing.

### 2. Create a GitHub Release

1. Go to **Releases → Draft a new release**
2. Create a **new tag** following semver with a `v` prefix:
   - `v1.0.0`, `v1.1.0`, `v2.0.0-beta.1`
3. Set the **target** to `main`
4. Title the release (e.g. *"SheepCat v1.1.0"*)
5. Click **Publish release**

### 3. The workflow handles the rest

When the release is published, the **Release** workflow automatically:

1. ✅ Runs the full test suite (on Windows)
2. 🔢 Bumps the version number in `VERSION` and `installer/SheepCat.iss`
3. 🔨 Builds the application with PyInstaller
4. 📥 Downloads the Ollama installer
5. 📦 Builds the Windows installer with Inno Setup
6. 📤 Uploads the `.exe` installer to the GitHub Release as a downloadable asset
7. 📝 Auto-generates release notes from commits since the last tag
8. 🚀 Pushes the updated files + installer to the `release` branch

### 4. Users download from Releases

Users can download `SheepCatSetup_X.Y.Z.exe` directly from the
[Releases page](../../releases).

## Version Numbering

We follow **Semantic Versioning** (semver):

- **MAJOR** — breaking changes or major rewrites
- **MINOR** — new features, backwards-compatible
- **PATCH** — bug fixes, backwards-compatible

The single source of truth is the `VERSION` file in the repo root. The
`scripts/bump_version.py` script propagates it to all other files.

### Manual version bump (local development)

```bash
python scripts/bump_version.py 1.2.0
```

## Conventional Commits (Recommended)

For best auto-generated release notes, use conventional commit messages:

```
feat: add dark mode toggle
fix: resolve CSV export encoding issue
docs: update README installation steps
refactor(settings): simplify settings migration logic
```

Supported prefixes: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`,
`test`, `build`, `ci`, `chore`.

## Setting Up Branch Protection

To protect the `release` branch on GitHub:

1. Go to **Settings → Branches → Add branch protection rule**
2. Branch name pattern: `release`
3. Enable:
   - ✅ *Require a pull request before merging* (prevents direct pushes by humans)
   - ✅ *Allow force pushes* → select **"Specify who can force push"** → add
     `github-actions[bot]` (so the workflow can update the branch)
   - ✅ *Restrict who can push to matching branches* → add `github-actions[bot]`
4. Save changes

This ensures only the automated release workflow modifies the `release` branch.

## Testing the Build Locally

Before pushing changes or cutting a release, you can run the full pipeline
locally to catch problems early.

### Prerequisites

| Tool | Required for | Install |
|------|-------------|---------|
| Python 3.11+ | Everything | https://python.org |
| pip | Everything | Comes with Python |
| flake8 | Lint stage | `pip install flake8` (auto-installed by script) |
| PyInstaller | Build stage | `pip install -r requirements.txt` |
| Inno Setup 6 | Installer stage | https://jrsoftware.org/isdl.php |

### Windows (PowerShell)

```powershell
# Run the full pipeline: lint → test → build → installer
.\scripts\local_build.ps1

# Run only tests
.\scripts\local_build.ps1 -Stage test

# Run only lint
.\scripts\local_build.ps1 -Stage lint

# Build the app but skip the Inno Setup installer
.\scripts\local_build.ps1 -SkipInstaller

# Build with a specific version number
.\scripts\local_build.ps1 -Version 1.2.0

# Build the installer only (assumes app is already built)
.\scripts\local_build.ps1 -Stage installer
```

### Linux / macOS / Git Bash

```bash
# Run tests + lint (build is Windows-only)
./scripts/local_build.sh

# Just tests
./scripts/local_build.sh test

# Just lint
./scripts/local_build.sh lint
```

### What the script checks

The local build script mirrors the GitHub Actions pipeline step-by-step:

1. **Prerequisites** — checks that Python, pip, and optional tools are available
2. **Lint** — runs `flake8` (syntax errors block, style warnings are informational)
3. **Tests** — runs `test_data_repository` and `test_onboarding` via `unittest`
4. **Version bump** — stamps the version into `VERSION` and `installer/SheepCat.iss`
5. **PyInstaller build** — produces `dist\SheepCat\SheepCat.exe`
6. **Inno Setup** — produces `installer\Output\SheepCatSetup_X.Y.Z.exe`

If any stage fails, the script stops immediately with a clear error message.

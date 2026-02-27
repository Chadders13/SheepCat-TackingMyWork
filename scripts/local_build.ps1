<#
.SYNOPSIS
    Local build and test script for SheepCat -- mirrors the GitHub Actions pipeline.

.DESCRIPTION
    Runs the same steps as the CI and Release workflows so you can verify
    everything works before pushing.  Supports running individual stages or
    the full pipeline.

.PARAMETER Stage
    Which stage(s) to run.  Default is "all".
    Valid values: test, lint, build, installer, all

.PARAMETER Version
    Version to stamp into the build (e.g. "1.2.0").
    Defaults to whatever is in the VERSION file.

.PARAMETER SkipInstaller
    Skip the Inno Setup installer step (useful if you don't have iscc installed).

.EXAMPLE
    # Run everything
    .\scripts\local_build.ps1

    # Just run tests
    .\scripts\local_build.ps1 -Stage test

    # Full build with a specific version
    .\scripts\local_build.ps1 -Version 1.2.0

    # Build the app but skip the Inno Setup installer
    .\scripts\local_build.ps1 -SkipInstaller
#>

[CmdletBinding()]
param(
    [ValidateSet("test", "lint", "build", "installer", "all")]
    [string]$Stage = "all",

    [string]$Version = "",

    [switch]$SkipInstaller
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---- Helpers ----------------------------------------------------------------
function Write-StepHeader([string]$text) {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host ""
}

function Write-OK([string]$text) {
    Write-Host "  [OK] $text" -ForegroundColor Green
}

function Write-Err([string]$text) {
    Write-Host "  [FAIL] $text" -ForegroundColor Red
}

function Assert-Command([string]$cmd, [string]$installHint) {
    if (!(Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Err "$cmd is not installed or not on PATH."
        Write-Host "    -> $installHint" -ForegroundColor Yellow
        exit 1
    }
    Write-OK "$cmd found: $((Get-Command $cmd).Source)"
}

# ---- Resolve repo root (script lives in scripts/) --------------------------
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
Push-Location $RepoRoot

try {
    # ---- Read version -------------------------------------------------------
    if (-not $Version) {
        $Version = (Get-Content "VERSION" -Raw).Trim()
    }
    Write-Host "SheepCat local build -- version $Version" -ForegroundColor White
    Write-Host "Repo root: $RepoRoot"

    $runTest      = $Stage -in @("test", "all")
    $runLint      = $Stage -in @("lint", "all")
    $runBuild     = $Stage -in @("build", "installer", "all")
    $runInstaller = ($Stage -in @("installer", "all")) -and (-not $SkipInstaller)

    # =========================================================================
    #  PREREQUISITES CHECK
    # =========================================================================
    Write-StepHeader "Checking prerequisites"

    Assert-Command "python"   "Install Python 3.11+ from https://python.org"
    Assert-Command "pip"      "pip should come with Python -- reinstall Python if missing"

    if ($runLint) {
        # Install flake8 if not present
        if (!(Get-Command "flake8" -ErrorAction SilentlyContinue)) {
            Write-Host "  Installing flake8..." -ForegroundColor Yellow
            pip install flake8 --quiet
        }
        Assert-Command "flake8" "pip install flake8"
    }

    if ($runBuild) {
        Assert-Command "pyinstaller" "pip install pyinstaller  (or: pip install -r requirements.txt)"
    }

    if ($runInstaller) {
        # Look for iscc in common locations
        $isccPaths = @(
            "iscc",
            "${env:ProgramFiles(x86)}\Inno Setup 6\iscc.exe",
            "$env:ProgramFiles\Inno Setup 6\iscc.exe"
        )
        $isccFound = $false
        foreach ($p in $isccPaths) {
            if (Get-Command $p -ErrorAction SilentlyContinue) {
                $script:isccCmd = $p
                $isccFound = $true
                break
            }
            if (Test-Path $p) {
                $script:isccCmd = $p
                $isccFound = $true
                break
            }
        }
        if (-not $isccFound) {
            Write-Err "Inno Setup (iscc) not found."
            Write-Host "    -> Download from https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
            Write-Host "    -> Or use -SkipInstaller to skip this step" -ForegroundColor Yellow
            exit 1
        }
        Write-OK "iscc found: $($script:isccCmd)"
    }

    Write-Host ""
    Write-Host "  Installing Python dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt --quiet
    Write-OK "Dependencies installed"

    # =========================================================================
    #  STAGE: LINT
    # =========================================================================
    if ($runLint) {
        Write-StepHeader "Linting (flake8)"

        Write-Host "  Checking for syntax errors and undefined names..."
        flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
        if ($LASTEXITCODE -ne 0) {
            Write-Err "Lint failed -- syntax errors or undefined names found."
            exit 1
        }
        Write-OK "No syntax errors or undefined names"

        Write-Host ""
        Write-Host "  Style warnings (informational):"
        flake8 src/ --count --exit-zero --max-complexity=10 --max-line-length=120 --statistics
        Write-OK "Lint complete"
    }

    # =========================================================================
    #  STAGE: TEST
    # =========================================================================
    if ($runTest) {
        Write-StepHeader "Running unit tests"

        Write-Host "  test_data_repository..."
        python -m unittest test_data_repository -v
        if ($LASTEXITCODE -ne 0) {
            Write-Err "test_data_repository FAILED"
            exit 1
        }

        Write-Host ""
        Write-Host "  test_onboarding..."
        python -m unittest test_onboarding -v
        if ($LASTEXITCODE -ne 0) {
            Write-Err "test_onboarding FAILED"
            exit 1
        }

        Write-OK "All tests passed"
    }

    # =========================================================================
    #  STAGE: VERSION BUMP
    # =========================================================================
    if ($runBuild) {
        Write-StepHeader "Bumping version to $Version"
        python scripts/bump_version.py $Version
        if ($LASTEXITCODE -ne 0) {
            Write-Err "Version bump failed"
            exit 1
        }
    }

    # =========================================================================
    #  STAGE: BUILD (PyInstaller)
    # =========================================================================
    if ($runBuild) {
        Write-StepHeader "Building with PyInstaller"

        # Clean previous build
        if (Test-Path "dist\SheepCat") {
            Remove-Item "dist\SheepCat" -Recurse -Force
            Write-Host "  Cleaned previous dist\SheepCat"
        }

        pyinstaller SheepCat.spec
        if ($LASTEXITCODE -ne 0) {
            Write-Err "PyInstaller build failed"
            exit 1
        }

        if (!(Test-Path "dist\SheepCat\SheepCat.exe")) {
            Write-Err "Build output not found: dist\SheepCat\SheepCat.exe"
            exit 1
        }

        $exeSize = [math]::Round((Get-Item "dist\SheepCat\SheepCat.exe").Length / 1MB, 1)
        Write-OK "Build successful: dist\SheepCat\SheepCat.exe ($exeSize MB)"
    }

    # =========================================================================
    #  STAGE: INSTALLER (Inno Setup)
    # =========================================================================
    if ($runInstaller) {
        Write-StepHeader "Building installer with Inno Setup"

        $outputDir = "installer\Output"
        if (Test-Path $outputDir) {
            Remove-Item "$outputDir\*" -Force -ErrorAction SilentlyContinue
        }

        & $script:isccCmd "installer\SheepCat.iss" /O"$outputDir"
        if ($LASTEXITCODE -ne 0) {
            Write-Err "Inno Setup build failed"
            exit 1
        }

        $installerName = "SheepCatSetup_$Version.exe"
        $installerPath = Join-Path $outputDir $installerName

        if (!(Test-Path $installerPath)) {
            Write-Err "Installer not found: $installerPath"
            exit 1
        }

        $installerSize = [math]::Round((Get-Item $installerPath).Length / 1MB, 1)
        Write-OK "Installer built: $installerPath ($installerSize MB)"
    }

    # =========================================================================
    #  DONE
    # =========================================================================
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Green
    Write-Host "  All stages completed successfully!" -ForegroundColor Green
    Write-Host ("=" * 70) -ForegroundColor Green
    Write-Host ""

    if ($runBuild) {
        Write-Host "  App:       dist\SheepCat\SheepCat.exe"
    }
    if ($runInstaller) {
        Write-Host "  Installer: installer\Output\SheepCatSetup_$Version.exe"
    }
    Write-Host ""

} finally {
    Pop-Location
}

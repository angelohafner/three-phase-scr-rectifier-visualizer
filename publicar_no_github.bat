@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "REPO=angelohafner/three-phase-scr-rectifier-visualizer"

REM Ensure the required tools are available.
where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: Git is not installed or not in PATH.
    echo Install it with: winget install --id Git.Git -e
    exit /b 1
)
where gh >nul 2>nul
if errorlevel 1 (
    echo ERROR: GitHub CLI is not installed or not in PATH.
    echo Install it with: winget install --id GitHub.cli -e
    exit /b 1
)

REM Authenticate using the account that owns the target repository.
gh auth status >nul 2>nul
if errorlevel 1 (
    echo GitHub authentication required. Follow the browser login prompts.
    gh auth login --hostname github.com --web
    if errorlevel 1 exit /b 1
)
set "CURRENT_LOGIN="
for /f "delims=" %%L in ('gh api user --jq .login') do set "CURRENT_LOGIN=%%L"
if /i not "%CURRENT_LOGIN%"=="angelohafner" (
    echo ERROR: Authenticated GitHub login is "%CURRENT_LOGIN%", not "angelohafner".
    echo Switch accounts using gh auth switch and run this script again.
    exit /b 1
)

REM Do not publish into an unexpectedly existing repository.
gh repo view "%REPO%" >nul 2>nul
if not errorlevel 1 (
    echo ERROR: The destination repository already exists.
    echo For safety, review the existing repository before pushing new files.
    exit /b 1
)

REM Initialize the local repository and commit all deliverables.
if not exist ".git" (
    git init -b main
    if errorlevel 1 exit /b 1
)
git add .
if errorlevel 1 exit /b 1
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Initial release: twelve-state SCR rectifier visualization"
    if errorlevel 1 (
        echo ERROR: Git commit failed. Verify your git user.name and user.email.
        exit /b 1
    )
)

REM Create a private repository and publish the initial commit.
gh repo create "%REPO%" --private --source=. --remote=origin --push --description "Parameterized six-pulse SCR rectifier SVG diagrams with 12 conduction and commutation-overlap states"
if errorlevel 1 (
    echo ERROR: Repository creation or push failed.
    exit /b 1
)
echo.
echo SUCCESS: https://github.com/%REPO%
endlocal

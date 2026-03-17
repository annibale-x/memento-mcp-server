@echo off
REM Build script for MCP Memento package (Windows batch version)
REM
REM Usage:
REM   build.bat [command]
REM
REM Commands:
REM   clean     - Clean build artifacts
REM   build     - Build package (sdist + wheel)
REM   test      - Run tests
REM   check     - Check package with twine
REM   all       - Run clean, build, test, check
REM   install   - Install package locally
REM   version   - Show current version
REM   help      - Show this help

setlocal enabledelayedexpansion

REM Project directories
set "PROJECT_ROOT=%~dp0.."
set "DIST_DIR=%PROJECT_ROOT%\dist"
set "BUILD_DIR=%PROJECT_ROOT%\build"
set "EGG_INFO_DIR=%PROJECT_ROOT%\src\mcp_memento.egg-info"

REM Colors for output
if "%CI%" == "" (
    set "GREEN="
    set "RED="
    set "YELLOW="
    set "BLUE="
    set "RESET="
) else (
    set "GREEN=[32m"
    set "RED=[31m"
    set "YELLOW=[33m"
    set "BLUE=[34m"
    set "RESET=[0m"
)

REM Function to print colored output
:print_color
    echo %~1
    exit /b 0

REM Function to run command and check error
:run_command
    echo 🚀 Running: %~1
    %~1
    if errorlevel 1 (
        echo ❌ Command failed: %~1
        exit /b 1
    )
    exit /b 0

REM Clean build artifacts
:clean
    echo 🧹 Cleaning build artifacts...

    REM Remove distribution directories
    if exist "%DIST_DIR%" (
        echo   Removing %DIST_DIR%
        rmdir /s /q "%DIST_DIR%"
    )

    if exist "%BUILD_DIR%" (
        echo   Removing %BUILD_DIR%
        rmdir /s /q "%BUILD_DIR%"
    )

    REM Remove egg-info directory
    if exist "%EGG_INFO_DIR%" (
        echo   Removing %EGG_INFO_DIR%
        rmdir /s /q "%EGG_INFO_DIR%"
    )

    REM Remove Python cache files
    echo   Removing Python cache files...
    python -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]"
    python -c "import pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]"

    REM Remove coverage files
    for %%f in (.coverage .coverage.*) do (
        if exist "%%f" (
            echo   Removing %%f
            del "%%f"
        )
    )

    echo ✅ Clean completed
    exit /b 0

REM Build the package
:build
    echo 🔨 Building package...

    REM Ensure dist directory exists
    if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"

    REM Build package
    call :run_command "python -m build"

    REM List generated files
    echo 📦 Generated distribution files:
    for %%f in ("%DIST_DIR%\*") do (
        for %%i in ("%%f") do (
            set "size=%%~zi"
            set /a "size_kb=!size! / 1024"
            echo   - %%~nxf (!size_kb! KB)
        )
    )

    echo ✅ Build completed
    exit /b 0

REM Run tests
:test
    echo 🧪 Running tests...
    call :run_command "python -m pytest tests/ -v --tb=short"
    echo ✅ Tests completed
    exit /b 0

REM Check package with twine
:check
    echo 🔍 Checking package with twine...

    REM Check if distribution files exist
    set "has_files=0"
    for %%f in ("%DIST_DIR%\*") do set "has_files=1"

    if "!has_files!"=="0" (
        echo ❌ No distribution files found. Run 'build' first.
        exit /b 1
    )

    call :run_command "twine check %DIST_DIR%\*"
    echo ✅ Package check completed
    exit /b 0

REM Install package locally
:install
    echo 📦 Installing package locally...

    REM Find the latest wheel
    set "latest_wheel="
    set "latest_time=0"

    for %%f in ("%DIST_DIR%\*.whl") do (
        for %%i in ("%%f") do (
            set "file_time=%%~ti"
            set "file_time=!file_time:~0,19!"

            REM Convert to sortable format (YYYYMMDDHHMMSS)
            set "sortable_time=!file_time:~6,4!!file_time:~3,2!!file_time:~0,2!!file_time:~11,2!!file_time:~14,2!!file_time:~17,2!"

            if !sortable_time! gtr !latest_time! (
                set "latest_time=!sortable_time!"
                set "latest_wheel=%%f"
            )
        )
    )

    if "!latest_wheel!"=="" (
        echo ❌ No wheel files found. Run 'build' first.
        exit /b 1
    )

    echo   Installing: %latest_wheel%
    call :run_command "pip install --force-reinstall "%latest_wheel%""

    REM Verify installation
    for /f "delims=" %%v in ('memento --version 2^>nul') do set "version_output=%%v"
    echo   Installed version: !version_output!

    echo ✅ Installation completed
    exit /b 0

REM Show current version
:version
    echo 📋 MCP Memento version information:

    REM Try to read from pyproject.toml
    if exist "%PROJECT_ROOT%\pyproject.toml" (
        for /f "tokens=2 delims==" %%v in ('findstr /i "version" "%PROJECT_ROOT%\pyproject.toml"') do (
            set "version=%%v"
            set "version=!version:"=!"
            set "version=!version: =!"
            echo   From pyproject.toml: !version!
        )
    )

    REM Try to read from __init__.py
    if exist "%PROJECT_ROOT%\src\memento\__init__.py" (
        for /f "tokens=2 delims==" %%v in ('findstr "__version__" "%PROJECT_ROOT%\src\memento\__init__.py"') do (
            set "init_version=%%v"
            set "init_version=!init_version:"=!"
            set "init_version=!init_version: =!"
            echo   From __init__.py: !init_version!
        )
    )

    exit /b 0

REM Run all tasks
:all
    call :clean
    call :build
    call :test
    call :check
    echo 🎉 All tasks completed successfully!
    exit /b 0

REM Show help
:help
    echo MCP Memento Build Script (Windows Batch)
    echo.
    echo Usage:
    echo   build.bat [command]
    echo.
    echo Commands:
    echo   clean     - Clean build artifacts
    echo   build     - Build package ^(sdist + wheel^)
    echo   test      - Run tests
    echo   check     - Check package with twine
    echo   all       - Run clean, build, test, check
    echo   install   - Install package locally
    echo   version   - Show current version
    echo   help      - Show this help
    echo.
    echo Examples:
    echo   build.bat all
    echo   build.bat build ^&^& build.bat install
    exit /b 0

REM Main execution
if "%1"=="" (
    call :help
    exit /b 0
)

REM Execute the requested command
if "%1"=="clean" call :clean
if "%1"=="build" call :build
if "%1"=="test" call :test
if "%1"=="check" call :check
if "%1"=="all" call :all
if "%1"=="install" call :install
if "%1"=="version" call :version
if "%1"=="help" call :help

REM If command not recognized
if not "%1"=="clean" if not "%1"=="build" if not "%1"=="test" if not "%1"=="check" if not "%1"=="all" if not "%1"=="install" if not "%1"=="version" if not "%1"=="help" (
    echo ❌ Unknown command: %1
    echo.
    call :help
    exit /b 1
)

endlocal

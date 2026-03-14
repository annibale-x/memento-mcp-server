@echo off
REM Test runner batch script for mcp-context-keeper project
REM Usage: run_tests.bat [options]

setlocal enabledelayedexpansion

REM Set colors for output
if "%CI%" == "" (
    for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do (
        set "DEL=%%a"
    )
    echo.
    call :colorEcho 0A "============================================================"
    echo.
) else (
    echo ============================================================
)

echo Starting test suite for mcp-context-keeper
if "%CI%" == "" (
    call :colorEcho 0A "============================================================"
    echo.
) else (
    echo ============================================================
)
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    if "%CI%" == "" (
        call :colorEcho 0C "ERROR: Python is not installed or not in PATH"
    ) else (
        echo ERROR: Python is not installed or not in PATH
    )
    exit /b 1
)

REM Parse command line arguments
set VERBOSE=
set OUTPUT=
set LIST=

:parse_args
if "%1"=="" goto :run_tests
if "%1"=="-v" set VERBOSE=-v
if "%1"=="--verbose" set VERBOSE=-v
if "%1"=="-o" (
    set OUTPUT=-o "%2"
    shift
)
if "%1"=="--output" (
    set OUTPUT=-o "%2"
    shift
)
if "%1"=="--list" set LIST=--list
shift
goto :parse_args

:run_tests
REM Change to script directory
cd /d "%~dp0"

REM Run the test runner
if not "%LIST%"=="" (
    echo Listing available test files...
    echo.
    python run_tests.py --list
    goto :end
)

if "%VERBOSE%"=="" (
    echo Running tests... (use -v for verbose output)
    echo.
) else (
    echo Running tests with verbose output...
    echo.
)

python run_tests.py %VERBOSE% %OUTPUT%
set TEST_RESULT=%errorlevel%

echo.
if "%CI%" == "" (
    call :colorEcho 0A "============================================================"
    echo.
) else (
    echo ============================================================
)

if %TEST_RESULT% equ 0 (
    if "%CI%" == "" (
        call :colorEcho 0A "[PASS] All tests passed successfully!"
    ) else (
        echo [PASS] All tests passed successfully!
    )
) else (
    if "%CI%" == "" (
        call :colorEcho 0C "[FAIL] Some tests failed. Exit code: %TEST_RESULT%"
    ) else (
        echo [FAIL] Some tests failed. Exit code: %TEST_RESULT%
    )
)
echo.
if "%CI%" == "" (
    call :colorEcho 0A "============================================================"
) else (
    echo ============================================================
)
endlocal
exit /b %TEST_RESULT%

:colorEcho
REM Function to print colored text
<nul set /p ".=%DEL%" > "%~2"
findstr /v /a:%1 /R "^$" "%~2" nul
del "%~2" > nul 2>&1
goto :eof

:end
endlocal

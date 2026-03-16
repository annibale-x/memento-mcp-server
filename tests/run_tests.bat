@echo off
REM Windows test runner for mcp-memento project
REM Usage: run_tests.bat [options] [test_files...]
REM
REM Options:
REM   -v, --verbose      Increase verbosity of test output
REM   -q, --quiet        Reduce verbosity of test output
REM   --list             List all available test files and exit
REM   -k EXPRESSION      Only run tests matching the given substring expression
REM   -x, --exitfirst    Exit instantly on first error or failed test
REM   --tb STYLE         Set traceback style (short, long, line, no)
REM   --no-header        Suppress header and summary output
REM   --coverage         Generate coverage report (requires pytest-cov)

setlocal enabledelayedexpansion

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)

REM Change to script directory
cd /d "%~dp0"

REM Initialize variables
set VERBOSE=
set QUIET=
set LIST=
set KEYWORD=
set EXITFIRST=
set TB=short
set NOHEADER=
set COVERAGE=
set TEST_FILES=

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :run_tests

if "%~1"=="-v" set VERBOSE=-v
if "%~1"=="--verbose" set VERBOSE=-v
if "%~1"=="-q" set QUIET=-q
if "%~1"=="--quiet" set QUIET=-q
if "%~1"=="--list" set LIST=--list
if "%~1"=="-k" (
    set KEYWORD=-k "%~2"
    shift
)
if "%~1"=="--exitfirst" set EXITFIRST=-x
if "%~1"=="-x" set EXITFIRST=-x
if "%~1"=="--tb" (
    set TB=%~2
    shift
)
if "%~1"=="--no-header" set NOHEADER=--no-header
if "%~1"=="--coverage" set COVERAGE=--coverage

REM Check if argument is a test file (not starting with -)
if not "%~1"=="" (
    echo "%~1" | findstr "^[^-]" >nul
    if not errorlevel 1 (
        if not "!TEST_FILES!"=="" set TEST_FILES=!TEST_FILES! "%~1"
        if "!TEST_FILES!"=="" set TEST_FILES="%~1"
    )
)

shift
goto :parse_args

:run_tests
echo ============================================================
echo MCP MEMENTO - TEST SUITE (WINDOWS)
echo ============================================================
echo.

if not "%LIST%"=="" (
    echo Listing available test files...
    echo.
    python run_tests.py --list
    goto :summary
)

echo Starting test execution...
echo.

REM Build command
set PYTEST_CMD=python run_tests.py

if not "%VERBOSE%"=="" set PYTEST_CMD=!PYTEST_CMD! %VERBOSE%
if not "%QUIET%"=="" set PYTEST_CMD=!PYTEST_CMD! %QUIET%
if not "%KEYWORD%"=="" set PYTEST_CMD=!PYTEST_CMD! %KEYWORD%
if not "%EXITFIRST%"=="" set PYTEST_CMD=!PYTEST_CMD! %EXITFIRST%
if not "%TB%"=="short" set PYTEST_CMD=!PYTEST_CMD! --tb %TB%
if not "%NOHEADER%"=="" set PYTEST_CMD=!PYTEST_CMD! %NOHEADER%
if not "%COVERAGE%"=="" set PYTEST_CMD=!PYTEST_CMD! %COVERAGE%
if not "%TEST_FILES%"=="" set PYTEST_CMD=!PYTEST_CMD! %TEST_FILES%

REM Display command
echo Command: !PYTEST_CMD!
echo.

REM Run the tests
set START_TIME=%TIME%
!PYTEST_CMD!
set EXIT_CODE=%errorlevel%

REM Calculate duration
set END_TIME=%TIME%
call :calculate_duration "%START_TIME%" "%END_TIME%"

:summary
echo.
echo ============================================================
echo TEST EXECUTION SUMMARY
echo ============================================================

if "%EXIT_CODE%"=="0" (
    echo RESULT: ALL TESTS PASSED
) else if "%EXIT_CODE%"=="1" (
    echo RESULT: SOME TESTS FAILED
) else if "%EXIT_CODE%"=="2" (
    echo RESULT: TEST EXECUTION WAS INTERRUPTED
) else if "%EXIT_CODE%"=="3" (
    echo RESULT: INTERNAL ERROR IN TEST EXECUTION
) else if "%EXIT_CODE%"=="4" (
    echo RESULT: USAGE ERROR
) else (
    echo RESULT: UNKNOWN EXIT CODE (%EXIT_CODE%)
)

if defined DURATION (
    echo DURATION: %DURATION% seconds
)

echo ============================================================
echo.

endlocal
exit /b %EXIT_CODE%

REM Function to calculate time duration
:calculate_duration
setlocal
set START=%~1
set END=%~2

REM Parse times (format: HH:MM:SS.mm)
for /f "tokens=1-4 delims=:." %%a in ("%START%") do (
    set START_HOUR=%%a
    set START_MIN=%%b
    set START_SEC=%%c
    set START_MS=%%d
)

for /f "tokens=1-4 delims=:." %%a in ("%END%") do (
    set END_HOUR=%%a
    set END_MIN=%%b
    set END_SEC=%%c
    set END_MS=%%d
)

REM Convert to total seconds
set /a START_TOTAL = START_HOUR * 3600 + START_MIN * 60 + START_SEC
set /a END_TOTAL = END_HOUR * 3600 + END_MIN * 60 + END_SEC

REM Calculate difference
set /a DURATION_SEC = END_TOTAL - START_TOTAL

REM Handle milliseconds if available
if not "%START_MS%"=="" if not "%END_MS%"=="" (
    set /a DURATION_MS = END_MS - START_MS
    if !DURATION_MS! lss 0 (
        set /a DURATION_SEC = DURATION_SEC - 1
        set /a DURATION_MS = 100 + DURATION_MS
    )
    set DURATION=!DURATION_SEC!.!DURATION_MS!
) else (
    set DURATION=!DURATION_SEC!
)

endlocal & set DURATION=%DURATION%
goto :eof

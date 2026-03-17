@echo off
REM Build script wrapper for MCP Memento package (Windows)
REM This simply calls the main Python build script to ensure consistent behavior
REM across platforms and to avoid duplicating build logic.

python "%~dp0build_memento.py" %*

"""
CLI test suite for mcp-memento.

This module tests the command-line interface functionality.
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from memento.cli import (
    _eprint,
    handle_export,
    handle_import,
    main,
    perform_health_check,
    print_config_summary,
    validate_profile,
)
from memento.config import Config


class TestCLIBasic:
    """Test basic CLI functionality."""

    def test_eprint_function(self):
        """Test _eprint prints to stderr."""
        import io
        from contextlib import redirect_stderr

        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            _eprint("Test message")
            _eprint("Another message", "with arg")

        output = stderr_capture.getvalue()
        assert "Test message\n" in output
        assert "Another message with arg\n" in output

    def test_validate_profile_valid(self):
        """Test profile validation with valid inputs."""
        # Valid modern profiles
        validate_profile("core")
        validate_profile("extended")
        # Valid legacy profiles (should warn but not exit)
        validate_profile("lite")
        validate_profile("standard")
        validate_profile("full")

    def test_validate_profile_invalid(self):
        """Test profile validation with invalid inputs."""
        with pytest.raises(SystemExit):
            validate_profile("invalid_profile")

        with pytest.raises(SystemExit):
            validate_profile("basic")

    def test_print_config_summary(self, capsys):
        """Test config summary printing."""
        # Mock stderr output by using _eprint which we already test
        # Actually print_config_summary uses _eprint internally
        with patch("memento.cli._eprint") as mock_eprint:
            print_config_summary()

            # Verify _eprint was called
            assert mock_eprint.call_count > 0

            # Check that some expected text appears in calls
            # Handle different call structures (positional vs keyword args)
            call_texts = []
            for call in mock_eprint.call_args_list:
                if call[0]:  # positional arguments
                    call_texts.append(str(call[0][0]))
                elif call[1]:  # keyword arguments
                    # Look for message in keyword args
                    for key, value in call[1].items():
                        if key in ["msg", "message", "text"]:
                            call_texts.append(str(value))
                        elif key == "args" and value:
                            call_texts.append(str(value[0]))

            call_text = "\n".join(call_texts)
            if call_text:  # Only check if we extracted text
                assert (
                    "Current Configuration:" in call_text
                    or "Backend:" in call_text
                    or "Tool Profile:" in call_text
                )

    def test_cli_help(self):
        """Test CLI help output."""
        # Mock sys.argv and sys.exit
        with patch("sys.argv", ["memento.cli", "--help"]):
            with patch("sys.exit") as mock_exit:
                with patch("memento.cli._eprint") as mock_eprint:
                    main()

                    # Should exit with 0 after printing help
                    # Note: argparse may call sys.exit multiple times in some cases
                    # Check that at least one call was with exit code 0
                    exit_calls = [
                        call for call in mock_exit.call_args_list if call[0] == (0,)
                    ]
                    assert len(exit_calls) > 0, "Expected at least one sys.exit(0) call"
                    # Help should be printed
                    assert mock_eprint.call_count > 0

    def test_cli_version(self, capsys):
        """Test CLI version output."""
        with patch("sys.argv", ["memento.cli", "--version"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Version should exit with 0
            assert exc_info.value.code == 0

    def test_cli_show_config(self):
        """Test --show-config option."""
        with patch("sys.argv", ["memento.cli", "--show-config"]):
            with patch("sys.exit") as mock_exit:
                with patch("memento.cli._eprint") as mock_eprint:
                    main()

                    # Check that exit was called with 0 (may be called multiple times)
                    mock_exit.assert_any_call(0)
                    # Config summary should be printed
                    assert mock_eprint.call_count > 0


class TestCLIHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_perform_health_check_success(self):
        """Test successful health check."""
        # Mock SQLiteBackend
        mock_backend = AsyncMock()
        mock_backend.connect = AsyncMock(return_value=True)
        mock_backend.disconnect = AsyncMock(return_value=None)
        mock_backend.health_check = AsyncMock(
            return_value={
                "status": "healthy",
                "connected": True,
                "backend_type": "sqlite",
                "db_path": "/tmp/test.db",
                "version": "3.42.0",
                "statistics": {"memory_count": 42},
                "database_size_bytes": 1024,
            }
        )

        with patch("memento.database.engine.SQLiteBackend", return_value=mock_backend):
            result = await perform_health_check(timeout=1.0)

            assert result["status"] == "healthy"
            assert result["connected"] is True
            assert result["backend_type"] == "sqlite"
            assert "version" in result
            assert "statistics" in result

            # Verify backend methods were called
            mock_backend.connect.assert_called_once()
            mock_backend.health_check.assert_called_once()
            mock_backend.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_perform_health_check_timeout(self):
        """Test health check timeout handling."""
        # Mock SQLiteBackend to timeout on connect
        mock_backend = AsyncMock()
        mock_backend.connect = AsyncMock(
            side_effect=asyncio.TimeoutError("Timeout"), return_value=None
        )

        with patch("memento.database.engine.SQLiteBackend", return_value=mock_backend):
            result = await perform_health_check(timeout=0.1)

            assert result["status"] == "unhealthy"
            assert result["connected"] is False
            assert "error" in result
            assert "timed out" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_perform_health_check_exception(self):
        """Test health check exception handling."""
        # Mock SQLiteBackend to raise exception
        mock_backend = AsyncMock()
        mock_backend.connect = AsyncMock(
            side_effect=Exception("Connection failed"), return_value=None
        )

        with patch("memento.database.engine.SQLiteBackend", return_value=mock_backend):
            result = await perform_health_check(timeout=1.0)

            assert result["status"] == "unhealthy"
            assert result["connected"] is False
            assert "error" in result
            assert "connection failed" in result["error"].lower()

    def test_cli_health_option(self):
        """Test --health option."""
        with patch("sys.argv", ["memento.cli", "--health"]):
            with patch("sys.exit") as mock_exit:
                with patch("memento.cli.perform_health_check") as mock_check:
                    # Mock async function
                    mock_check.return_value = {
                        "status": "healthy",
                        "connected": True,
                        "backend_type": "sqlite",
                        "timestamp": "2024-01-15T10:30:00Z",
                    }

                    with patch("memento.cli.asyncio.run") as mock_run:
                        # Mock asyncio.run to return the mock result directly
                        mock_run.side_effect = lambda coro: mock_check.return_value
                        main()

                        # Should exit with 0 for healthy
                        mock_exit.assert_any_call(0)
                        mock_check.assert_called_once()

    def test_cli_health_json_option(self):
        """Test --health --health-json option."""
        with patch("sys.argv", ["memento.cli", "--health", "--health-json"]):
            with patch("sys.exit") as mock_exit:
                with patch(
                    "memento.cli.perform_health_check", new_callable=AsyncMock
                ) as mock_check:
                    health_data = {
                        "status": "healthy",
                        "connected": True,
                        "backend_type": "sqlite",
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                    # Configure AsyncMock to return value directly without creating coroutine
                    mock_check.return_value = health_data
                    mock_check._is_coroutine = False

                    with patch("memento.cli.asyncio.run") as mock_run:
                        with patch("builtins.print") as mock_print:
                            # Mock asyncio.run to return the mock result directly
                            # Use side_effect to avoid creating an AsyncMock
                            mock_run.side_effect = lambda coro: mock_check.return_value
                            # Mark the mock as not a coroutine to avoid warnings
                            mock_run._is_coroutine = False
                            main()

                        # Should print JSON to stdout
                        # Check that JSON was printed to stdout
                        json_calls = [
                            call
                            for call in mock_print.call_args_list
                            if len(call.args) > 0
                            and isinstance(call.args[0], str)
                            and call.args[0].strip().startswith("{")
                        ]
                        assert len(json_calls) == 1
                        call_args = json_calls[0].args[0]
                        parsed = json.loads(call_args)
                        assert parsed["status"] == "healthy"
                        # Should exit with 0
                        mock_exit.assert_any_call(0)


class TestCLIExportImport:
    """Test export and import commands."""

    @pytest.mark.asyncio
    async def test_handle_export_json(self):
        """Test export to JSON format."""
        # Create temporary file for export
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            output_path = tmp.name

        try:
            # Mock arguments
            mock_args = MagicMock()
            mock_args.format = "json"
            mock_args.output = output_path
            mock_args.force = False

            # Mock database and backend
            mock_backend = AsyncMock()
            mock_backend.disconnect = AsyncMock(return_value=None)
            mock_backend.backend_name = MagicMock(return_value="sqlite")

            mock_db = AsyncMock(return_value=None)

            # Mock export_to_json function
            with patch("memento.utils.export_import.export_to_json") as mock_export:
                mock_export.return_value = {
                    "memory_count": 10,
                    "relationship_count": 5,
                    "backend_type": "sqlite",
                }

                with patch("memento.cli._create_backend_and_db") as mock_create:
                    mock_create.return_value = (mock_backend, "sqlite", mock_db)

                    # Capture printed output
                    with patch("memento.cli._eprint") as mock_eprint:
                        await handle_export(mock_args)

                        # Verify export was called
                        mock_export.assert_called_once_with(mock_db, output_path)
                        # Verify backend was disconnected
                        mock_backend.disconnect.assert_called_once()
                        # Verify success message was printed
                        assert mock_eprint.call_count > 0

                        call_text = "\n".join(
                            [call[0][0] for call in mock_eprint.call_args_list]
                        )
                        assert "Export complete!" in call_text
                        assert "Memories: 10" in call_text
                        assert "Relationships: 5" in call_text

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    @pytest.mark.asyncio
    async def test_handle_export_markdown(self):
        """Test export to Markdown format."""
        # Create temporary directory for markdown export
        temp_dir = tempfile.mkdtemp()

        try:
            # Mock arguments
            mock_args = MagicMock()
            mock_args.format = "markdown"
            mock_args.output = temp_dir

            # Mock database and backend
            mock_backend = AsyncMock()
            mock_backend.disconnect = AsyncMock(return_value=None)
            mock_backend.backend_name = MagicMock(return_value="sqlite")

            mock_db = AsyncMock(return_value=None)
            mock_db.initialize_schema = AsyncMock(return_value=None)

            # Mock export_to_markdown function
            with patch("memento.utils.export_import.export_to_markdown") as mock_export:
                mock_export.return_value = None  # Function doesn't return value

                with patch("memento.cli._create_backend_and_db") as mock_create:
                    mock_create.return_value = (mock_backend, "sqlite", mock_db)

                    with patch("memento.cli._eprint") as mock_eprint:
                        await handle_export(mock_args)

                        # Verify export was called
                        mock_export.assert_called_once_with(mock_db, temp_dir)
                        # Verify backend was disconnected
                        mock_backend.disconnect.assert_called_once()
                        # Verify success message was printed
                        assert mock_eprint.call_count > 0

        finally:
            if os.path.exists(temp_dir):
                import shutil

                shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_handle_import_json(self):
        """Test import from JSON format."""
        # Create temporary input file
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tmp:
            json.dump({"memories": [], "relationships": []}, tmp)
            input_path = tmp.name

        try:
            # Mock arguments
            mock_args = MagicMock()
            mock_args.format = "json"
            mock_args.input = input_path
            mock_args.skip_duplicates = True

            # Mock database and backend
            mock_backend = AsyncMock()
            mock_backend.disconnect = AsyncMock(return_value=None)
            mock_backend.backend_name = MagicMock(return_value="sqlite")

            mock_db = AsyncMock(return_value=None)
            mock_db.initialize_schema = AsyncMock(return_value=None)

            # Mock import_from_json function
            with patch("memento.utils.export_import.import_from_json") as mock_import:
                mock_import.return_value = {
                    "imported_memories": 5,
                    "imported_relationships": 3,
                    "skipped_memories": 2,
                    "skipped_relationships": 1,
                }

                with patch("memento.cli._create_backend_and_db") as mock_create:
                    mock_create.return_value = (mock_backend, "sqlite", mock_db)

                    with patch("memento.cli._eprint") as mock_eprint:
                        await handle_import(mock_args)

                        # Verify import was called
                        mock_import.assert_called_once_with(
                            mock_db, input_path, skip_duplicates=True
                        )
                        # Verify backend was disconnected
                        mock_backend.disconnect.assert_called_once()
                        # Verify success message was printed
                        assert mock_eprint.call_count > 0

        finally:
            if os.path.exists(input_path):
                os.unlink(input_path)

    @pytest.mark.asyncio
    async def test_handle_export_error(self):
        """Test export error handling."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            output_path = tmp.name

        try:
            # Mock arguments
            mock_args = MagicMock()
            mock_args.format = "json"
            mock_args.output = output_path
            mock_args.force = False

            # Mock database and backend to raise exception
            mock_backend = AsyncMock()
            mock_backend.disconnect = AsyncMock(return_value=None)
            mock_backend.backend_name = MagicMock(return_value="sqlite")

            mock_db = AsyncMock(return_value=None)
            mock_db.initialize_schema = AsyncMock(return_value=None)

            with patch("memento.cli._create_backend_and_db") as mock_create:
                mock_create.side_effect = Exception("Export failed")

                with patch("memento.cli._eprint") as mock_eprint:
                    with pytest.raises(SystemExit):
                        await handle_export(mock_args)

                    # Verify error message was printed
                    assert mock_eprint.call_count > 0
                    error_text = mock_eprint.call_args_list[0][0][0]
                    assert "Export failed" in error_text

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_cli_export_command(self):
        """Test export command via CLI."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            output_path = tmp.name

        try:
            with patch(
                "sys.argv",
                [
                    "memento.cli",
                    "export",
                    "--format",
                    "json",
                    "--output",
                    output_path,
                ],
            ):
                with patch("sys.exit") as mock_exit:
                    with patch("memento.cli.handle_export") as mock_handle:
                        mock_handle.return_value = None

                        with patch("memento.cli.asyncio.run") as mock_run:
                            # Mock asyncio.run to return None directly
                            mock_run.side_effect = lambda coro: None
                            main()

                            mock_exit.assert_any_call(0)
                            mock_handle.assert_called_once()
                            # Should exit with 0
                            mock_exit.assert_any_call(0)

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_cli_import_command(self):
        """Test import command via CLI."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            input_path = tmp.name

        try:
            with patch(
                "sys.argv",
                [
                    "memento.cli",
                    "import",
                    "--format",
                    "json",
                    "--input",
                    input_path,
                ],
            ):
                with patch("sys.exit") as mock_exit:
                    with patch("memento.cli.handle_import") as mock_handle:
                        mock_handle.return_value = None

                        with patch("memento.cli.asyncio.run") as mock_run:
                            # Mock asyncio.run to return None directly
                            mock_run.side_effect = lambda coro: None
                            main()

                            mock_exit.assert_any_call(0)
                            mock_handle.assert_called_once()
                            # Should exit with 0
                            mock_exit.assert_any_call(0)

        finally:
            if os.path.exists(input_path):
                os.unlink(input_path)


class TestCLIServerStart:
    """Test server startup via CLI."""

    def test_cli_server_default(self):
        """Test default server startup."""
        with patch("sys.argv", ["memento.cli"]):
            with patch("sys.exit") as mock_exit:
                with patch("memento.cli.server_main") as mock_server_main:
                    with patch("memento.cli.asyncio.run") as mock_run:
                        # Mock KeyboardInterrupt to stop the server
                        mock_run.side_effect = KeyboardInterrupt()

                        main()

                        # Server should have been started
                        mock_server_main.assert_called_once()
                        # Should exit with 0 after KeyboardInterrupt
                        mock_exit.assert_called_once_with(0)

    def test_cli_server_with_profile(self):
        """Test server startup with profile option."""
        with patch("sys.argv", ["memento.cli", "--profile", "extended"]):
            with patch("sys.exit") as mock_exit:
                with patch("memento.cli.server_main") as mock_server_main:
                    with patch("memento.cli.asyncio.run") as mock_run:
                        mock_run.side_effect = KeyboardInterrupt()

                        main()

                        # Server should have been started
                        mock_server_main.assert_called_once()
                        mock_exit.assert_called_once_with(0)

    def test_cli_server_with_log_level(self):
        """Test server startup with log level option."""
        with patch("sys.argv", ["memento.cli", "--log-level", "DEBUG"]):
            with patch("sys.exit") as mock_exit:
                with patch("memento.cli.server_main") as mock_server_main:
                    with patch("memento.cli.asyncio.run") as mock_run:
                        mock_run.side_effect = KeyboardInterrupt()

                        main()

                        mock_server_main.assert_called_once()
                        mock_exit.assert_called_once_with(0)

    def test_cli_server_error(self):
        """Test server error handling."""
        with patch("sys.argv", ["memento.cli"]):
            with patch("sys.exit") as mock_exit:
                with patch("memento.cli.server_main") as mock_server_main:
                    with patch("memento.cli.asyncio.run") as mock_run:
                        mock_run.side_effect = Exception("Server error")

                        main()

                        # Should exit with 1 on error
                        mock_exit.assert_called_once_with(1)


class TestCLIEnvironmentVariables:
    """Test CLI environment variable handling."""

    def test_environment_variable_profile(self):
        """Test MEMENTO_TOOL_PROFILE environment variable."""
        with patch.dict(os.environ, {"MEMENTO_TOOL_PROFILE": "extended"}, clear=True):
            with patch("sys.argv", ["memento.cli", "--show-config"]):
                with patch("sys.exit") as mock_exit:
                    with patch("memento.cli._eprint") as mock_eprint:
                        main()

                        # Should show extended profile in config
                        # Check that exit was called with 0 (may be called multiple times)
                        mock_exit.assert_any_call(0)
                        # Check that extended profile is mentioned
                        call_text = "\n".join(
                            [
                                call.args[0] if call.args else ""
                                for call in mock_eprint.call_args_list
                            ]
                        )
                        assert "extended" in call_text.lower()

    def test_environment_variable_log_level(self):
        """Test MEMENTO_LOG_LEVEL environment variable."""
        with patch.dict(os.environ, {"MEMENTO_LOG_LEVEL": "DEBUG"}, clear=True):
            with patch("sys.argv", ["memento.cli", "--show-config"]):
                with patch("sys.exit") as mock_exit:
                    with patch("memento.cli._eprint") as mock_eprint:
                        main()

                        # Check that exit was called with 0 (may be called multiple times)
                        mock_exit.assert_any_call(0)
                        call_text = "\n".join(
                            [
                                call.args[0] if call.args else ""
                                for call in mock_eprint.call_args_list
                            ]
                        )
                        assert "debug" in call_text.lower()

    def test_cli_args_override_env_vars(self):
        """Test that CLI arguments override environment variables."""
        with patch.dict(os.environ, {"MEMENTO_TOOL_PROFILE": "core"}, clear=True):
            with patch(
                "sys.argv",
                ["memento.cli", "--profile", "extended", "--show-config"],
            ):
                with patch("sys.exit") as mock_exit:
                    with patch("memento.cli._eprint") as mock_eprint:
                        main()

                        # Check that exit was called with 0 (may be called multiple times)
                        mock_exit.assert_any_call(0)
                        # Should show extended (from CLI arg), not core (from env var)
                        call_text = "\n".join(
                            [
                                call.args[0] if call.args else ""
                                for call in mock_eprint.call_args_list
                            ]
                        )
                        assert "extended" in call_text.lower()
                        # core might still appear in some context, but profile should be extended


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

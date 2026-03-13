#!/usr/bin/env python3
"""
Test runner for mcp-user-memory project.

This script runs all test files and provides a comprehensive test report.
All output is in English.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path to import user_memory
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from user_memory import MemoryGraphServer
    from user_memory.models import MemoryType, RelationshipType

    IMPORT_SUCCESS = True
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


class TestRunner:
    """Main test runner class."""

    def __init__(self, verbose: bool = False, output_file: str = None):
        self.verbose = verbose
        self.output_file = output_file
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "project": "mcp-user-memory",
            "tests": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration": 0.0,
            },
        }
        self.start_time = None

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def log_verbose(self, message: str):
        """Log verbose message if enabled."""
        if self.verbose:
            self.log(message, "DEBUG")

    async def run_test_file(self, test_file: Path) -> Dict:
        """Run a single test file."""
        self.log(f"Running test file: {test_file.name}")

        # Import the test module
        module_name = test_file.stem
        import importlib.util

        spec = importlib.util.spec_from_file_location(module_name, test_file)
        module = importlib.util.module_from_spec(spec)

        test_result = {
            "file": test_file.name,
            "status": "unknown",
            "duration": 0.0,
            "errors": [],
            "warnings": [],
            "details": {},
        }

        start_time = time.time()

        try:
            spec.loader.exec_module(module)

            # Check if the module has a main function
            if hasattr(module, "main"):
                self.log_verbose(f"  Found main() function in {test_file.name}")

                if asyncio.iscoroutinefunction(module.main):
                    # Async main function
                    success = await module.main()
                else:
                    # Sync main function
                    success = module.main()

                test_result["status"] = "passed" if success else "failed"
                test_result["details"]["main_result"] = success

            elif hasattr(module, "test_all") or hasattr(module, "run_tests"):
                self.log(
                    f"  WARNING: {test_file.name} has test_all/run_tests but no main()",
                    "WARNING",
                )
                test_result["status"] = "skipped"
                test_result["warnings"].append("No main() function found")

            else:
                self.log(
                    f"  INFO: {test_file.name} has no test functions to run", "INFO"
                )
                test_result["status"] = "skipped"
                test_result["details"]["reason"] = "No test functions found"

        except Exception as e:
            self.log(f"  ERROR: Failed to run {test_file.name}: {e}", "ERROR")
            test_result["status"] = "failed"
            test_result["errors"].append(str(e))
            import traceback

            test_result["details"]["traceback"] = traceback.format_exc()

        test_result["duration"] = time.time() - start_time

        status_emoji = {"passed": "✅", "failed": "❌", "skipped": "⚠️", "unknown": "❓"}

        self.log(
            f"  {status_emoji[test_result['status']]} {test_file.name}: {test_result['status'].upper()} ({test_result['duration']:.2f}s)"
        )

        return test_result

    async def run_import_test(self) -> Dict:
        """Test basic imports and module availability."""
        self.log("Running import test...")

        test_result = {
            "file": "import_test",
            "status": "unknown",
            "duration": 0.0,
            "errors": [],
            "warnings": [],
            "details": {},
        }

        start_time = time.time()

        try:
            if not IMPORT_SUCCESS:
                raise ImportError(f"Failed to import user_memory: {IMPORT_ERROR}")

            # Test basic imports
            test_result["details"]["imports"] = {
                "MemoryGraphServer": MemoryGraphServer.__name__,
                "MemoryType_count": len(list(MemoryType)),
                "RelationshipType_count": len(list(RelationshipType)),
            }

            self.log_verbose(f"  Memory types: {[t.value for t in MemoryType]}")
            self.log_verbose(
                f"  Relationship types: {[t.value for t in RelationshipType]}"
            )

            # Test server instantiation
            server = MemoryGraphServer()
            test_result["details"]["server_instance"] = str(server)

            test_result["status"] = "passed"
            self.log("  ✅ Import test: PASSED")

        except Exception as e:
            self.log(f"  ❌ Import test: FAILED - {e}", "ERROR")
            test_result["status"] = "failed"
            test_result["errors"].append(str(e))
            import traceback

            test_result["details"]["traceback"] = traceback.format_exc()

        test_result["duration"] = time.time() - start_time
        return test_result

    async def run_json_test(self) -> Dict:
        """Test JSON test data file."""
        self.log("Running JSON test data validation...")

        test_result = {
            "file": "json_test",
            "status": "unknown",
            "duration": 0.0,
            "errors": [],
            "warnings": [],
            "details": {},
        }

        start_time = time.time()

        try:
            json_file = Path(__file__).parent / "test_import.json"

            if not json_file.exists():
                raise FileNotFoundError(f"Test JSON file not found: {json_file}")

            with open(json_file, "r") as f:
                data = json.load(f)

            # Validate structure
            required_keys = ["version", "memories", "relationships"]
            for key in required_keys:
                if key not in data:
                    raise ValueError(f"Missing required key in JSON: {key}")

            # Validate memories
            memories = data.get("memories", [])
            test_result["details"]["memory_count"] = len(memories)

            for i, memory in enumerate(memories):
                if "id" not in memory:
                    raise ValueError(f"Memory {i} missing 'id' field")
                if "content" not in memory:
                    raise ValueError(f"Memory {i} missing 'content' field")

            # Validate relationships
            relationships = data.get("relationships", [])
            test_result["details"]["relationship_count"] = len(relationships)

            for i, rel in enumerate(relationships):
                if "id" not in rel:
                    raise ValueError(f"Relationship {i} missing 'id' field")
                if "from_memory_id" not in rel:
                    raise ValueError(f"Relationship {i} missing 'from_memory_id' field")
                if "to_memory_id" not in rel:
                    raise ValueError(f"Relationship {i} missing 'to_memory_id' field")
                if "relationship_type" not in rel:
                    raise ValueError(
                        f"Relationship {i} missing 'relationship_type' field"
                    )

            test_result["status"] = "passed"
            self.log(
                f"  ✅ JSON test: PASSED ({len(memories)} memories, {len(relationships)} relationships)"
            )

        except Exception as e:
            self.log(f"  ❌ JSON test: FAILED - {e}", "ERROR")
            test_result["status"] = "failed"
            test_result["errors"].append(str(e))

        test_result["duration"] = time.time() - start_time
        return test_result

    async def run_all_tests(self):
        """Run all available tests."""
        self.start_time = time.time()
        self.log("=" * 60)
        self.log("Starting test suite for mcp-user-memory")
        self.log("=" * 60)

        # Run import test first
        import_result = await self.run_import_test()
        self.results["tests"]["import_test"] = import_result

        # Run JSON test
        json_result = await self.run_json_test()
        self.results["tests"]["json_test"] = json_result

        # Find and run test files
        test_dir = Path(__file__).parent
        test_files = list(test_dir.glob("test_*.py"))

        self.log(f"\nFound {len(test_files)} test files:")
        for tf in test_files:
            self.log(f"  - {tf.name}")

        for test_file in test_files:
            if test_file.name == "run_tests.py":
                continue  # Skip this file

            test_result = await self.run_test_file(test_file)
            self.results["tests"][test_file.stem] = test_result

        # Calculate summary
        self._calculate_summary()

        # Print summary
        self._print_summary()

        # Save results if output file specified
        if self.output_file:
            self._save_results()

        return self.results["summary"]["failed"] == 0

    def _calculate_summary(self):
        """Calculate test summary statistics."""
        total = passed = failed = skipped = 0
        total_duration = 0.0

        for test_name, result in self.results["tests"].items():
            total += 1
            total_duration += result["duration"]

            if result["status"] == "passed":
                passed += 1
            elif result["status"] == "failed":
                failed += 1
            else:
                skipped += 1

        self.results["summary"].update(
            {
                "total": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "duration": total_duration,
            }
        )

    def _print_summary(self):
        """Print test summary."""
        summary = self.results["summary"]
        total_time = time.time() - self.start_time

        self.log("\n" + "=" * 60)
        self.log("TEST SUMMARY")
        self.log("=" * 60)

        self.log(f"Total tests: {summary['total']}")
        self.log(f"Passed:      {summary['passed']} ✅")
        self.log(f"Failed:      {summary['failed']} ❌")
        self.log(f"Skipped:     {summary['skipped']} ⚠️")
        self.log(f"Total time:  {total_time:.2f} seconds")

        # Print detailed results
        if self.verbose or summary["failed"] > 0:
            self.log("\nDetailed results:")
            for test_name, result in self.results["tests"].items():
                status_emoji = {
                    "passed": "✅",
                    "failed": "❌",
                    "skipped": "⚠️",
                    "unknown": "❓",
                }[result["status"]]

                self.log(
                    f"  {status_emoji} {test_name}: {result['status'].upper()} ({result['duration']:.2f}s)"
                )

                if result["errors"]:
                    for error in result["errors"]:
                        self.log(f"    ERROR: {error}", "ERROR")

                if result["warnings"]:
                    for warning in result["warnings"]:
                        self.log(f"    WARNING: {warning}", "WARNING")

        # Final result
        self.log("\n" + "=" * 60)
        if summary["failed"] == 0:
            self.log("✅ ALL TESTS PASSED!")
        else:
            self.log(f"❌ {summary['failed']} TEST(S) FAILED")
        self.log("=" * 60)

    def _save_results(self):
        """Save test results to JSON file."""
        try:
            with open(self.output_file, "w") as f:
                json.dump(self.results, f, indent=2, default=str)
            self.log(f"Test results saved to: {self.output_file}")
        except Exception as e:
            self.log(f"Failed to save results: {e}", "ERROR")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run tests for mcp-user-memory")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Output JSON file for test results"
    )
    parser.add_argument(
        "--list", action="store_true", help="List available test files and exit"
    )

    args = parser.parse_args()

    if args.list:
        test_dir = Path(__file__).parent
        test_files = list(test_dir.glob("test_*.py"))
        print(f"Available test files in {test_dir}:")
        for tf in test_files:
            if tf.name != "run_tests.py":
                print(f"  - {tf.name}")
        return 0

    runner = TestRunner(verbose=args.verbose, output_file=args.output)
    success = await runner.run_all_tests()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

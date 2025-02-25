import logging
import subprocess
from pathlib import Path
from typing import Optional

from agents.utils.models import TestResult

logger = logging.getLogger(__name__)


def run_all_tests(class_dir: Path, yaml_path: Optional[Path]) -> tuple[TestResult, Optional[TestResult]]:
    """Runs LLM-generated tests and (optionally) ground truth tests."""
    llm_test_dir = class_dir / "LLMGeneratedTests"
    llm_results = _run_tests(llm_test_dir, "LLM generated tests")
    logger.info(
        "[LLM generated tests] Run complete - Passed: %d, Failed: %d, Skipped: %d, Duration: %d ms",
        llm_results.passed,
        llm_results.failed,
        llm_results.skipped,
        llm_results.duration_ms,
    )

    gt_results = None
    if yaml_path:
        gt_test_dir = class_dir / "GroundTruthTests"
        if gt_test_dir.exists():
            gt_results = _run_tests(gt_test_dir, "Ground truth tests")
            logger.info(
                "[Ground truth tests] Run complete - Passed: %d, Failed: %d, Skipped: %d, Duration: %d ms",
                gt_results.passed,
                gt_results.failed,
                gt_results.skipped,
                gt_results.duration_ms,
            )

    return llm_results, gt_results


def _run_tests(project_dir: Path, project_name: str) -> TestResult:
    """Runs tests in the given project directory."""
    logger.info(f"[{project_name}] Starting tests in {project_dir} ...")

    try:
        proc = subprocess.run(
            ["dotnet", "test", "--no-build", "--nologo"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=480,
        )
        stdout_full = proc.stdout + "\n" + proc.stderr

        if proc.returncode == 0:
            logger.info(f"[{project_name}] Tests completed successfully.")
        else:
            logger.info(f"[{project_name}] Tests reported failures/exit code {proc.returncode}.")
        return _parse_test_output(stdout_full)
    except Exception as ex:
        error_msg = f"Test execution failed: {str(ex)}"
        logger.error(f"[{project_name}] {error_msg}")
        return TestResult(failed=1, error_details=[error_msg], raw_output="")


# TODO: we should use a runner with structured output rather than parsing
def _parse_test_output(test_stdout: str) -> TestResult:
    """Parses the test output and returns a TestResult."""
    passed = failed = skipped = duration_ms = 0
    error_details = []

    try:
        for line in test_stdout.splitlines():
            line_strip = line.strip()

            if "Failed!  -" in line_strip or "Passed!  -" in line_strip:
                stats_part = line_strip.split("-")[1].strip()
                parts = stats_part.split(",")
                for part in parts:
                    part = part.strip()
                    if part.startswith("Failed:"):
                        failed = int(part.split(":")[1].strip())
                    elif part.startswith("Passed:"):
                        passed = int(part.split(":")[1].strip())
                    elif part.startswith("Skipped:"):
                        skipped = int(part.split(":")[1].strip())
                    elif part.startswith("Duration:"):
                        time_str = part.replace("Duration:", "").replace("ms", "").strip()
                        time_str = time_str.split(" ")[0]
                        try:
                            duration_ms = int(time_str)
                        except ValueError:
                            duration_ms = 0

            if "[FAIL]" in line_strip:
                error_details.append(line_strip)
    except Exception as e:
        logger.error(f"Error parsing test output: {e}")

    return TestResult(
        passed=passed,
        failed=failed,
        skipped=skipped,
        duration_ms=duration_ms,
        error_details=error_details if error_details else None,
        raw_output=test_stdout,
    )

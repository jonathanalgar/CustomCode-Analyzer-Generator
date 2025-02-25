import logging
import re
import subprocess
from pathlib import Path

from agents.utils.models import BuildMetrics

logger = logging.getLogger(__name__)


def build_solution(class_dir: Path) -> tuple[BuildMetrics, str]:
    """Builds the solution in the given directory."""
    logger.info("Starting build process...")
    try:
        proc = subprocess.run(
            ["dotnet", "build", "--nologo", "-nowarn:CS9057"],
            cwd=class_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        build_stdout = proc.stdout + "\n" + proc.stderr
        logger.debug(f"Full build output:\n{build_stdout}")

    except Exception as e:
        error_msg = f"Build encountered an unexpected error: {str(e)}"
        logger.error(error_msg)
        return BuildMetrics(warnings=[], errors=[error_msg], success=False, duration_ms=0), ""

    metrics = _parse_build_output(build_stdout)
    return metrics, build_stdout


# TODO: we should use a runner with structured output rather than parsing
def _parse_build_output(build_stdout: str) -> BuildMetrics:
    """Extracts warnings, errors, success, and duration from build output."""
    warnings = []
    errors = []
    seen_warning_lines = set()
    seen_error_lines = set()
    duration_ms = 0

    for line in build_stdout.splitlines():
        if ": warning " in line and line not in seen_warning_lines:
            warnings.append(line)
            seen_warning_lines.add(line)

        if ": error " in line and line not in seen_error_lines:
            errors.append(line)
            seen_error_lines.add(line)

    success = "Build succeeded" in build_stdout and len(errors) == 0

    try:
        time_elapsed_pattern = r"Time Elapsed\s+(\d+):(\d+):([\d.]+)"
        match = re.search(time_elapsed_pattern, build_stdout)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = float(match.group(3))
            duration_ms = int((hours * 3600 + minutes * 60 + seconds) * 1000)
    except (ValueError, AttributeError, IndexError) as e:
        logger.warning(f"Failed to parse build duration: {e}")

    return BuildMetrics(
        warnings=warnings,
        errors=errors,
        success=success,
        duration_ms=duration_ms,
        raw_output=build_stdout,
    )

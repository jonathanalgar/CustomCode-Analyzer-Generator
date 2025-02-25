import logging
import subprocess
import tempfile
from pathlib import Path

from agents.validation.constants import ODC_TEST_GENERATOR_EXE

logger = logging.getLogger(__name__)


def display_directory_structure(directory: Path, prefix: str = "", is_last: bool = True) -> None:
    """Displays a tree-like view of directory contents."""
    directory_name = directory.name + "/"
    logger.info(prefix + ("└── " if is_last else "├── ") + directory_name)

    children_prefix = prefix + ("    " if is_last else "│   ")
    items = sorted(
        [p for p in directory.iterdir() if not (p.is_dir() and p.name == "obj")],
        key=lambda x: (not x.is_dir(), x.name),
    )

    for i, path in enumerate(items):
        is_last_item = i == len(items) - 1
        if path.is_dir():
            display_directory_structure(path, children_prefix, is_last_item)
        else:
            logger.info(children_prefix + ("└── " if is_last_item else "├── ") + path.name)


def extract_class_name(code: str) -> str:
    """Uses CCAGTestGenerator to extract the class name."""
    with tempfile.NamedTemporaryFile(suffix=".cs", mode="w", delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name).resolve()
        try:
            tmp_file.write(code)
            tmp_file.flush()

            result = subprocess.run(
                [
                    str(ODC_TEST_GENERATOR_EXE),
                    "--classname",
                    str(tmp_path),
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )

            class_name = result.stdout.strip()
            if not class_name:
                raise ValueError("CCAGTestGenerator did not return a class name")

            return class_name
        finally:
            tmp_path.unlink(missing_ok=True)



"""Defines paths related to the CCAGTestGenerator project."""

from pathlib import Path

TARGET_FRAMEWORK = "net8.0"

# Project file path (for builds)
_ODC_TEST_GENERATOR_PROJECT = (
    Path(__file__).parent.parent / "evaluation/CCAGTestGenerator/CCAGTestGenerator.Core/CCAGTestGenerator.Core.csproj"
).resolve()

if not _ODC_TEST_GENERATOR_PROJECT.exists():
    raise FileNotFoundError(
        f"CCAGTestGenerator project not found at expected path: {_ODC_TEST_GENERATOR_PROJECT}\n"
        f"Current file location: {Path(__file__)}\n"
        f"Absolute path attempted: {_ODC_TEST_GENERATOR_PROJECT.absolute()}"
    )

ODC_TEST_GENERATOR_EXE = (
    _ODC_TEST_GENERATOR_PROJECT.parent / "bin" / "Release" / TARGET_FRAMEWORK / "CCAGTestGenerator.Core"
)

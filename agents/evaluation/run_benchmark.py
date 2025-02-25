#!/usr/bin/env python3

import argparse
import logging
from pathlib import Path
from typing import List

from agents.evaluation.benchmark import run_benchmark
from agents.utils.logger_config import setup_logger
from agents.utils.model_definitions import get_model


def setup_args() -> argparse.ArgumentParser:
    """Defines and returns CLI argument parser."""
    parser = argparse.ArgumentParser(description="Run benchmarks for code generation")

    parser.add_argument(
        "--test-cases",
        type=str,
        nargs="+",
        default=["agents/evaluation/ground_truth/power.yml"],
        help="List of test case YAML files or folders containing YAML files (default: ground_truth/power.yml)",
    )

    parser.add_argument("--prompt", type=str, default="ONE_SHOT", help="Prompt to use (default: ONE_SHOT)")

    parser.add_argument(
        "--search-model",
        type=str,
        default="gpt4o-mini",
        help="Model to use for NuGet package search (default: gpt4o-mini)",
    )

    parser.add_argument(
        "--generation-model",
        type=str,
        default="gpt4o",
        help="Model to use for code generation (default: gpt4o)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    return parser


def collect_yaml_files(paths: List[str]) -> List[Path]:
    """Recursively collects YAML files from given paths."""
    yaml_files = []
    for path_str in paths:
        path = Path(path_str)
        if path.is_file() and path.suffix.lower() in [".yml", ".yaml"]:
            yaml_files.append(path)
        elif path.is_dir():
            yaml_files.extend(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in [".yml", ".yaml"])
    return yaml_files


def main() -> None:
    """Main entry point for running benchmarks."""
    parser = setup_args()
    args = parser.parse_args()

    logger = setup_logger(level=getattr(logging, args.log_level))

    # Collect all YAML files
    test_cases = collect_yaml_files(args.test_cases)
    if not test_cases:
        logger.error("No YAML files found in the specified paths")
        return

    logger.info(f"Found {len(test_cases)} YAML files to process")

    search_term_llm = get_model(args.search_model)
    code_generation_llm = get_model(args.generation_model)

    try:
        run_benchmark(
            test_cases=test_cases,
            prompt_key=args.prompt,
            search_term_llm=search_term_llm,
            code_generation_llm=code_generation_llm,
        )

    except Exception as e:
        logger.error(f"Error running benchmark: {str(e)}")
        raise


if __name__ == "__main__":
    main()

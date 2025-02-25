import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel

from agents.utils.models import BuildMetrics, ValidationInputs, ValidationMetrics
from agents.validation.custom_exceptions import (
    PackageInstallationError,
    ProjectSetupError,
)

from . import build, setup, test, utils

logger = logging.getLogger(__name__)


def validate_generated_code(
    validation_inputs: ValidationInputs,
    search_term_llm: Optional[BaseChatModel] = None,
    target_dir: Optional[Path] = None,
    retain_on_failure: bool = False,
) -> ValidationMetrics:
    """Validates the generated implementation and tests, returning metrics."""
    implementation_code = validation_inputs.implementation_code
    unit_test_code = validation_inputs.unit_test_code
    nuget_packages = validation_inputs.nuget_packages
    yaml_path = validation_inputs.yaml_path

    build_metrics = BuildMetrics(success=False, duration_ms=0)
    llm_results = None
    gt_results = None
    odc_generator_logs = ""

    logger.info("Starting code validation...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        try:
            class_name = utils.extract_class_name(implementation_code)
        except ValueError as e:
            logger.error(f"No valid public class found: {str(e)}")
            return ValidationMetrics(
                build_metrics=build_metrics,
                llm_test_results=None,
                ground_truth_test_results=None,
                odc_generator_output=str(e),
            )
        except Exception as e:
            error_msg = getattr(e, "stderr", str(e))
            logger.error(f"Failed to extract class name: {error_msg}")
            return ValidationMetrics(
                build_metrics=build_metrics,
                llm_test_results=None,
                ground_truth_test_results=None,
                odc_generator_output=error_msg,
            )

        class_dir = tmp_path / class_name
        class_dir.mkdir(parents=True, exist_ok=True)

        try:
            odc_generator_logs, action_map_info = setup.create_and_setup_projects(
                class_dir, class_name, implementation_code, unit_test_code, nuget_packages, search_term_llm, yaml_path
            )
        except ProjectSetupError as e:
            logger.error("Project setup failed: %s", str(e))
            return ValidationMetrics(
                build_metrics=build_metrics,
                llm_test_results=None,
                ground_truth_test_results=None,
                odc_generator_output=e.output,
            )
        except PackageInstallationError as e:
            logger.error("Required package installation failed: %s", str(e))
            return ValidationMetrics(
                build_metrics=build_metrics,
                llm_test_results=None,
                ground_truth_test_results=None,
                odc_generator_output=e.error_output,
            )
        except Exception as e:
            error_msg = getattr(e, "stderr", str(e))
            logger.error("Project setup encountered an error: %s", error_msg)
            return ValidationMetrics(
                build_metrics=build_metrics,
                llm_test_results=None,
                ground_truth_test_results=None,
                odc_generator_output=error_msg,
            )

        # If we have ground truth YAML but the action map validation fails or indicates multiple actions, skip build
        if yaml_path and (
            action_map_info is None
            or not action_map_info.matches
            or int(action_map_info.implementation.split("(")[0]) > 1
        ):
            logger.info("Skipping build based on action map validation.")
            return ValidationMetrics(
                build_metrics=build_metrics,
                llm_test_results=None,
                ground_truth_test_results=None,
                odc_generator_output=odc_generator_logs,
                action_map_info=action_map_info,
            )

        build_metrics, _ = build.build_solution(class_dir)
        logger.info(
            "Build finished. Success: %s, Duration: %.2f seconds",
            build_metrics.success,
            build_metrics.duration_ms / 1000,
        )
        if build_metrics.warnings:
            logger.info("Build generated %d warnings", len(build_metrics.warnings))
        if not build_metrics.success:
            logger.info("Build failed with %d errors; skipping tests.", len(build_metrics.errors))
            result = ValidationMetrics(
                build_metrics=build_metrics,
                llm_test_results=None,
                ground_truth_test_results=None,
                odc_generator_output=odc_generator_logs,
                solution_dir=class_dir if retain_on_failure else None,
            )

        # Build successful -> run tests
        if build_metrics.success:
            llm_results, gt_results = test.run_all_tests(class_dir, yaml_path)
            result = ValidationMetrics(
                build_metrics=build_metrics,
                llm_test_results=llm_results,
                ground_truth_test_results=gt_results,
                odc_generator_output=odc_generator_logs,
                solution_dir=class_dir,
                action_map_info=action_map_info,
            )

        if target_dir is not None and (build_metrics.success or retain_on_failure):
            try:
                solution_dir = target_dir / class_name
                if solution_dir.exists():
                    logger.info(f"Removing existing solution at {solution_dir}")
                    shutil.rmtree(solution_dir)
                logger.info(f"Copying solution to {solution_dir}")
                shutil.copytree(class_dir, solution_dir, ignore=shutil.ignore_patterns("bin", "obj"))
                result.solution_dir = solution_dir
            except Exception as e:
                logger.error(f"Failed to copy solution to target directory: {e}")

        return result

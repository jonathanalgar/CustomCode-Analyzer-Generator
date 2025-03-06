import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel

from agents.generation.llm_generation import (
    LLMInputs,
    generate_code,
    run_reflection_pass,
)
from agents.generation.prompts import PROMPTS
from agents.utils.postvalidation import (
    get_icon_for_solution,
    get_token_stats,
    prettify_code,
)
from agents.validation.workflow import ValidationInputs, validate_generated_code

logger = logging.getLogger(__name__)


def generate_and_validate(
    use_case: str,
    prompt_key: str,
    search_term_llm: BaseChatModel,
    code_generation_llm: BaseChatModel,
    output_dir: Optional[Path] = None,
    stream: bool = False,
) -> Optional[Path]:
    """Generates and validates an external library for a given use case."""
    logger.info(f"Generating solution for: {use_case}")

    env_retain = os.getenv("RETAIN_ON_FAILURE")
    if env_retain and env_retain.strip():
        retain_on_failure = env_retain.lower() in ["true", "1", "yes", "y"]
        logger.info(f"Using RETAIN_ON_FAILURE={retain_on_failure} from .env")
    else:
        retain_input = input("Retain solution even if build fails? (y/n) [default: y]: ")
        retain_on_failure = retain_input.lower() in ["y", "yes"] or retain_input == ""
        print("(Tip: add RETAIN_ON_FAILURE=true or RETAIN_ON_FAILURE=true to .env to skip this input prompt in future)")

    llm_inputs = LLMInputs(
        use_case=use_case,
        prompt=PROMPTS[prompt_key],
        search_term_llm=search_term_llm,
        code_generation_llm=code_generation_llm,
    )

    # First pass code generation
    generated_code, _, code_gen_prompt, project_id = generate_code(llm_inputs, stream=stream)

    validation_inputs = ValidationInputs(
        implementation_code=generated_code["implementation_code"],
        unit_test_code=generated_code["unit_test_code"],
        nuget_packages=generated_code["nuget_packages"],
        yaml_path=None,
    )

    validation_metrics = validate_generated_code(
        validation_inputs=validation_inputs,
        target_dir=output_dir,
        retain_on_failure=retain_on_failure,
        search_term_llm=search_term_llm,
    )

    # Reflection pass if build/tests failed
    reflection_result = run_reflection_pass(
        llm_inputs=llm_inputs,
        validation_metrics=validation_metrics,
        code_gen_prompt_with_first_result=code_gen_prompt,
        stream=stream,
    )

    if reflection_result:
        reflection_code, _, _ = reflection_result

        reflection_validation_inputs = ValidationInputs(
            implementation_code=reflection_code["implementation_code"],
            unit_test_code=reflection_code["unit_test_code"],
            nuget_packages=reflection_code["nuget_packages"],
            yaml_path=None,
        )

        reflection_metrics = validate_generated_code(
            validation_inputs=reflection_validation_inputs,
            target_dir=output_dir,
            retain_on_failure=retain_on_failure,
            search_term_llm=search_term_llm,
        )

    # If either the original or reflection build succeeded, keep the solution
    if validation_metrics.build_metrics.success or reflection_metrics.build_metrics.success or retain_on_failure:
        logger.info(f"Solution generation successful - retaining solution in {validation_metrics.solution_dir}")

        # Add an icon if FREEPIK_API_KEY is set
        api_key = os.getenv("FREEPIK_API_KEY")
        if api_key and validation_metrics.solution_dir:
            icon_path = get_icon_for_solution(
                use_case=use_case,
                search_term_llm=search_term_llm,
                class_dir=validation_metrics.solution_dir / validation_metrics.solution_dir.name,
            )
            if icon_path:
                logger.info("Successfully added icon to solution")

        # Format the code using CSharpier
        if validation_metrics.solution_dir:
            prettify_code(validation_metrics.solution_dir)

        # Copy the generate_upload_package.ps1 script
        resources_dir = Path(__file__).parent / "resources"
        src_script = resources_dir / "generate_upload_package.ps1"
        if src_script.exists() and validation_metrics.solution_dir:
            dest_script = (
                validation_metrics.solution_dir / validation_metrics.solution_dir.name / "generate_upload_package.ps1"
            )
            shutil.copy2(src_script, dest_script)
            logger.info(f"Copied {src_script.name} implementation project directory")

        if project_id:
            total_tokens, total_cost, url = get_token_stats(project_id)
            logger.info(f"Total tokens: {total_tokens:,} / ${total_cost:.2f} (via {url})")
        else:
            logger.info("No project ID available for token statistics")

        return validation_metrics.solution_dir
    else:
        if validation_metrics.solution_dir and validation_metrics.solution_dir.exists():
            shutil.rmtree(validation_metrics.solution_dir)

        if project_id:
            total_tokens, total_cost, url = get_token_stats(project_id)
            logger.info(f"Total tokens: {total_tokens:,} / ${total_cost:.2f} (via {url})")
        else:
            logger.info("No project ID available for token statistics")

        return None

import logging
import subprocess
from pathlib import Path
from typing import Optional

import yaml
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agents.utils.models import ActionMapInfo, ActionMapResult
from agents.validation.constants import ODC_TEST_GENERATOR_EXE

logger = logging.getLogger(__name__)


def validate_action_map(
    implementation_project_dir: Path,
    class_name: str,
    yaml_path: Path,
    search_term_llm: BaseChatModel,
) -> ActionMapResult:
    """Checks that the action map matches the ground truth from the YAML."""
    if not yaml_path:
        return ActionMapResult(True, "", None, None)

    impl_file = implementation_project_dir / f"{class_name}.cs"

    try:
        # Ask CCAGTestGenerator to map out the actions in the implementation
        action_map_proc = subprocess.run(
            [
                str(ODC_TEST_GENERATOR_EXE),
                "--map",
                str(impl_file),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        impl_map = action_map_proc.stdout.strip()
        if not impl_map:
            return ActionMapResult(False, "Empty implementation map", None, None)

        # Parse YAML ground truth
        try:
            with open(yaml_path, "r") as f:
                yaml_content = yaml.safe_load(f)
        except (yaml.YAMLError, IOError) as e:
            logger.error(f"Failed to read YAML file: {e}")
            return ActionMapResult(False, f"YAML error: {str(e)}", None, None)

        # Generate ground truth map
        try:
            actions = yaml_content["actions"]
            num_actions = len(actions)
            param_counts = [len(action["params"]) for action in actions.values()]
            param_counts.sort()
            gt_map = f"{num_actions}({', '.join(map(str, param_counts))})"
        except (KeyError, AttributeError) as e:
            logger.error(f"Invalid YAML structure: {e}")
            return ActionMapResult(False, f"Invalid YAML structure: {str(e)}", None, None)

        action_map_info = ActionMapInfo(implementation=impl_map, ground_truth=gt_map, matches=impl_map == gt_map)

        logger.info("Action map [# Actions(# Parameters)]:")
        logger.info(f"  Ground truth  : {action_map_info.ground_truth}")
        logger.info(f"  Implementation: {action_map_info.implementation}")
        logger.info(f"  Match?          {'✓' if action_map_info.matches else '✗'}")

        if not action_map_info.matches:
            logger.info("Action maps don't match - skipping benchmarking.")
            return ActionMapResult(False, "", action_map_info, None)

        try:
            num_actions, param_counts = _parse_impl_map(impl_map)

            if num_actions > 1:
                logger.error(
                    f"Implementation contains {num_actions} actions. Only implementations with 1 action are supported for benchmarking."
                )
                return ActionMapResult(False, "", action_map_info, None)

            param_count = param_counts[0]
            if param_count == 1:
                logger.info(
                    "[Ground truth tests] With 1 parameter for 1 action there is a one-to-one mapping between the ground truth parameter and generated implementation code parameter."
                )
                return ActionMapResult(True, "", action_map_info, None)
            else:
                logger.info(
                    "[Ground truth tests] With >1 parameter for 1 action we need to match the ground truth parameters with the generated implementation code parameters."
                )
                param_mapping = _get_param_mapping(impl_file, yaml_path, search_term_llm)
                if param_mapping is None:
                    return ActionMapResult(False, "Failed to generate parameter mapping", action_map_info, None)
                return ActionMapResult(True, "", action_map_info, param_mapping)
        except ValueError as e:
            logger.error(f"Failed to parse implementation map: {e}")
            return ActionMapResult(False, str(e), None, None)
    except Exception as e:
        logger.error(f"Unexpected error in action map validation: {e}")
        return ActionMapResult(False, str(e), None, None)


def _parse_impl_map(impl_map: str) -> tuple[int, list[int]]:
    try:
        actions_str, params_str = impl_map.split("(", 1)
        num_actions = int(actions_str)

        params_str = params_str.rstrip(")")
        param_counts = [int(p.strip()) for p in params_str.split(",")] if params_str else []

        return num_actions, param_counts
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid implementation map format: {impl_map}") from e


def _get_param_mapping(
    impl_file: Path,
    yaml_path: Path,
    search_term_llm: BaseChatModel,
) -> Optional[str]:
    """Generates a param mapping between implementation and YAML."""
    try:
        report_proc = subprocess.run(
            [
                str(ODC_TEST_GENERATOR_EXE),
                "--report",
                str(impl_file),
                str(yaml_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

        example1 = """\
C# method name: Power
C# parameters:
- baseNumber (double)
- exponent (double)

YAML method name: Power
YAML parameters:
- base
- exponent\
        """
        example1_output = "(Power:base=Power:baseNumber),(Power:exponent=Power:exponent)"

        messages = [
            SystemMessage(
                content="I will give you a C# method name and its parameters and a YAML method name and its parameters. Each YAML parameter should have a C# equivalent parameter. I want you to create a map of this one-to-one parameter equivalence in the exact format '(YAMLMethodName:YAMLParameter1=CSharpMethodName:CSharpParameter1),(YAMLMethodName:YAMLParameter2=CSharpMethodName:CSharpParameter2),...'"
            ),
            HumanMessage(content=example1),
            AIMessage(content=example1_output),
            HumanMessage(content=report_proc.stdout),
        ]

        mapping_response = search_term_llm.invoke(messages)
        mapping = mapping_response.content
        if isinstance(mapping, str):
            mapping = mapping.strip()
        else:
            logger.error("Unexpected response format for mapping")
            return None

        logger.info(f"[Ground truth tests] Generated parameter mapping: {mapping}")
        return mapping
    except Exception as e:
        logger.error(f"[Ground truth tests] Failed to generate parameter mapping: {e}")
        return None

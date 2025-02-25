from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from typing_extensions import Annotated


@dataclass
class LLMInputs:
    """Holds all necessary inputs for code generation."""

    use_case: str
    prompt: ChatPromptTemplate
    search_term_llm: BaseChatModel
    code_generation_llm: BaseChatModel


@dataclass
class GenerationTiming:
    """Captures timing metrics for code generation steps."""

    nuget_search_time: float
    code_generation_time: float


@dataclass
class ValidationInputs:
    """Inputs needed for validation of generated code."""

    implementation_code: str
    unit_test_code: str
    nuget_packages: str
    yaml_path: Optional[Path] = None
    search_term_llm: Optional[BaseChatModel] = None


@dataclass
class BuildMetrics:
    """Holds information about the build process."""

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = False
    duration_ms: int = 0
    raw_output: str = ""


@dataclass
class TestResult:
    """Represents the results of a test run."""

    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: int = 0
    error_details: Optional[list[str]] = None
    raw_output: str = ""


@dataclass
class ActionMapInfo:
    """Stores info about the mapping of actions in the code to ground truth."""

    implementation: str
    ground_truth: str
    matches: bool


@dataclass
class ValidationMetrics:
    """Collects all metrics resulting from the validation steps."""

    build_metrics: BuildMetrics
    llm_test_results: Optional[TestResult] = None
    ground_truth_test_results: Optional[TestResult] = None
    odc_generator_output: str = ""
    solution_dir: Optional[Path] = None
    action_map_info: Optional[ActionMapInfo] = None


@dataclass
class ActionMapResult:
    """Encapsulates the result of an action map validation."""

    should_continue: bool
    odc_generator_output: str
    action_map_info: Optional[ActionMapInfo]
    param_mapping: Optional[str]


class GeneratedCode(TypedDict):
    """Generated code for OutSystems external library."""

    prefix: Annotated[str, ..., "Description of the problem and approach"]
    implementation_code: Annotated[
        str,
        ...,
        "Complete C# code for the implementation contained in a namespace. Also include complete Using statements.",
    ]
    unit_test_code: Annotated[
        str,
        ...,
        "Complete C# code for the Xunit test contained in a namespace. Also include complete Using statements.",
    ]
    nuget_packages: Annotated[
        str,
        ...,
        "Comma seperated list of versionless NuGet packages required for the implementation code. And include any native asset packages needed for these packages in runtime (Linux). Return 'None' if there are no packages to install.",
    ]

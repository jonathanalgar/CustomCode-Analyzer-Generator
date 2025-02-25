import logging
import subprocess
import time
from pathlib import Path
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel

from agents.utils.models import ActionMapInfo
from agents.validation.constants import ODC_TEST_GENERATOR_EXE, TARGET_FRAMEWORK
from agents.validation.custom_exceptions import (
    PackageInstallationError,
    ProjectSetupError,
)

from . import action_map, utils

logger = logging.getLogger(__name__)


def create_and_setup_projects(
    class_dir: Path,
    class_name: str,
    implementation_code: str,
    unit_test_code: str,
    nuget_packages: str,
    search_term_llm: Optional[BaseChatModel],
    yaml_path: Optional[Path] = None,
) -> tuple[str, Optional[ActionMapInfo]]:
    """Creates the implementation/test projects and sets them up."""
    odc_raw_output = ""
    action_map_info = None

    implementation_project_dir = _create_implementation_project(
        class_dir=class_dir,
        class_name=class_name,
        implementation_code=implementation_code,
    )

    _install_optional_packages(nuget_packages, implementation_project_dir)

    llm_test_dir = _create_llm_test_project(
        class_dir=class_dir,
        class_name=class_name,
        implementation_project_dir=implementation_project_dir,
        unit_test_code=unit_test_code,
    )

    if yaml_path:
        odc_raw_output, action_map_info = _create_ground_truth_tests(
            class_dir=class_dir,
            class_name=class_name,
            implementation_project_dir=implementation_project_dir,
            search_term_llm=search_term_llm,
            yaml_path=yaml_path,
        )

    _create_solution_and_add_projects(
        class_dir=class_dir,
        class_name=class_name,
        implementation_project_dir=implementation_project_dir,
        llm_test_dir=llm_test_dir,
        yaml_path=yaml_path,
    )

    return odc_raw_output, action_map_info


def _create_implementation_project(
    class_dir: Path,
    class_name: str,
    implementation_code: str,
) -> Path:
    """Creates the C# classlib project for the generated implementation."""
    implementation_project_dir = class_dir / class_name
    implementation_project_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"[LLM generated implementation] Creating project '{class_name}' in {implementation_project_dir}...")

    try:
        subprocess.run(
            ["dotnet", "new", "classlib", "--framework", TARGET_FRAMEWORK, "--no-restore"],
            cwd=implementation_project_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        logger.warning(f"[LLM generated implementation] First attempt failed with: {str(e)}")
        time.sleep(2)
        try:
            subprocess.run(
                ["dotnet", "new", "classlib", "--framework", TARGET_FRAMEWORK, "--no-restore"],
                cwd=implementation_project_dir,
                capture_output=True,
                text=True,
                check=True,
                timeout=40,
            )
        except Exception as e2:
            error_output = getattr(e2, "stderr", str(e2))
            raise ProjectSetupError("Failed to create implementation project", error_output)

    # Write implementation code
    try:
        default_file = implementation_project_dir / "Class1.cs"
        if default_file.exists():
            default_file.unlink()
        code_path = implementation_project_dir / f"{class_name}.cs"
        code_path.write_text(implementation_code)
        logger.info(f"[LLM generated implementation] Wrote code to {code_path}")
    except Exception as e:
        raise ProjectSetupError(f"Failed to write implementation code: {str(e)}")

    # Install required packages
    try:
        for pkg in ["OutSystems.ExternalLibraries.SDK", "CustomCode.Analyzer"]:
            _install_package(pkg, implementation_project_dir, "LLM generated implementation", allow_failure=False)
    except PackageInstallationError as e:
        raise ProjectSetupError(f"Failed to install required package: {e.package}", e.error_output)

    return implementation_project_dir


def _install_optional_packages(nuget_packages: str, implementation_project_dir: Path) -> None:
    """Installs additional NuGet packages declared by the LLM, if any."""
    if nuget_packages and nuget_packages.lower() != "none":
        packages = [pkg.strip() for pkg in nuget_packages.split(",")]
        packages = [pkg for pkg in packages if pkg and pkg.lower() != "none" and pkg.lower() != "moq"]
        failed_packages = []

        for package in packages:
            success = _install_package(
                package, implementation_project_dir, "LLM generated implementation", allow_failure=True
            )
            if not success:
                failed_packages.append(package)

        if failed_packages:
            logger.warning(
                f"[LLM generated implementation] Some optional packages failed to install: {', '.join(failed_packages)}"
            )


def _create_llm_test_project(
    class_dir: Path, class_name: str, implementation_project_dir: Path, unit_test_code: str
) -> Path:
    """Creates an XUnit test project for the LLM-generated tests."""
    llm_test_dir = class_dir / "LLMGeneratedTests"
    llm_test_dir.mkdir(exist_ok=True)

    logger.info("[LLM generated tests] Creating project...")
    try:
        subprocess.run(
            ["dotnet", "new", "xunit", "--framework", TARGET_FRAMEWORK, "--no-restore"],
            cwd=llm_test_dir,
            capture_output=True,
            text=True,
            check=True,
        )

        # Remove default test files
        for df in [llm_test_dir / "UnitTest1.cs", llm_test_dir / "GlobalUsings.cs"]:
            if df.exists():
                df.unlink()

        # Install essential packages for XUnit and mocking
        for pkg in ["xunit", "xunit.runner.visualstudio", "Microsoft.NET.Test.Sdk", "Moq"]:
            _install_package(pkg, llm_test_dir, "LLM generated tests", allow_failure=False)

        # Add reference to the implementation project
        subprocess.run(
            ["dotnet", "add", "reference", str(implementation_project_dir / f"{class_name}.csproj")],
            cwd=llm_test_dir,
            capture_output=True,
            text=True,
            check=True,
        )

        llm_test_path = llm_test_dir / f"{class_name}Tests.cs"
        llm_test_path.write_text(unit_test_code)
        logger.info(f"[LLM generated tests] Wrote code to {llm_test_path}")
    except Exception as e:
        error_output = getattr(e, "stderr", str(e))
        raise ProjectSetupError("Failed to setup LLM test project", error_output)

    return llm_test_dir


def _create_ground_truth_tests(
    class_dir: Path,
    class_name: str,
    implementation_project_dir: Path,
    search_term_llm: Optional[BaseChatModel],
    yaml_path: Path,
) -> tuple[str, Optional[ActionMapInfo]]:
    """Generate ground truth tests using CCAGTestGenerator and create XUnit test project."""
    odc_raw_output = ""
    action_map_info = None

    gt_test_dir = class_dir / "GroundTruthTests"
    gt_test_dir.mkdir(exist_ok=True)

    logger.info("[Ground truth tests] Creating project...")
    try:
        subprocess.run(
            ["dotnet", "new", "xunit", "--framework", TARGET_FRAMEWORK],
            cwd=gt_test_dir,
            capture_output=True,
            text=True,
            check=True,
        )

        for df in [gt_test_dir / "UnitTest1.cs", gt_test_dir / "GlobalUsings.cs"]:
            if df.exists():
                df.unlink()

        for pkg in [
            "xunit",
            "xunit.runner.visualstudio",
            "Microsoft.NET.Test.Sdk",
        ]:
            _install_package(pkg, gt_test_dir, "Ground truth tests", allow_failure=False)

        subprocess.run(
            ["dotnet", "add", "reference", str(implementation_project_dir / f"{class_name}.csproj")],
            cwd=gt_test_dir,
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception as e:
        error_output = getattr(e, "stderr", str(e))
        raise ProjectSetupError("Failed to setup ground truth tests", error_output)

    if search_term_llm is None:
        logger.warning("search_term_llm is None; skipping action map validation.")
        odc_raw_output = ""
        action_map_info = None
    else:
        # Validate the action map before generating ground truth tests
        result = action_map.validate_action_map(
            implementation_project_dir=implementation_project_dir,
            class_name=class_name,
            yaml_path=yaml_path,
            search_term_llm=search_term_llm,
        )
        odc_raw_output = result.odc_generator_output
        action_map_info = result.action_map_info

    if not result.should_continue:
        return odc_raw_output, action_map_info

    # Generate test code using CCAGTestGenerator
    code_path = implementation_project_dir / f"{class_name}.cs"
    cmd = [
        str(ODC_TEST_GENERATOR_EXE),
        str(code_path),
        str(yaml_path),
    ]
    if result.param_mapping:
        cmd.extend(["--paramMap", result.param_mapping])

    logger.info("[Ground truth tests] Running CCAGTestGenerator...")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(gt_test_dir),
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        odc_raw_output = proc.stdout + "\n" + proc.stderr
        logger.info("[Ground truth tests] CCAGTestGenerator output:\n" + proc.stdout)

        generated_test_path = gt_test_dir / f"{class_name}Tests.cs"
        if generated_test_path.exists():
            logger.info("[Ground truth tests] Generated code:\n" + generated_test_path.read_text())
    except Exception as e:
        odc_raw_output = getattr(e, "stdout", "") + "\n" + getattr(e, "stderr", str(e))
        logger.error(f"[Ground truth tests] CCAGTestGenerator failed: {odc_raw_output}")

    return odc_raw_output, action_map_info


def _create_solution_and_add_projects(
    class_dir: Path,
    class_name: str,
    implementation_project_dir: Path,
    llm_test_dir: Path,
    yaml_path: Optional[Path],
) -> None:
    """Creates a solution file, adds both implementation and test projects."""
    try:
        logger.info("Creating overall solution...")
        subprocess.run(["dotnet", "new", "sln"], cwd=class_dir, capture_output=True, text=True, check=True)

        projects_to_add = [
            (implementation_project_dir / f"{class_name}.csproj", f"{class_name}.csproj"),
            (llm_test_dir / "LLMGeneratedTests.csproj", "LLMGeneratedTests.csproj"),
        ]

        gt_dir = class_dir / "GroundTruthTests"
        if yaml_path and gt_dir.exists():
            projects_to_add.append((gt_dir / "GroundTruthTests.csproj", "GroundTruthTests.csproj"))

        for prj, prj_name in projects_to_add:
            try:
                subprocess.run(
                    ["dotnet", "sln", "add", str(prj)],
                    cwd=class_dir,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                logger.info(f"Added {prj_name} to the solution")
            except Exception as e:
                logger.error(f"Failed to add {prj_name}: {getattr(e, 'stderr', str(e))}")

        logger.info("Final solution structure:")
        utils.display_directory_structure(class_dir)

    except Exception as e:
        error_output = getattr(e, "stderr", str(e))
        raise ProjectSetupError("Failed to create solution", error_output)


def _install_package(package: str, project_dir: Path, project_name: str, *, allow_failure: bool = False) -> bool:
    """Installs a single NuGet package to the specified project."""
    try:
        subprocess.run(
            ["dotnet", "add", "package", package],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info(f"[{project_name}] Installed package: {package}")
        return True
    except subprocess.CalledProcessError as e:
        msg = f"[{project_name}] Failed to install {package}:\n{e.stderr.strip()}"
        if allow_failure:
            logger.warning(msg)
            return False
        raise PackageInstallationError(package, e.stderr)

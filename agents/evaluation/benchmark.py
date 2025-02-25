import logging
import platform
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

import pandas as pd
import psutil
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from agents.generation.llm_generation import (
    GenerationTiming,
    LLMInputs,
    generate_code,
    run_reflection_pass,
)
from agents.generation.prompts import PROMPTS
from agents.utils.postvalidation import get_token_stats
from agents.validation.workflow import (
    ValidationInputs,
    ValidationMetrics,
    validate_generated_code,
)

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResults:
    """Represents the aggregated benchmark results."""

    df: pd.DataFrame
    search_term_llm: str
    code_generation_llm: str
    prompt: str
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Initializes timestamp if not set."""
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def _repr_html_(self) -> str:
        """HTML representation for notebooks."""
        header_html = f"""
        <div style="display: inline-block; border: 1px solid #ccc; padding: 5px 10px; margin-bottom: 10px;">
            <strong>search_term_llm=</strong><code>{self.search_term_llm}</code><br>
            <strong>code_generation_llm=</strong><code>{self.code_generation_llm}</code><br>
            <strong>prompt=</strong><code>{self.prompt}</code><br>
            <strong>run_timestamp=</strong><code>{self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else 'N/A'}</code>
        </div>
        """
        return header_html + self.df.to_html(escape=False)

    def save(self, base_path: str | Path) -> Path:
        """Saves benchmark results as Parquet."""
        base_path = Path(base_path)
        timestamp_str = self.timestamp.strftime("%Y%m%d_%H%M%S") if self.timestamp else "N/A"

        filename = f"{base_path.stem}_{timestamp_str}.parquet"
        final_path = base_path.parent / filename

        table = pa.Table.from_pandas(self.df)
        metadata = {
            "search_term_llm": self.search_term_llm,
            "code_generation_llm": self.code_generation_llm,
            "prompt": self.prompt,
            "timestamp": self.timestamp.isoformat() if self.timestamp else "N/A",
        }
        table = table.replace_schema_metadata(
            {**table.schema.metadata, **{k.encode(): str(v).encode() for k, v in metadata.items()}}
        )
        pq.write_table(table, final_path)

        return final_path

    @classmethod
    def load(cls, path: str | Path) -> "BenchmarkResults":
        """Loads benchmark results from a Parquet file."""
        table = pq.read_table(path)
        metadata = {k.decode(): v.decode() for k, v in table.schema.metadata.items()}

        return cls(
            df=table.to_pandas(),
            search_term_llm=metadata["search_term_llm"],
            code_generation_llm=metadata["code_generation_llm"],
            prompt=metadata["prompt"],
            timestamp=datetime.fromisoformat(metadata["timestamp"]),
        )


def display_comprehensive_results(
    llm_generation_inputs: LLMInputs,
    llm_generation_metrics: GenerationTiming,
    validation_inputs: ValidationInputs,
    validation_metrics: ValidationMetrics,
    prompt: ChatPromptTemplate,
    output_file: Optional[Path] = None,
    debug: bool = False,
) -> str:
    """Displays or writes detailed benchmark and validation results."""
    output = []

    def add_section(title: str, content: str) -> None:
        output.extend(["\n" + "=" * 40, title, "=" * 40 + "\n", content])

    sys_info = platform.uname()
    sys_content = [
        f"System:       {sys_info.system} ({sys_info.release})",
        f"Processor:    {sys_info.processor}",
        f"CPU Cores:    {psutil.cpu_count(logical=False)} physical, {psutil.cpu_count(logical=True)} total",
    ]

    mem = psutil.virtual_memory()
    sys_content.extend(
        [
            f"Total RAM:    {mem.total / (1024**3):.2f} GB",
            f"Available:    {mem.available / (1024**3):.2f} GB",
            f"RAM Usage:    {mem.percent:.2f}%",
        ]
    )
    add_section("System information", "\n".join(sys_content))

    input_content = [
        f"Test case:\n{llm_generation_inputs.use_case}\n",
        f"Search term LLM:\n{llm_generation_inputs.search_term_llm}\n",
        f"Code generation LLM:\n{llm_generation_inputs.code_generation_llm}\n",
    ]
    add_section("Benchmark input", "\n".join(input_content))

    latency_content = [
        f"NuGet search time: {llm_generation_metrics.nuget_search_time:.2f}s",
        f"Code generation time: {llm_generation_metrics.code_generation_time:.2f}s",
        f"Total generation time: "
        f"{(llm_generation_metrics.nuget_search_time + llm_generation_metrics.code_generation_time):.2f}s",
    ]
    add_section("Code generation latency", "\n".join(latency_content))

    validation_content = [
        f"Ground truth YAML: {validation_inputs.yaml_path}",
        f"Unit test code length: {len(validation_inputs.unit_test_code)} chars",
        f"Implementation code length: {len(validation_inputs.implementation_code)} chars",
    ]
    add_section("Validation inputs: summary", "\n".join(validation_content))

    results_content = []

    bm = validation_metrics.build_metrics
    results_content.extend(
        [
            "Build metrics:",
            f"  Build success:    {bm.success}",
            f"  Build duration:   {bm.duration_ms} ms",
            f"  # of Warnings:    {len(bm.warnings)}",
            f"  # of Errors:      {len(bm.errors)}",
        ]
    )

    for i, warn in enumerate(bm.warnings[:3], 1):
        results_content.append(f"     [Warning {i}] {warn}")
    for i, err in enumerate(bm.errors[:3], 1):
        results_content.append(f"     [Error {i}] {err}")

    results_content.append("\nLLM generated tests run:")
    llm_res = validation_metrics.llm_test_results
    if llm_res:
        results_content.extend(
            [
                f"  Passed:   {llm_res.passed}",
                f"  Failed:   {llm_res.failed}",
                f"  Skipped:  {llm_res.skipped}",
                f"  Duration: {llm_res.duration_ms} ms",
            ]
        )
        if llm_res.error_details:
            for detail in llm_res.error_details:
                results_content.append(f"    [ERROR] {detail}")
    else:
        results_content.append("  No LLM test results (build may have failed or was skipped).")

    results_content.append("\nGround truth tests run:")
    gt_res = validation_metrics.ground_truth_test_results
    if gt_res:
        results_content.extend(
            [
                f"  Passed:   {gt_res.passed}",
                f"  Failed:   {gt_res.failed}",
                f"  Skipped:  {gt_res.skipped}",
                f"  Duration: {gt_res.duration_ms} ms",
            ]
        )
        if gt_res.error_details:
            for detail in gt_res.error_details:
                results_content.append(f"    [ERROR] {detail}")
    else:
        results_content.append("  No Ground Truth test results (build may have failed or was skipped).")

    results_content.append("\nAction map [# Actions(# Parameters)]:")
    if validation_metrics.action_map_info:
        results_content.extend(
            [
                f"  Ground truth    : {validation_metrics.action_map_info.ground_truth}",
                f"  Implementation  : {validation_metrics.action_map_info.implementation}",
                f"  Match?          :      {'✓' if validation_metrics.action_map_info.matches else '✗'}",
            ]
        )

    add_section("Validation results: summary", "\n".join(results_content))

    if debug:
        debug_content = []
        if validation_metrics.odc_generator_output:
            debug_content.extend(
                ["CCAGTestGenerator output:\n" + validation_metrics.odc_generator_output, "\n" + "*" * 40]
            )

        if bm.raw_output:
            debug_content.extend(["Build output:\n" + bm.raw_output, "\n" + "*" * 40])

        if llm_res and llm_res.raw_output:
            debug_content.extend(["LLM generated tests run output:\n" + llm_res.raw_output, "\n" + "*" * 40])

        if gt_res and gt_res.raw_output:
            debug_content.extend(["Ground truth tests run output:\n" + gt_res.raw_output, "\n" + "*" * 40])

        debug_content.append("Full prompt:\n" + str(prompt))
        add_section("Debug output", "\n".join(debug_content))

    full_output = "\n".join(output)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_output)
    else:
        print(full_output)

    return full_output


def run_benchmark(
    test_cases: list[Path],
    prompt_key: str,
    search_term_llm: "BaseChatModel",
    code_generation_llm: "BaseChatModel",
) -> BenchmarkResults:
    """Runs the benchmark for each test case and returns aggregated results."""
    results = []

    run_id = str(uuid4())[:5]
    output_dir = Path("/app/output")
    run_dir = output_dir / f"run_{run_id}"

    logger.info(f"Creating run directory: {run_dir}")
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Directory created successfully")
    except Exception as e:
        logger.error(f"Error creating directory: {e}")
        raise

    def get_model_identifier(llm: "BaseChatModel") -> str:
        model_name = getattr(llm, "model_name", None)
        if model_name is not None:
            return model_name

        model = getattr(llm, "model", None)
        if model is not None:
            return model

        return "unknown"

    search_model = get_model_identifier(search_term_llm)
    search_value = getattr(search_term_llm, "reasoning_effort", None)
    search_param_name = "reasoning_effort"
    if search_value is None:
        search_value = getattr(search_term_llm, "temperature", 0.0)
        search_param_name = "temperature"

    code_model = get_model_identifier(code_generation_llm)
    code_value = getattr(code_generation_llm, "reasoning_effort", None)
    code_param_name = "reasoning_effort"
    if code_value is None:
        code_value = getattr(code_generation_llm, "temperature", 0.0)
        code_param_name = "temperature"

    logger.info("Starting benchmark run...")
    logger.info("=" * 60)
    logger.info(f"Search term LLM:      {search_model} ({search_param_name}={search_value})")
    logger.info(f"Code generation LLM:  {code_model} ({code_param_name}={code_value})")
    logger.info(f"System prompt:        {prompt_key}")
    logger.info(f"Number of test cases: {len(test_cases)}")
    logger.info("-" * 60)

    logger.info("Test cases:")
    for i, yaml_path in enumerate(test_cases, 1):
        with open(yaml_path, "r") as f:
            yaml_content = yaml.safe_load(f)
            use_case = yaml_content["description"]
        logger.info(f"{i}. {use_case} -> {yaml_path}")
    logger.info("=" * 60 + "\n")

    for case_num, yaml_path in enumerate(test_cases, 1):
        with open(yaml_path, "r") as f:
            yaml_content = yaml.safe_load(f)
            use_case = yaml_content["description"]

        base_prompt = PROMPTS[prompt_key]

        logger.info(f"Running test case ({case_num}/{len(test_cases)}): '{use_case}'...")
        llm_inputs = LLMInputs(
            use_case=use_case,
            prompt=deepcopy(base_prompt),
            search_term_llm=search_term_llm,
            code_generation_llm=code_generation_llm,
        )

        generated_code, generation_metrics, code_gen_prompt_with_first_result, project_id = generate_code(
            llm_inputs, stream=False
        )

        validation_inputs = ValidationInputs(
            implementation_code=generated_code["implementation_code"],
            unit_test_code=generated_code["unit_test_code"],
            nuget_packages=generated_code["nuget_packages"],
            yaml_path=yaml_path,
            search_term_llm=search_term_llm,
        )

        validation_metrics = validate_generated_code(
            validation_inputs=validation_inputs, search_term_llm=search_term_llm
        )

        base_name = Path(yaml_path).stem
        out_file = run_dir / f"{base_name}.output"
        logger.info(f"Saving detailed output to '{out_file}'...")

        display_comprehensive_results(
            llm_generation_inputs=llm_inputs,
            llm_generation_metrics=generation_metrics,
            validation_inputs=validation_inputs,
            validation_metrics=validation_metrics,
            prompt=code_gen_prompt_with_first_result,
            output_file=out_file,
            debug=True,
        )
        results.append(
            _make_results_row(
                use_case=use_case,
                generation_timing=generation_metrics,
                validation_metrics=validation_metrics,
                log_file=str(out_file),
                run_type="initial",
                project_id=project_id,
            )
        )

        reflection_result = run_reflection_pass(
            llm_inputs=llm_inputs,
            validation_metrics=validation_metrics,
            code_gen_prompt_with_first_result=code_gen_prompt_with_first_result,
            stream=False,
        )

        if reflection_result:
            reflection_code, reflection_timing, reflection_prompt = reflection_result
            reflection_validation_inputs = ValidationInputs(
                implementation_code=reflection_code["implementation_code"],
                unit_test_code=reflection_code["unit_test_code"],
                nuget_packages=reflection_code["nuget_packages"],
                yaml_path=yaml_path,
            )

            reflection_validation_metrics = validate_generated_code(
                validation_inputs=reflection_validation_inputs,
                search_term_llm=search_term_llm,
            )

            out_file_reflection = run_dir / f"{base_name}_reflection.output"

            display_comprehensive_results(
                llm_generation_inputs=llm_inputs,
                llm_generation_metrics=reflection_timing,
                validation_inputs=reflection_validation_inputs,
                validation_metrics=reflection_validation_metrics,
                prompt=reflection_prompt,
                output_file=out_file_reflection,
                debug=True,
            )
            results.append(
                _make_results_row(
                    use_case=use_case,
                    generation_timing=reflection_timing,
                    validation_metrics=reflection_validation_metrics,
                    log_file=str(out_file_reflection),
                    run_type="reflection",
                    project_id=project_id,
                )
            )

        logger.info(f"Completed test case ({case_num}/{len(test_cases)}): '{use_case}'")

    logger.info("All benchmarks completed. Returning DataFrame.")

    df = pd.DataFrame(results)
    df = df.set_index(["Test case", "Run"])

    for col in ["NuGet search latency (s)", "Code generation latency (s)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").round(1)

    benchmark_results = BenchmarkResults(
        df=df,
        search_term_llm=f"{search_model} ({search_param_name}={search_value})",
        code_generation_llm=f"{code_model} ({code_param_name}={code_value})",
        prompt=prompt_key,
    )

    final_path = benchmark_results.save(run_dir / "benchmark")
    logger.info(f"Benchmark results saved to {final_path}")

    return benchmark_results


def _make_results_row(
    use_case: str,
    generation_timing: GenerationTiming,
    validation_metrics: ValidationMetrics,
    log_file: str,
    run_type: str,
    project_id: Optional[str] = None,
) -> dict:
    """Creates a dictionary for each test case result."""
    nuget_s = generation_timing.nuget_search_time
    codegen_s = generation_timing.code_generation_time
    build_ok = validation_metrics.build_metrics.success
    warning_count = len(validation_metrics.build_metrics.warnings)
    error_count = len(validation_metrics.build_metrics.errors)

    if validation_metrics.action_map_info:
        map_info = validation_metrics.action_map_info
        if map_info.matches:
            action_map_status = f"✓ {map_info.implementation}"
        else:
            action_map_status = f"✗ Got: {map_info.implementation}, Expected: {map_info.ground_truth}"
    else:
        action_map_status = "-"

    if build_ok:
        llm_res = validation_metrics.llm_test_results
        gt_res = validation_metrics.ground_truth_test_results

        if llm_res:
            total_llm_tests = llm_res.passed + llm_res.failed
            llm_pass_rate = f"{llm_res.passed}/{total_llm_tests}" if total_llm_tests > 0 else "-"
        else:
            llm_pass_rate = "-"

        if gt_res:
            total_gt_tests = gt_res.passed + gt_res.failed
            gt_pass_rate = f"{gt_res.passed}/{total_gt_tests}" if total_gt_tests > 0 else "-"
        else:
            gt_pass_rate = "-"
    else:
        llm_pass_rate = "-"
        gt_pass_rate = "-"

    row = {
        "Test case": use_case,
        "Run": run_type,
        "NuGet search latency (s)": nuget_s,
        "Code generation latency (s)": codegen_s,
        "Action map match?": action_map_status,
        "Build success?": "✓" if build_ok else "✗",
        "# Build WARNING": warning_count,
        "# Build ERROR": error_count,
        "LLM test pass rate": llm_pass_rate,
        "Ground truth test pass rate": gt_pass_rate,
        "Log file": str(log_file).replace("/app/output/", ""),
    }

    if project_id:
        _, _, url = get_token_stats(project_id)
        row["LangSmith URL"] = f'<a href="{url}" target="_blank">traces</a>'
    else:
        row["LangSmith URL"] = "-"

    return row

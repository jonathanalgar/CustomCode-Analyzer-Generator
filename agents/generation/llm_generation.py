import logging
import os
import re
import time
from typing import Optional, Union, cast

import requests
from haikunator import Haikunator
from langchain.chains.base import RunnableSerializable
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langsmith import Client

from agents.utils.models import GeneratedCode, GenerationTiming, LLMInputs
from agents.validation.workflow import ValidationMetrics

logger = logging.getLogger(__name__)

ENABLE_TRACING = (os.getenv("LANGCHAIN_TRACING_V2") == "true") and bool(os.getenv("LANGCHAIN_API_KEY"))


def generate_code(
    llm_inputs: LLMInputs, stream: bool = False
) -> tuple[GeneratedCode, GenerationTiming, ChatPromptTemplate, str | None]:
    """Generates code using the LLM based on the provided use case."""
    use_case = llm_inputs.use_case
    code_gen_prompt = llm_inputs.prompt
    search_term_llm = llm_inputs.search_term_llm
    code_generation_llm = llm_inputs.code_generation_llm
    project_id = None

    if ENABLE_TRACING:
        client = Client()
        haikunator = Haikunator()
        project_name = haikunator.haikunate()
        project = client.create_project(
            project_name=project_name,
            description="Project created by CustomCode-Analyzer-Generator",
        )
        os.environ["LANGCHAIN_PROJECT"] = project_name
        project_id = str(project.id)

    logger.info("Searching NuGet packages...")
    nuget_packages_info, nuget_search_time = _get_nuget_info(use_case, search_term_llm)

    framing_context = (
        f"Use case: {use_case}\n"
        + "Some NuGet packages that may or may not be useful for the implementation code:\n"
        + f"{nuget_packages_info}"
    )

    code_gen_prompt.append(("user", framing_context))

    code_gen_chain = code_gen_prompt | code_generation_llm.with_structured_output(GeneratedCode, strict=True)

    logger.info("Starting code generation...")
    start_time = time.time()

    try:
        result = _run_chain_with_optional_streaming(chain=code_gen_chain, stream=stream)
    except Exception as e:
        logger.error(f"Critical error during code generation: {str(e)}")
        raise

    code_generation_time = time.time() - start_time
    timing = GenerationTiming(
        nuget_search_time=nuget_search_time,
        code_generation_time=code_generation_time,
    )

    logger.info("Code generation completed")

    dict_str = str(result)
    dict_escaped = dict_str.replace("{", "{{").replace("}", "}}")
    code_gen_prompt.append(("ai", dict_escaped))

    return result, timing, code_gen_prompt, project_id


def generate_code_from_prompt(
    code_gen_prompt_with_first_result: ChatPromptTemplate,
    code_generation_llm: BaseChatModel,
    stream: bool = False,
) -> tuple[GeneratedCode, GenerationTiming, ChatPromptTemplate]:
    """Generates code using an existing prompt."""
    logger.info("Starting code generation (reflection pass)...")
    start_time = time.time()

    reflection_chain = code_gen_prompt_with_first_result | code_generation_llm.with_structured_output(
        GeneratedCode, strict=True
    )

    try:
        result = _run_chain_with_optional_streaming(chain=reflection_chain, stream=stream)
    except Exception as e:
        logger.error(f"Critical error during code generation: {str(e)}")
        raise

    logger.info("Code generation completed (reflection pass)")

    code_generation_time = time.time() - start_time

    # Store the reflection pass response in the prompt
    dict_str = str(result)
    dict_escaped = dict_str.replace("{", "{{").replace("}", "}}")
    code_gen_prompt_with_first_result.append(("ai", dict_escaped))

    timing = GenerationTiming(
        nuget_search_time=0.0,
        code_generation_time=code_generation_time,
    )
    return result, timing, code_gen_prompt_with_first_result


def run_reflection_pass(
    llm_inputs: LLMInputs,
    validation_metrics: ValidationMetrics,
    code_gen_prompt_with_first_result: ChatPromptTemplate,
    stream: bool = False,
) -> Optional[tuple[GeneratedCode, GenerationTiming, ChatPromptTemplate]]:
    """Performs a second code generation pass if validation fails."""
    if not validation_metrics.build_metrics.success:
        reflection_prompt = (
            "Your solution failed to build:\n\n"
            f"{validation_metrics.build_metrics.raw_output}"
            "- reflect on this and your prior attempt to solve the problem."
            "(1) State what you think went wrong with the prior solution and "
            "(2) try to solve this problem again. Return the FULL SOLUTION "
            "complete with prefix, implementation and single XUnit unit test."
        )
    elif validation_metrics.llm_test_results and validation_metrics.llm_test_results.failed > 0:
        reflection_prompt = (
            "Your solution failed the generated unit test:\n\n"
            f"{validation_metrics.llm_test_results.raw_output}\n\n"
            "- reflect on this and your prior attempt to solve the problem. "
            "(1) State what you think went wrong with the prior solution and "
            "(2) try to solve this problem again. The issue could be with the "
            "implementation code or the unit test itself. Return the FULL SOLUTION "
            "complete with prefix, implementation and single XUnit unit test."
        )
    else:
        return None

    reflection_prompt = reflection_prompt.replace("{", "{{").replace("}", "}}")
    code_gen_prompt_with_first_result.append(("human", reflection_prompt))

    reflection_result = generate_code_from_prompt(
        code_gen_prompt_with_first_result, llm_inputs.code_generation_llm, stream=stream
    )

    return reflection_result


def _fetch_github_readme(project_url: str) -> str:
    """Attempts to fetch README content if URL is from GitHub."""
    if "github.com" not in project_url.lower():
        return ""

    parts = project_url.rstrip("/").split("/")
    if len(parts) < 5:
        return ""

    owner, repo = parts[-2], parts[-1]

    for branch in ["master", "main"]:
        for readme_name in ["README.md", "readme.md"]:
            try:
                readme_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{readme_name}"
                response = requests.get(readme_url, timeout=5)
                if response.status_code == 200:
                    return response.text
            except Exception as e:
                logger.debug(f"Failed to fetch README: {e}")
    return ""


def _search_nuget_packages(search_terms: str, take: int = 3, include_readme: bool = False) -> str:
    """Calls NuGet search API to get top package info."""
    base_url = "https://azuresearch-usnc.nuget.org/query"
    params: dict[str, Union[str, int]] = {
        "q": search_terms,
        "take": take,
        "prerelease": "false",
        "semVerLevel": "2.0.0",
    }

    response = requests.get(base_url, params=params)
    logger.debug(f"NuGet Search API response status code: {response.status_code}")

    if response.status_code == 200:
        packages = response.json().get("data", [])
        package_infos = []

        for pkg in packages:
            package_info = (
                f"\n* Package: {pkg['id']} (v{pkg['version']})"
                f"\n  Description: {pkg.get('description', 'No description')}"
            )

            if include_readme:
                readme_content = _fetch_github_readme(pkg.get("projectUrl", ""))
                if readme_content:
                    package_info += f"\n  README:\n{readme_content}\n"

            package_infos.append(package_info)

        return "\n".join(package_infos)
    return ""


def _generate_nuget_search_term(use_case: str, search_term_llm: BaseChatModel) -> str:
    """Uses LLM to create a concise NuGet search term from the use case."""
    messages = [
        SystemMessage(
            content="Extract the most relevant search term for the NuGet search API from the use case. Return only the search term."
        ),
        HumanMessage(content="Use case: " + use_case),
    ]
    search_term_response = search_term_llm.invoke(messages)
    return re.sub(r"[^a-zA-Z0-9\s]", "", str(search_term_response.content))


def _get_nuget_info(use_case: str, search_term_llm: BaseChatModel) -> tuple[str, float]:
    """Get NuGet package information and measure the time taken."""
    start_time = time.time()

    try:
        search_term = _generate_nuget_search_term(use_case, search_term_llm)
        logger.debug(f"LLM generated NuGet search term: {search_term}")
        nuget_packages_info = _search_nuget_packages(search_term).replace("{", "{{").replace("}", "}}")
    except Exception as e:
        logger.warning(
            f"Problem during NuGet search process: {str(e)}. "
            "Won't be able to provide the LLM code generation with relevant NuGet information."
        )
        nuget_packages_info = ""

    elapsed_time = time.time() - start_time
    return nuget_packages_info, elapsed_time


def _run_chain_with_optional_streaming(
    chain: RunnableSerializable,
    stream: bool,
) -> GeneratedCode:
    """Runs a chain with or without token-level streaming."""
    HEADERS = {
        "prefix": "> Thinking about my approach...",
        "implementation_code": "> Writing the implementation code...",
        "unit_test_code": "> Writing the unit test...",
    }

    previous_text = {k: "" for k in HEADERS}
    printed_header = {k: False for k in HEADERS}
    final_result = None

    def _print_output(result: dict) -> None:
        first = True
        for field, header_txt in HEADERS.items():
            if field in result and result[field]:
                if first:
                    print()
                    first = False
                else:
                    print("\n")
                print(header_txt)
                print(result[field], end="")

    def _print_stream_chunk(chunk: dict) -> None:
        for field, header_txt in HEADERS.items():
            if field in chunk and chunk[field] != previous_text[field]:
                if not printed_header[field] and chunk[field]:
                    if any(printed_header.values()):
                        print("\n")
                    else:
                        print()
                    print(header_txt)
                    printed_header[field] = True

                old = previous_text[field]
                new_field_text = chunk[field]
                delta = new_field_text[len(old) :]
                if delta:
                    print(delta, end="", flush=True)
                previous_text[field] = new_field_text

    if stream:
        for chunk in chain.stream({}):
            _print_stream_chunk(chunk)
            final_result = chunk
    else:
        final_result = chain.invoke({})
        _print_output(final_result)

    if final_result is None:
        raise ValueError("Chain did not produce any output.")

    return cast(GeneratedCode, final_result)

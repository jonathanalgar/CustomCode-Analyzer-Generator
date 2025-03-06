#!/usr/bin/env python3

import logging
import os
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel

from agents.generate_and_validate import generate_and_validate
from agents.utils.logger_config import setup_logger
from agents.utils.model_definitions import (
    get_available_models,
    load_api_keys,
    select_model,
)

setup_logger(level=logging.INFO)


def get_user_input() -> str:
    """Prompts user for a functionality description."""
    banner = """\
                _______________________________________________
             _-'    .-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.  --- `-_
          _-'.-.-. .---.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.--.  .-.-.`-_
       _-'.-.-.-. .---.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-`__`. .-.-.-.`-_
    _-'.-.-.-.-. .-----.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-.-----. .-.-.-.-.`-_
 _-'.-.-.-.-.-. .---.-. .-----------------------------. .-.---. .---.-.-.-.`-_
:-----------------------------------------------------------------------------:
`---._.--- CustomCode-Analyzer-Generator, an experimental project -ja---._.---'"""

    print(banner)
    print("\n\nPlease describe what functionality you want the ODC External Library to provide.")
    print("Example: 'take a string and return the sha1 hash'")
    print("\nEnter the functionality:")

    while True:
        use_case = input("> ").strip()
        if not use_case:
            print("Please enter a non-empty description.")
            continue

        if len(use_case) < 10:
            print("Description must be at least 10 characters long.")
            continue

        return use_case


def _get_model_from_env_or_prompt(available_models: dict, model_type: str, env_var_name: str) -> BaseChatModel:
    """Get model from environment variable or prompt the user to select one."""
    env_model_name = os.getenv(env_var_name)
    if env_model_name and env_model_name.strip():
        for _, models in available_models.items():
            if env_model_name in models:
                print(f"Using {env_model_name} for {model_type} (from environment variable)")
                return models[env_model_name]
        print(f"Warning: Model '{env_model_name}' specified in {env_var_name} not found. Prompting for selection.")
    return select_model(available_models, model_type, env_var_name)


def main() -> None:
    """Main entry point for generating and validating an external library."""
    api_keys = load_api_keys()
    if not api_keys["openai"]:
        raise EnvironmentError("No OpenAI API key found in .env file. Please add OPENAI_API_KEY")

    available_models = get_available_models(api_keys)

    use_case = get_user_input()

    print("\nNow let's select which LLMs to use to generate the library..")
    search_term_llm = _get_model_from_env_or_prompt(available_models, "NuGet package search", "SEARCH_TERM_LLM")

    code_generation_llm = _get_model_from_env_or_prompt(available_models, "code generation", "CODE_GENERATION_LLM")
    print("\n")
    generate_and_validate(
        use_case=use_case,
        prompt_key="ONE_SHOT",
        search_term_llm=search_term_llm,
        code_generation_llm=code_generation_llm,
        output_dir=Path("output"),
        stream=True,
    )


if __name__ == "__main__":
    main()

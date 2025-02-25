import os
from typing import Any, Dict, List, Optional, Tuple

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

_DEFAULT_TEMPERATURE = 0

_OPENAI_MODELS: Dict[str, ChatOpenAI] = {
    "gpt4o": ChatOpenAI(model="gpt-4o", temperature=_DEFAULT_TEMPERATURE),
    "gpt4o-mini": ChatOpenAI(model="gpt-4o-mini", temperature=_DEFAULT_TEMPERATURE),
    "o3-mini-medium": ChatOpenAI(model="o3-mini", reasoning_effort="medium"),
    "o3-mini-high": ChatOpenAI(model="o3-mini", reasoning_effort="high"),
    "o1-high": ChatOpenAI(model="o1", reasoning_effort="high"),
}

_ANTHROPIC_MODELS: Dict[str, ChatAnthropic] = {
    "claude-3-5-sonnet": ChatAnthropic(model_name="claude-3-5-sonnet-20241022")  # type: ignore
}


def load_api_keys() -> Dict[str, Optional[str]]:
    """Loads API keys from the environment (or .env) into a dictionary."""
    return {"openai": os.getenv("OPENAI_API_KEY"), "anthropic": os.getenv("ANTHROPIC_API_KEY")}


def get_available_models(api_keys: Dict[str, Optional[str]]) -> Dict[str, Dict[str, Any]]:
    """Returns available models grouped by provider."""
    available: Dict[str, Dict[str, Any]] = {}
    if api_keys.get("openai"):
        available["openai"] = _OPENAI_MODELS
    if api_keys.get("anthropic"):
        available["anthropic"] = _ANTHROPIC_MODELS
    return available


def get_model(model_name: str) -> BaseChatModel:
    """Retrieve a model instance based on the provided model name."""
    if model_name in _OPENAI_MODELS:
        return _OPENAI_MODELS[model_name]
    elif model_name in _ANTHROPIC_MODELS:
        return _ANTHROPIC_MODELS[model_name]
    else:
        raise KeyError(f"Model {model_name} not found in any provider.")


def select_model(available_models: Dict[str, Dict[str, Any]], purpose: str) -> Any:
    """Prompts the user to select a model from the available models based on the given purpose."""
    print(f"\nSelect model for {purpose}:")
    options = _get_model_options(available_models, purpose)
    default_option = options[0]

    for idx, (name, _) in enumerate(options, start=1):
        if idx == 1:
            print(f"{idx}. {name} (default - press Enter)")
        else:
            print(f"{idx}. {name}")

    while True:
        choice = input("Enter your choice (number or press Enter for default): ").strip()
        if choice == "":
            provider, model_key = default_option[1]
            print(f"Selected default: {default_option[0]}")
            return available_models[provider][model_key]
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(options):
                provider, model_key = options[choice_num - 1][1]
                return available_models[provider][model_key]
            print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            if choice:
                print("Please enter a valid number or press Enter for default")


def _get_model_options(available_models: Dict[str, Dict[str, Any]], purpose: str) -> List[Tuple[str, Tuple[str, str]]]:
    """Generates a list of model options based on the available models and the specified purpose."""
    options: List[Tuple[str, Tuple[str, str]]] = []
    if purpose == "NuGet package search":
        if "openai" in available_models:
            options.append(("gpt4o-mini", ("openai", "gpt4o-mini")))
            options.append(("gpt4o", ("openai", "gpt4o")))
        if "anthropic" in available_models:
            options.append(("claude-3-5-sonnet", ("anthropic", "claude-3-5-sonnet")))
    else:
        if "openai" in available_models:
            options.append(("gpt4o", ("openai", "gpt4o")))
            options.append(("gpt4o-mini", ("openai", "gpt4o-mini")))
            options.append(("o3-mini-medium", ("openai", "o3-mini-medium")))
            options.append(("o3-mini-high", ("openai", "o3-mini-high")))
            options.append(("o1-high", ("openai", "o1-high")))
        if "anthropic" in available_models:
            options.append(("claude-3-5-sonnet", ("anthropic", "claude-3-5-sonnet")))
    return options

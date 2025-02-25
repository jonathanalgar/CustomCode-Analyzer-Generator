import logging
import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Union

import requests
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agents.validation.constants import ODC_TEST_GENERATOR_EXE

logger = logging.getLogger(__name__)


def get_icon_for_solution(use_case: str, search_term_llm: BaseChatModel, class_dir: Path) -> Optional[Path]:
    """Fetches and sets an icon for the generated solution."""
    try:
        # Generate search term using LLM
        messages = [
            SystemMessage(
                content="Generate a single word or short phrase that would be good for searching for an icon that represents this functionality. Focus on visual concepts that could be represented as an icon."
            ),
            HumanMessage(content=f"Functionality: {use_case}"),
        ]

        search_term_response = search_term_llm.invoke(messages)
        search_term = search_term_response.content
        if isinstance(search_term, str):
            search_term = search_term.strip().strip('"').strip("'")
        else:
            logger.warning("Unexpected response format for search term")
            return None

        logger.debug(f"Generated icon search term: {search_term}")

        # Freepik icon search endpoint
        search_url = "https://api.freepik.com/v1/icons"
        headers = {"x-freepik-api-key": os.getenv("FREEPIK_API_KEY")}

        # We request a single free SVG icon
        search_params: dict[str, Union[str, int]] = {
            "term": search_term,
            "filters[free_svg]": "free",
            "per_page": 1,
        }

        search_response = requests.get(search_url, headers=headers, params=search_params)
        search_response.raise_for_status()
        search_data = search_response.json()

        if not search_data.get("data"):
            logger.warning(f"No icons found for search term: {search_term}")
            return None

        # Get the top result from the search
        top_icon_id = search_data["data"][0]["id"]
        icon_url = f"https://api.freepik.com/v1/icons/{top_icon_id}"
        icon_response = requests.get(icon_url, headers=headers)
        icon_response.raise_for_status()

        icon_data = icon_response.json()
        # Choose the largest available thumbnail
        largest_thumb = max(icon_data["data"]["thumbnails"], key=lambda x: x["width"] * x["height"])

        # Download the icon
        binary_response = requests.get(largest_thumb["url"])
        binary_response.raise_for_status()

        # Save the icon file locally
        icon_path = class_dir / "icon.png"
        with open(icon_path, "wb") as f:
            f.write(binary_response.content)

        logger.debug("Saved icon to solution root")

        # Update the interface
        impl_file = class_dir / f"{class_dir.name}.cs"
        try:
            subprocess.run(
                [
                    str(ODC_TEST_GENERATOR_EXE),
                    "--addicon",
                    str(impl_file),
                    "icon.png",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.debug("Successfully configured icon in project")
            return icon_path

        except subprocess.CalledProcessError as e:
            logger.warning(f"Error configuring icon in project: {e.stderr}")
            return None

    except Exception as e:
        logger.warning(f"Error getting icon: {str(e)}")
        return None


def get_token_stats(project_id: str) -> Tuple[int, float, str]:
    """Fetches token usage statistics from LangSmith."""
    total_tokens = 0
    total_cost = 0.0
    url = f"https://smith.langchain.com/projects/p/{project_id}"

    try:
        from langsmith import Client

        client = Client()
        stats = client.get_run_stats(project_ids=[project_id])

        total_tokens = stats.get("total_tokens", 0)
        total_cost = stats.get("total_cost", 0.0)

    except Exception as e:
        logger.debug(f"Failed to fetch token stats: {e}")

    return total_tokens, total_cost, url


def prettify_code(solution_dir: Path) -> None:
    """Sets up and runs CSharpier code formatting on the solution."""
    try:
        subprocess.run(
            ["dotnet", "new", "tool-manifest"],
            cwd=solution_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        logger.debug("Created .NET tool manifest")

        subprocess.run(
            ["dotnet", "tool", "install", "--local", "csharpier"],
            cwd=solution_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        logger.debug("Installed CSharpier")

        subprocess.run(
            ["dotnet", "csharpier", "."],
            cwd=solution_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info("Successfully formatted solution code with CSharpier")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to set up or run CSharpier: {e.stderr}")
    except Exception as e:
        logger.warning(f"Unexpected error during code formatting: {str(e)}")

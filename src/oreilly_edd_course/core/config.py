import os

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

DEFAULT_MODEL_ID = "qwen/qwen3.6-35b-a3b@q4_k_m"
DEFAULT_BASE_URL = "http://localhost:1234/v1"
DEFAULT_API_KEY = "lm-studio"


def get_model(
    model_id: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> OpenAIChatModel:
    """Build the LM Studio-backed model used throughout the course."""
    return OpenAIChatModel(
        model_id or os.environ.get("EDD_MODEL_ID", DEFAULT_MODEL_ID),
        provider=OpenAIProvider(
            base_url=base_url or os.environ.get("EDD_BASE_URL", DEFAULT_BASE_URL),
            api_key=api_key or os.environ.get("EDD_API_KEY", DEFAULT_API_KEY),
        ),
    )

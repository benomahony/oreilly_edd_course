"""Provider configuration via pydantic-settings.

Switch providers with the PROVIDER env var:
    PROVIDER=lmstudio   (default) local OpenAI-compatible server (LM Studio)
    PROVIDER=google     Google Gemini (uses GOOGLE_API_KEY)
"""

from typing import Literal

from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    provider: Literal["lmstudio", "google"] = "google"
    model: str = "meta/muse-glimmer"
    google_model: str = "gemini-2.5-pro"
    lmstudio_base_url: str = "http://localhost:1234/v1"


def get_model() -> Model:
    settings = Settings()
    if settings.provider == "google":
        return GoogleModel(settings.google_model)
    return OpenAIChatModel(
        settings.model,
        provider=OpenAIProvider(
            base_url=settings.lmstudio_base_url, api_key="lm-studio"
        ),
    )

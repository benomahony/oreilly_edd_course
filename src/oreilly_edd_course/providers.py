"""Provider-agnostic model factory.

Builds a pydantic-ai model from pydantic-settings configuration so you can
switch providers without editing code. Settings are read from environment
variables (or a `.env` file):

    PROVIDER=lmstudio   (default) local OpenAI-compatible server (LM Studio)
    PROVIDER=google     Google Gemini (uses GEMINI_API_KEY)
    PROVIDER=openai     OpenAI (uses OPENAI_API_KEY)

Example:
    PROVIDER=google uv run src/oreilly_edd_course/inference.py
"""

from typing import Literal

from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the LLM provider, read from env vars / `.env`."""

    model_config = SettingsConfigDict(env_file=".env")

    provider: Literal["lmstudio", "google", "openai"] = "lmstudio"
    model: str = "meta/muse-glimmer"
    lmstudio_base_url: str = "http://localhost:1234/v1"
    google_model: str = "gemini-2.5-flash"
    openai_model: str = "gpt-4o-mini"

    def build_model(self) -> Model:
        """Build the pydantic-ai model for the configured provider."""
        if self.provider == "google":
            return GoogleModel(self.google_model)
        if self.provider == "openai":
            return OpenAIChatModel(self.openai_model)
        return OpenAIChatModel(
            self.model,
            provider=OpenAIProvider(
                base_url=self.lmstudio_base_url,
                api_key="lm-studio",
            ),
        )


settings = Settings()


def get_model() -> Model:
    """Build the configured pydantic-ai model from the shared settings."""
    return settings.build_model()
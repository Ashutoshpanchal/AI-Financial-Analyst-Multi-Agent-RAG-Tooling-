from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Central config loaded from environment variables / .env file.
    All settings are typed and validated by Pydantic.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Database
    database_url: str = ""

    # OpenAI
    openai_api_key: str = ""

    # Langfuse
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    # Local LLM (Ollama)
    local_llm_enabled: bool = False
    local_llm_model: str = "llama3.2"
    local_llm_base_url: str = "http://localhost:11434/v1"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Use this everywhere via FastAPI dependency injection.
    """
    return Settings()

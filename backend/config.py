from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BAH API"
    app_version: str = "2.0.0"
    environment: str = "development"
    frontend_origin: str = "http://localhost:3000"

    # mock = test without GPU; remote = call local vLLM inside the cloud container
    inference_mode: str = "mock"
    vllm_base_url: str = "http://127.0.0.1:8000"
    vllm_api_key: str = ""
    vllm_model: str = "bah"
    model_version: str = "BAH-HF-v2"

    supabase_url: str = ""
    supabase_secret_key: str = ""

    admin_key: str = ""

    max_new_tokens: int = 1024
    temperature: float = 0.2
    request_timeout_seconds: int = 120
    max_history_messages: int = 8
    max_message_chars: int = 6000

    rate_limit_per_minute: int = 12
    rate_limit_window_seconds: int = 60

    # Set false in a private/local development environment only if you explicitly
    # want to allow requests without a configured analytics backend.
    analytics_optional: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

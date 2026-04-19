from pydantic_settings import BaseSettings, SettingsConfigDict


class SDKSettings(BaseSettings):
    api_base_url: str = "http://localhost:8000"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    timeout_seconds: float = 30.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = SDKSettings()

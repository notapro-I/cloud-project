from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_user: str = "llmobs"
    postgres_password: str = "llmobs"
    postgres_db: str = "llmobs"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    worker_poll_seconds: int = 60
    quality_sample_rate: float = 0.10
    quality_threshold: float = 3.5
    quality_window_size: int = 50

    drift_recent_count: int = 15
    drift_baseline_count: int = 30
    drift_min_samples: int = 10
    drift_delta_threshold: float = 0.0

    ollama_base_url: str = "http://localhost:11434"
    ollama_judge_model: str = "mistral"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def db_dsn(self) -> str:
        return (
            f"dbname={self.postgres_db} user={self.postgres_user} password={self.postgres_password} "
            f"host={self.postgres_host} port={self.postgres_port}"
        )


settings = Settings()

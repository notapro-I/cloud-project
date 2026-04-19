from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_user: str = "llmobs"
    postgres_password: str = "llmobs"
    postgres_db: str = "llmobs"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    api_port: int = 8000
    quality_sample_rate: float = 0.10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def db_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()

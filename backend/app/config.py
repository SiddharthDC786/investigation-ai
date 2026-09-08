from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(validation_alias=AliasChoices("DATABASE_URL", "database_url"))
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        validation_alias=AliasChoices("CORS_ORIGINS", "cors_origins"),
    )
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        validation_alias=AliasChoices("NEO4J_URI", "neo4j_uri"),
    )
    neo4j_user: str = Field(
        default="neo4j",
        validation_alias=AliasChoices("NEO4J_USER", "neo4j_user"),
    )
    neo4j_password: str = Field(
        default="vigilneo4j2026",
        validation_alias=AliasChoices("NEO4J_PASSWORD", "neo4j_password"),
    )
    neo4j_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("NEO4J_ENABLED", "neo4j_enabled"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

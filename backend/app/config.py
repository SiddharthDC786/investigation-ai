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
    jwt_secret: str = Field(
        default="change-me-in-production-use-long-random-secret",
        validation_alias=AliasChoices("JWT_SECRET", "jwt_secret"),
    )
    jwt_expire_minutes: int = Field(
        default=480,
        validation_alias=AliasChoices("JWT_EXPIRE_MINUTES", "jwt_expire_minutes"),
    )
    auth_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("AUTH_ENABLED", "auth_enabled"),
    )
    auth_password_salt: str = Field(
        default="vigil-demo-salt-change-in-production",
        validation_alias=AliasChoices("AUTH_PASSWORD_SALT", "auth_password_salt"),
    )
    demo_investigator_badge: str = Field(default="INV-2847")
    demo_supervisor_badge: str = Field(default="SUP-1001")
    demo_investigator_cases: list[str] = Field(default=["CASE0001"])
    demo_investigator_password_hash: str | None = Field(default=None)
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "environment"),
    )
    allow_demo_passwords: bool = Field(
        default=True,
        validation_alias=AliasChoices("ALLOW_DEMO_PASSWORDS", "allow_demo_passwords"),
    )
    login_rate_limit: int = Field(default=8)
    login_rate_window_seconds: int = Field(default=300)
    demo_supervisor_password_hash: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def validate_runtime_settings() -> None:
    """Reject unsafe production configuration at startup."""
    if settings.environment.lower() != "production":
        return
    unsafe_secrets = (
        "change-me-in-production-use-long-random-secret",
        "vigil-demo-salt-change-in-production",
    )
    if settings.jwt_secret in unsafe_secrets:
        raise RuntimeError("Production requires a unique JWT_SECRET")
    if settings.auth_password_salt in unsafe_secrets:
        raise RuntimeError("Production requires a unique AUTH_PASSWORD_SALT")
    if settings.allow_demo_passwords:
        raise RuntimeError("Set ALLOW_DEMO_PASSWORDS=false in production")


settings = Settings()
validate_runtime_settings()

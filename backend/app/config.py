from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "development"
    log_level: str = "INFO"
    log_format: str = "json"
    cors_allow_origins: str = "http://localhost:3000,http://localhost:8000"
    rate_limit_per_minute: int = 120
    max_bundle_size_mb: int = 20
    max_page_size: int = 200

    database_url: str = "postgresql+asyncpg://clerkstone:clerkstone@localhost:5432/clerkstone"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_statement_timeout_ms: int = 5000

    jwt_issuer: str = "https://clerkstone.local"
    jwt_audience: str = "clerkstone-api"
    jwt_access_token_ttl_seconds: int = 900
    jwt_private_key_path: str = ""
    jwt_public_key_path: str = ""
    # Inline PEM keys (base64/raw) for local dev where file secrets are unavailable.
    jwt_private_key_pem: str = ""
    jwt_public_key_pem: str = ""

    validator_base_url: str = "http://localhost:8080"
    validator_timeout_seconds: int = 20
    ukcore_package_version: str = "hl7.fhir.uk.core.r4@2.4.0"

    terminology_backend: str = "local"
    terminology_local_db_path: str = "./data/terminology/subset.json"
    terminology_nhse_base_url: str = "https://ontology.nhs.uk/production1/fhir"
    terminology_nhse_api_key: str = ""
    terminology_cache_ttl_seconds: int = 86400
    terminology_circuit_breaker_threshold: int = 5

    audit_hash_salt: str = "dev-salt"
    audit_verify_on_startup: bool = False

    data_class: str = "synthetic"

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

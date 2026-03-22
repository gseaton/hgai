"""HypergraphAI configuration settings."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HGAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # MongoDB
    mongo_uri: str = Field(
        default="mongodb://localhost:27017", description="MongoDB connection URI"
    )
    mongo_db: str = Field(default="hgai", description="MongoDB database name")

    # Security
    secret_key: str = Field(
        default="insecure-default-change-me", description="JWT signing secret key"
    )
    token_expire_minutes: int = Field(default=480, description="JWT token lifetime in minutes")
    algorithm: str = Field(default="HS256", description="JWT algorithm")

    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    log_level: str = Field(default="info")
    reload: bool = Field(default=False)
    cors_origins: str = Field(default="*")

    # Server identity
    server_id: str = Field(default="hgai-local")
    server_name: str = Field(default="HypergraphAI Local")

    # Query cache
    cache_enabled: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=300)
    cache_max_size: int = Field(default=1000)

    # Bootstrap admin account
    admin_username: str = Field(default="admin")
    admin_password: str = Field(default="pwd357")
    admin_email: str = Field(default="admin@hgai.local")

    @property
    def cors_origins_list(self) -> List[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()

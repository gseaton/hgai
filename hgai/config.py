"""HypergraphAI configuration settings."""

from functools import lru_cache
from typing import List, Optional

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

    # Storage backend
    storage_backend: str = Field(
        default="mongodb",
        description="Storage backend name (e.g. 'mongodb'). Env: HGAI_STORAGE_BACKEND",
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

    # API keys for machine-to-machine auth (UUID4 strings recommended)
    primary_api_key: Optional[str] = Field(default=None, description="Primary API key (UUID4)")
    secondary_api_key: Optional[str] = Field(default=None, description="Secondary API key (UUID4)")

    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8357)
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

    # SHQL / inference candidate caps. A pattern (or inference pass) fetches at
    # most this many documents from storage; anything beyond is dropped and the
    # result is flagged `truncated`.
    shql_max_node_candidates: int = Field(
        default=2000, ge=1,
        description="Max hypernodes fetched per SHQL node pattern. Env: HGAI_SHQL_MAX_NODE_CANDIDATES",
    )
    shql_max_edge_candidates: int = Field(
        default=2000, ge=1,
        description="Max hyperedges fetched per SHQL edge pattern. Env: HGAI_SHQL_MAX_EDGE_CANDIDATES",
    )
    inference_max_fact_edges: int = Field(
        default=5000, ge=1,
        description="Max fact edges fetched for inference expansion / transitive closure. "
                    "Env: HGAI_INFERENCE_MAX_FACT_EDGES",
    )

    shql_join_batch_size: int = Field(
        default=200, ge=1,
        description="Max distinct bound values (node ids / member-id sets) resolved by one storage "
                    "query when a SHQL pattern is evaluated against many bindings; 1 = one query per "
                    "binding. Env: HGAI_SHQL_JOIN_BATCH_SIZE",
    )

    # Mesh
    mesh_sync_interval_seconds: int = Field(default=300, description="Background mesh graph-list sync interval (0 = disabled)")

    # Help
    help_dir: Optional[str] = Field(
        default=None,
        description="Root directory of the built-in Help content (contains notes/*.md topics and media/). "
                    "Defaults to <project root>/docs/help. Env: HGAI_HELP_DIR",
    )

    # AI Agent Chat
    agent_chat_enabled: bool = Field(
        default=True, description="Master on/off switch for the AI Agent Chat module. Env: HGAI_AGENT_CHAT_ENABLED"
    )

    # Media
    max_media_size_mb: int = Field(default=100, description="Maximum upload size for a single media file, in MB")
    media_backend: str = Field(
        default="gridfs",
        description="Blob storage for media bytes: 'gridfs' (default, stored in MongoDB) or 's3'. "
                    "Metadata (id/checksum/ref_count/...) always stays in MongoDB either way. "
                    "Env: HGAI_MEDIA_BACKEND",
    )
    s3_bucket: Optional[str] = Field(default=None, description="S3 bucket name (required when media_backend=s3)")
    s3_endpoint_url: Optional[str] = Field(default=None, description="S3-compatible endpoint URL (e.g. MinIO); omit for real AWS S3")
    s3_region: str = Field(default="us-east-1", description="S3 region")
    s3_access_key_id: Optional[str] = Field(default=None, description="S3 access key (omit to use the default AWS credential chain)")
    s3_secret_access_key: Optional[str] = Field(default=None, description="S3 secret key (omit to use the default AWS credential chain)")

    # Bootstrap admin account
    admin_username: str = Field(default="admin")
    admin_password: str = Field(default="pwd357")
    admin_email: str = Field(default="admin@hgai.local")

    # Multi-tenancy — see docs/architecture/hypergraph-ai-multi-tenancy-*.md. Off by
    # default: everything runs in the implicit "default" tenant and behaves as before.
    multitenancy_enabled: bool = Field(
        default=False,
        description="Enforce tenant isolation between accounts. Env: HGAI_MULTITENANCY_ENABLED",
    )

    # Telemetry — see docs/architect/telemetry-20260929061557.md. Off by default:
    # a self-hosted operator must opt in. `telemetry_endpoint` is optional even
    # when enabled — Phase 1 ships HTTP export only (local-hypergraph storage,
    # the no-endpoint fallback the plan describes, is Phase 3a; until then,
    # enabling telemetry with no endpoint configured collects events in-process
    # but has nowhere to send them, and a startup warning says so).
    telemetry_enabled: bool = Field(
        default=False,
        description="Master switch for OTEL-shaped usage/error telemetry. Env: HGAI_TELEMETRY_ENABLED",
    )
    telemetry_endpoint: Optional[str] = Field(
        default=None,
        description="URL telemetry batches are POSTed to, e.g. https://telemetry.hypergra.ai/report. "
                    "Optional even when enabled. Env: HGAI_TELEMETRY_ENDPOINT",
    )
    telemetry_protocol: str = Field(
        default="hgai-envelope",
        description="Wire format for HGAI_TELEMETRY_ENDPOINT: 'hgai-envelope' (one JSON body per batch, "
                    "posted to the exact URL) or 'otlp-http-json' (not yet implemented — falls back to "
                    "hgai-envelope with a startup warning). Env: HGAI_TELEMETRY_PROTOCOL",
    )
    telemetry_api_key: Optional[str] = Field(
        default=None,
        description="Optional bearer credential sent to the telemetry endpoint. Env: HGAI_TELEMETRY_API_KEY",
    )
    telemetry_batch_size: int = Field(
        default=100, ge=1,
        description="Max events per export batch. Env: HGAI_TELEMETRY_BATCH_SIZE",
    )
    telemetry_flush_interval_seconds: float = Field(
        default=10, gt=0,
        description="Max time an event waits before its batch is dispatched, even if telemetry_batch_size "
                    "isn't reached. Env: HGAI_TELEMETRY_FLUSH_INTERVAL_SECONDS",
    )
    telemetry_queue_max_size: int = Field(
        default=10000, ge=1,
        description="Bounded in-memory event queue; oldest event is dropped when full. "
                    "Env: HGAI_TELEMETRY_QUEUE_MAX_SIZE",
    )
    telemetry_local_enabled: bool = Field(
        default=False,
        description="Also write telemetry into the __local-telemetry hypergraph even when "
                    "telemetry_endpoint is set (it is always used when no endpoint is set, "
                    "regardless of this flag). Env: HGAI_TELEMETRY_LOCAL_ENABLED",
    )
    telemetry_local_retention_days: int = Field(
        default=30, ge=0,
        description="Prune __local-telemetry hypernodes older than this many days; 0 disables pruning. "
                    "Env: HGAI_TELEMETRY_LOCAL_RETENTION_DAYS",
    )
    telemetry_include_graph_ids: bool = Field(
        default=False,
        description="Send graph/space ids in the clear instead of HMAC-hashed. "
                    "Env: HGAI_TELEMETRY_INCLUDE_GRAPH_IDS",
    )
    telemetry_include_account_ids: bool = Field(
        default=False,
        description="Send account usernames in the clear instead of HMAC-hashed. "
                    "Env: HGAI_TELEMETRY_INCLUDE_ACCOUNT_IDS",
    )
    telemetry_allow_insecure: bool = Field(
        default=False,
        description="Permit a non-HTTPS telemetry endpoint (local development only). "
                    "Env: HGAI_TELEMETRY_ALLOW_INSECURE",
    )
    telemetry_sample_rate: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Fraction of *usage* events kept (0.0-1.0). Error events are never sampled. "
                    "Env: HGAI_TELEMETRY_SAMPLE_RATE",
    )
    telemetry_environment: str = Field(
        default="production",
        description="Free-text deployment.environment resource attribute on every telemetry batch. "
                    "Env: HGAI_TELEMETRY_ENVIRONMENT",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()

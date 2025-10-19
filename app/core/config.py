"""Application configuration using pydantic-settings.

This module provides centralized configuration management,
loading settings from environment variables with validation.
"""
import logging

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Weak passwords that should trigger warnings
WEAK_PASSWORDS = {
    "password",
    "password123",
    "admin",
    "dev_password_change_in_production",
    "minioadmin",
    "",
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden via environment variables.
    See .env.example for all available options.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        frozen=True,  # Make immutable
    )

    # OpenAI Configuration
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key (required for production)"
    )
    openai_org_id: str | None = Field(
        default=None,
        description="OpenAI organization ID (optional)"
    )

    # Anthropic Configuration
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key (required for Claude models)"
    )

    # Ollama Configuration
    ollama_host: str = Field(
        default="http://localhost:11434",
        description="Ollama API host URL"
    )

    # Neo4j Configuration
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j database URI"
    )
    neo4j_user: str = Field(
        default="neo4j",
        description="Neo4j username"
    )
    neo4j_password: str = Field(
        default="dev_password_change_in_production",
        description="Neo4j password"
    )

    @field_validator("neo4j_password")
    @classmethod
    def validate_neo4j_password(cls, v: str) -> str:
        """Validate Neo4j password is not weak."""
        if v in WEAK_PASSWORDS:
            logger.warning(
                "⚠️  SECURITY WARNING: Weak Neo4j password detected! "
                "Set NEO4J_PASSWORD environment variable with a strong password."
            )
        return v

    # Model Configuration
    model_nano: str = Field(
        default="gpt-5-nano",
        description="Nano model for simple tasks"
    )
    model_mini: str = Field(
        default="gpt-5-mini",
        description="Mini model for moderate tasks"
    )
    model_standard: str = Field(
        default="gpt-5",
        description="Standard model for complex tasks"
    )

    # Cost Limits (USD)
    monthly_budget: float = Field(
        default=100.0,
        gt=0,
        description="Monthly budget limit in USD"
    )
    daily_budget: float = Field(
        default=3.33,
        gt=0,
        description="Daily budget limit in USD"
    )
    per_request_limit: float = Field(
        default=0.50,
        gt=0,
        description="Per-request cost limit in USD"
    )

    # Database Configuration
    postgres_host: str = Field(
        default="localhost",
        description="PostgreSQL host"
    )
    postgres_port: int = Field(
        default=5432,
        gt=0,
        lt=65536,
        description="PostgreSQL port"
    )
    postgres_db: str = Field(
        default="williams_librarian",
        description="PostgreSQL database name"
    )
    postgres_user: str = Field(
        default="librarian",
        description="PostgreSQL user"
    )
    postgres_password: str = Field(
        default="dev_password_change_in_production",
        description="PostgreSQL password"
    )

    @field_validator("postgres_password")
    @classmethod
    def validate_postgres_password(cls, v: str) -> str:
        """Validate PostgreSQL password is not weak."""
        if v in WEAK_PASSWORDS:
            logger.warning(
                "⚠️  SECURITY WARNING: Weak PostgreSQL password detected! "
                "Set POSTGRES_PASSWORD environment variable with a strong password."
            )
        return v

    # Redis Configuration
    redis_host: str = Field(
        default="localhost",
        description="Redis host"
    )
    redis_port: int = Field(
        default=6379,
        gt=0,
        lt=65536,
        description="Redis port"
    )
    redis_db: int = Field(
        default=0,
        ge=0,
        description="Redis database number"
    )

    # Qdrant Configuration
    qdrant_host: str = Field(
        default="localhost",
        description="Qdrant host"
    )
    qdrant_port: int = Field(
        default=6333,
        gt=0,
        lt=65536,
        description="Qdrant REST API port"
    )
    qdrant_grpc_port: int = Field(
        default=6334,
        gt=0,
        lt=65536,
        description="Qdrant gRPC port"
    )
    qdrant_collection_name: str = Field(
        default="librarian_embeddings",
        description="Qdrant collection name for content embeddings"
    )

    # MinIO Configuration
    minio_endpoint: str = Field(
        default="localhost:9000",
        description="MinIO endpoint (host:port)"
    )
    minio_access_key: str = Field(
        default="minioadmin",
        description="MinIO access key"
    )
    minio_secret_key: str = Field(
        default="minioadmin",
        description="MinIO secret key"
    )

    @field_validator("minio_secret_key")
    @classmethod
    def validate_minio_secret(cls, v: str) -> str:
        """Validate MinIO secret key is not weak."""
        if v in WEAK_PASSWORDS:
            logger.warning(
                "⚠️  SECURITY WARNING: Weak MinIO secret key detected! "
                "Set MINIO_SECRET_KEY environment variable with a strong password."
            )
        return v

    minio_secure: bool = Field(
        default=False,
        description="Use HTTPS for MinIO connections"
    )
    minio_region: str = Field(
        default="us-east-1",
        description="MinIO region (for S3 compatibility)"
    )

    # Library Configuration
    library_root: str = Field(
        default="./library",
        description="Root directory for local content library (deprecated, use MinIO)"
    )
    tier_a_threshold: float = Field(
        default=9.0,
        ge=0,
        le=10,
        description="Minimum quality score for tier-a (9.0+)"
    )
    tier_b_threshold: float = Field(
        default=7.0,
        ge=0,
        le=10,
        description="Minimum quality score for tier-b (7.0-8.9)"
    )
    tier_c_threshold: float = Field(
        default=5.0,
        ge=0,
        le=10,
        description="Minimum quality score for tier-c (5.0-6.9)"
    )

    # Application Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_file: str = Field(
        default="./data/logs/librarian.log",
        description="Log file path"
    )
    cache_dir: str = Field(
        default="./data/cache",
        description="Cache directory"
    )
    max_cache_size_gb: int = Field(
        default=10,
        gt=0,
        description="Maximum cache size in GB"
    )

    # Worker Configuration
    worker_concurrency: int = Field(
        default=4,
        gt=0,
        description="Number of concurrent workers"
    )
    batch_size: int = Field(
        default=10,
        gt=0,
        description="Batch size for processing"
    )
    retry_max_attempts: int = Field(
        default=3,
        gt=0,
        description="Maximum retry attempts"
    )
    retry_backoff_seconds: int = Field(
        default=2,
        gt=0,
        description="Retry backoff in seconds"
    )

    # UI Configuration
    streamlit_server_port: int = Field(
        default=8501,
        gt=0,
        lt=65536,
        description="Streamlit server port"
    )
    streamlit_theme: str = Field(
        default="dark",
        description="Streamlit theme"
    )

    # Feature Flags
    enable_caching: bool = Field(
        default=True,
        description="Enable caching"
    )
    enable_batch_processing: bool = Field(
        default=True,
        description="Enable batch processing"
    )
    enable_knowledge_graph: bool = Field(
        default=True,
        description="Enable knowledge graph"
    )
    enable_plugins: bool = Field(
        default=True,
        description="Enable plugin system"
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance.

    This function exists to allow for easier mocking in tests.

    Returns:
        The global Settings instance.
    """
    return settings

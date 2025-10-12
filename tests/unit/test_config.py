"""Unit tests for Settings configuration.

Following TDD RED-GREEN-REFACTOR cycle.
"""
import pytest
from pydantic import ValidationError

from app.core.config import Settings


class TestSettings:
    """Test suite for Settings configuration."""

    def test_settings_with_defaults(self):
        """Test Settings with default values."""
        settings = Settings()

        # Check defaults
        assert settings.log_level == "INFO"
        assert settings.monthly_budget == 100.0
        assert settings.daily_budget == 3.33
        assert settings.tier_a_threshold == 9.0
        assert settings.tier_b_threshold == 7.0
        assert settings.tier_c_threshold == 5.0

    def test_settings_model_names(self):
        """Test model name defaults."""
        settings = Settings()

        assert settings.model_nano == "gpt-5-nano"
        assert settings.model_mini == "gpt-5-mini"
        assert settings.model_standard == "gpt-5"

    def test_settings_database_config(self):
        """Test database configuration."""
        settings = Settings()

        assert settings.postgres_host == "localhost"
        assert settings.postgres_port == 5432
        assert settings.postgres_db == "williams_librarian"
        assert settings.redis_host == "localhost"
        assert settings.redis_port == 6379

    def test_settings_paths(self):
        """Test path configurations."""
        settings = Settings()

        assert settings.library_root == "./library"
        assert settings.qdrant_collection_name == "librarian_embeddings"
        assert settings.cache_dir == "./data/cache"
        assert settings.log_file == "./data/logs/librarian.log"

    def test_settings_feature_flags(self):
        """Test feature flag defaults."""
        settings = Settings()

        assert settings.enable_caching is True
        assert settings.enable_batch_processing is True
        assert settings.enable_knowledge_graph is True
        assert settings.enable_plugins is True

    def test_settings_from_env(self, monkeypatch):
        """Test loading settings from environment variables."""
        # Mock environment variables
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("MONTHLY_BUDGET", "200.0")
        monkeypatch.setenv("POSTGRES_HOST", "db.example.com")
        monkeypatch.setenv("ENABLE_CACHING", "false")

        settings = Settings()

        assert settings.log_level == "DEBUG"
        assert settings.monthly_budget == 200.0
        assert settings.postgres_host == "db.example.com"
        assert settings.enable_caching is False

    def test_settings_openai_api_key_optional(self):
        """Test that OpenAI API key can be None (for testing)."""
        settings = Settings()
        # API key is optional in Settings, required at runtime
        assert hasattr(settings, "openai_api_key")

    def test_settings_budget_validation(self):
        """Test budget values are positive."""
        # Monthly budget
        with pytest.raises(ValidationError):
            Settings(monthly_budget=-10.0)

        # Daily budget
        with pytest.raises(ValidationError):
            Settings(daily_budget=-1.0)

        # Per request limit
        with pytest.raises(ValidationError):
            Settings(per_request_limit=-0.5)

    def test_settings_tier_thresholds_order(self):
        """Test that tier thresholds are in correct order."""
        settings = Settings()

        # tier-a > tier-b > tier-c
        assert settings.tier_a_threshold > settings.tier_b_threshold
        assert settings.tier_b_threshold > settings.tier_c_threshold
        assert settings.tier_c_threshold > 0

    def test_settings_port_validation(self):
        """Test port numbers are valid."""
        # Postgres port
        with pytest.raises(ValidationError):
            Settings(postgres_port=-1)

        with pytest.raises(ValidationError):
            Settings(postgres_port=70000)

        # Redis port
        with pytest.raises(ValidationError):
            Settings(redis_port=0)

    def test_settings_worker_config(self):
        """Test worker configuration."""
        settings = Settings()

        assert settings.worker_concurrency == 4
        assert settings.batch_size == 10
        assert settings.retry_max_attempts == 3
        assert settings.retry_backoff_seconds == 2

    def test_settings_immutable(self):
        """Test that Settings is immutable (frozen)."""
        settings = Settings()

        with pytest.raises((ValidationError, AttributeError)):
            settings.log_level = "ERROR"

    def test_settings_max_cache_size(self):
        """Test max cache size configuration."""
        settings = Settings()
        assert settings.max_cache_size_gb == 10

    def test_settings_streamlit_config(self):
        """Test Streamlit configuration."""
        settings = Settings()
        assert settings.streamlit_server_port == 8501
        assert settings.streamlit_theme == "dark"

"""RED TESTS FOR S2-302: Prompt loader validation.

These tests verify that the production prompt loader:
1. Raises configuration error when template is missing
2. Loads prompts with checksum validation
3. Provides snapshot comparison for default prompts
"""
import pytest

from app.core.exceptions import ConfigurationError
from app.plugins.prompts import PromptLoader, PromptTemplate


@pytest.mark.unit
def test_prompt_loader_raises_on_missing_template():
    """Test that loader raises ConfigurationError when template doesn't exist."""
    loader = PromptLoader()
    
    with pytest.raises(ConfigurationError) as exc_info:
        loader.load("nonexistent_template")
    
    error_message = str(exc_info.value)
    assert "nonexistent_template" in error_message
    assert "not found" in error_message.lower()


@pytest.mark.unit
def test_prompt_loader_loads_template_with_checksum():
    """Test that loader loads template and computes checksum."""
    loader = PromptLoader()
    
    template = loader.load("summarize")
    
    assert isinstance(template, PromptTemplate)
    assert template.name == "summarize"
    assert len(template.content) > 0
    assert len(template.checksum) == 64  # SHA-256 hex digest


@pytest.mark.integration
def test_prompt_loader_matches_test_snapshot_checksum(tmp_path):
    """Test that production loader checksum matches test snapshot checksum."""
    # Create a test prompt file
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    prompt_file = prompt_dir / "test_prompt.prompt"
    test_content = "This is a test prompt for validation."
    prompt_file.write_text(test_content, encoding="utf-8")
    
    loader = PromptLoader(base_path=prompt_dir)
    template = loader.load("test_prompt")
    
    # Compute expected checksum manually
    import hashlib
    expected_checksum = hashlib.sha256(test_content.encode("utf-8")).hexdigest()
    
    assert template.checksum == expected_checksum


@pytest.mark.unit
def test_prompt_loader_caches_loaded_templates():
    """Test that loader caches templates to avoid repeated file I/O."""
    loader = PromptLoader()
    
    template1 = loader.load("summarize")
    template2 = loader.load("summarize")
    
    # Should return the same cached instance
    assert template1 is template2


@pytest.mark.unit
def test_prompt_template_exposes_required_fields():
    """Test that PromptTemplate has required fields for pipeline use."""
    loader = PromptLoader()
    template = loader.load("summarize")
    
    assert hasattr(template, "name")
    assert hasattr(template, "content")
    assert hasattr(template, "checksum")
    assert template.name == "summarize"

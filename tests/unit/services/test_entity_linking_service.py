"""Unit tests for EntityLinkingService."""

import pytest
from unittest.mock import Mock

from app.services.entity_linking_service import EntityLinkingService


@pytest.fixture
def mock_neo_repo():
    """Create mock Neo4j repository."""
    return Mock()


@pytest.fixture
def linking_service(mock_neo_repo):
    """Create EntityLinkingService instance."""
    return EntityLinkingService(mock_neo_repo)


def test_service_initialization(mock_neo_repo):
    """Test EntityLinkingService initializes correctly."""
    service = EntityLinkingService(mock_neo_repo)
    assert service._neo_repo == mock_neo_repo


def test_link_mention_new_entity(linking_service, mock_neo_repo):
    """Test linking mention to a new canonical entity."""
    mock_neo_repo.get_mention_text.return_value = "OpenAI"
    mock_neo_repo.get_entities_by_type.return_value = []  # No existing entities
    mock_neo_repo.get_entity.return_value = None  # Entity doesn't exist yet
    
    entity_id = linking_service.link_mention(
        mention_id="m123",
        canonical_name="OpenAI",
        entity_type="ORG"
    )
    
    # Should create new entity
    mock_neo_repo.create_canonical_entity.assert_called_once()
    mock_neo_repo.link_mention_to_entity.assert_called_once()
    assert entity_id is not None


def test_link_mention_existing_entity(linking_service, mock_neo_repo):
    """Test linking mention to existing canonical entity."""
    mock_neo_repo.get_mention_text.return_value = "openai"
    mock_neo_repo.get_entities_by_type.return_value = []
    mock_neo_repo.get_entity.return_value = {
        "id": "entity123",
        "canonical_name": "OpenAI",
        "entity_type": "ORG"
    }
    
    entity_id = linking_service.link_mention(
        mention_id="m123",
        canonical_name="OpenAI",
        entity_type="ORG"
    )
    
    # Should link to existing entity
    mock_neo_repo.link_mention_to_entity.assert_called_once()
    mock_neo_repo.add_entity_alias.assert_called_once()
    # Should not create new entity (already exists)
    assert entity_id is not None


def test_link_mention_nonexistent_mention(linking_service, mock_neo_repo):
    """Test linking nonexistent mention raises error."""
    mock_neo_repo.get_mention_text.return_value = None
    
    with pytest.raises(ValueError, match="does not exist"):
        linking_service.link_mention(
            mention_id="nonexistent",
            canonical_name="Test",
            entity_type="PERSON"
        )


def test_link_mention_fuzzy_match_existing(linking_service, mock_neo_repo):
    """Test linking mention with fuzzy matching to existing entity."""
    mock_neo_repo.get_mention_text.return_value = "open ai"
    
    # Existing similar entity
    existing_entity = {
        "id": "entity123",
        "canonical_name": "OpenAI",
        "entity_type": "ORG",
        "text": "OpenAI"
    }
    mock_neo_repo.get_entities_by_type.return_value = [existing_entity]
    mock_neo_repo.get_entity.return_value = existing_entity
    
    entity_id = linking_service.link_mention(
        mention_id="m123",
        canonical_name="open ai",
        entity_type="ORG"
    )
    
    # Should use existing entity
    assert entity_id == "entity123"
    mock_neo_repo.link_mention_to_entity.assert_called_once()


def test_batch_link_mentions(linking_service, mock_neo_repo):
    """Test batch linking of mentions."""
    mock_neo_repo.get_mention_text.side_effect = ["OpenAI", "Google", "Microsoft"]
    mock_neo_repo.get_entities_by_type.return_value = []
    mock_neo_repo.get_entity.return_value = None
    
    mentions = [
        {"mention_id": "m1", "canonical_name": "OpenAI", "entity_type": "ORG"},
        {"mention_id": "m2", "canonical_name": "Google", "entity_type": "ORG"},
        {"mention_id": "m3", "canonical_name": "Microsoft", "entity_type": "ORG"}
    ]
    
    entity_ids = linking_service.batch_link_mentions(mentions)
    
    assert len(entity_ids) == 3
    assert mock_neo_repo.create_canonical_entity.call_count == 3


def test_batch_link_mentions_empty_list(linking_service):
    """Test batch linking with empty list."""
    entity_ids = linking_service.batch_link_mentions([])
    assert entity_ids == []


def test_calculate_confidence_exact_match(linking_service):
    """Test confidence calculation for exact match."""
    confidence = linking_service._calculate_confidence("OpenAI", "OpenAI")
    assert confidence == 1.0


def test_calculate_confidence_case_insensitive_match(linking_service):
    """Test confidence for case-insensitive exact match."""
    confidence = linking_service._calculate_confidence("openai", "OpenAI")
    assert confidence == 1.0


def test_calculate_confidence_whitespace_normalized(linking_service):
    """Test confidence with extra whitespace."""
    confidence = linking_service._calculate_confidence("OpenAI  Inc", "OpenAI Inc")
    assert confidence == 1.0


def test_calculate_confidence_very_similar(linking_service):
    """Test confidence for very similar strings."""
    confidence = linking_service._calculate_confidence("OpenAI Inc", "OpenAI")
    assert confidence >= 0.90


def test_calculate_confidence_moderately_similar(linking_service):
    """Test confidence for moderately similar strings."""
    confidence = linking_service._calculate_confidence("John Smith", "Jon Smith")
    assert 0.6 <= confidence < 0.9


def test_calculate_confidence_low_similarity(linking_service):
    """Test confidence for low similarity strings."""
    confidence = linking_service._calculate_confidence("Apple", "Microsoft")
    assert confidence >= 0.6


def test_normalize_text_lowercase(linking_service):
    """Test text normalization converts to lowercase."""
    normalized = linking_service._normalize_text("OpenAI")
    assert normalized == "openai"


def test_normalize_text_removes_extra_whitespace(linking_service):
    """Test text normalization removes extra whitespace."""
    normalized = linking_service._normalize_text("Open  AI   Inc")
    assert normalized == "open ai inc"


def test_normalize_text_empty_string(linking_service):
    """Test normalizing empty string."""
    normalized = linking_service._normalize_text("")
    assert normalized == ""


def test_string_similarity_exact_match(linking_service):
    """Test string similarity for exact match."""
    similarity = linking_service._string_similarity("test", "test")
    assert similarity == 1.0


def test_string_similarity_substring_match(linking_service):
    """Test string similarity for substring match."""
    similarity = linking_service._string_similarity("openai", "openai inc")
    assert similarity >= 0.85


def test_string_similarity_reverse_substring(linking_service):
    """Test string similarity with reversed substring."""
    similarity = linking_service._string_similarity("openai inc", "openai")
    assert similarity >= 0.85


def test_string_similarity_space_difference(linking_service):
    """Test string similarity when only spaces differ."""
    similarity = linking_service._string_similarity("open ai", "openai")
    assert similarity == 0.95


def test_string_similarity_no_space_substring(linking_service):
    """Test similarity for substring match without spaces."""
    similarity = linking_service._string_similarity("open ai", "open ai inc")
    assert similarity >= 0.85


def test_string_similarity_empty_strings(linking_service):
    """Test similarity of empty strings."""
    assert linking_service._string_similarity("", "") == 0.0
    assert linking_service._string_similarity("test", "") == 0.0
    assert linking_service._string_similarity("", "test") == 0.0


def test_string_similarity_character_level(linking_service):
    """Test character-level similarity calculation."""
    similarity = linking_service._string_similarity("abc", "axc")
    # 2 out of 3 characters match
    assert similarity == pytest.approx(2/3, abs=0.01)


def test_find_similar_entity_exact_match(linking_service, mock_neo_repo):
    """Test finding similar entity with exact match."""
    entities = [
        {"id": "e1", "canonical_name": "OpenAI", "entity_type": "ORG", "text": "OpenAI"}
    ]
    mock_neo_repo.get_entities_by_type.return_value = entities
    
    similar = linking_service._find_similar_entity("OpenAI", "ORG")
    
    assert similar is not None
    assert similar["id"] == "e1"


def test_find_similar_entity_fuzzy_match(linking_service, mock_neo_repo):
    """Test finding similar entity with fuzzy match."""
    entities = [
        {"id": "e1", "canonical_name": "OpenAI", "entity_type": "ORG", "text": "OpenAI"}
    ]
    mock_neo_repo.get_entities_by_type.return_value = entities
    
    similar = linking_service._find_similar_entity("open ai", "ORG")
    
    assert similar is not None
    assert similar["id"] == "e1"


def test_find_similar_entity_no_match(linking_service, mock_neo_repo):
    """Test when no similar entity found."""
    entities = [
        {"id": "e1", "canonical_name": "Google", "entity_type": "ORG", "text": "Google"}
    ]
    mock_neo_repo.get_entities_by_type.return_value = entities
    
    similar = linking_service._find_similar_entity("Microsoft", "ORG")
    
    # Too dissimilar, should return None
    assert similar is None


def test_find_similar_entity_prefers_canonical(linking_service, mock_neo_repo):
    """Test that entities with canonical_name are preferred."""
    entities = [
        {
            "id": "e1",
            "text": "OpenAI",
            "entity_type": "ORG",
            "canonical_name": None  # Not yet linked
        },
        {
            "id": "e2",
            "canonical_name": "OpenAI",
            "entity_type": "ORG",
            "text": "OpenAI"  # Already linked
        }
    ]
    mock_neo_repo.get_entities_by_type.return_value = entities
    
    similar = linking_service._find_similar_entity("OpenAI", "ORG")
    
    # Should prefer e2 (has canonical_name)
    assert similar["id"] == "e2"


def test_find_similar_entity_empty_list(linking_service, mock_neo_repo):
    """Test finding similar entity when no entities exist."""
    mock_neo_repo.get_entities_by_type.return_value = []
    
    similar = linking_service._find_similar_entity("OpenAI", "ORG")
    
    assert similar is None


def test_link_mention_updates_existing_without_canonical(linking_service, mock_neo_repo):
    """Test linking updates existing entity that lacks canonical_name."""
    mock_neo_repo.get_mention_text.return_value = "OpenAI"
    mock_neo_repo.get_entities_by_type.return_value = []
    
    # Existing entity without canonical_name (created by EntityExtractor)
    existing_entity = {
        "id": "entity123",
        "text": "OpenAI",
        "entity_type": "ORG",
        "canonical_name": None  # Missing canonical fields
    }
    mock_neo_repo.get_entity.return_value = existing_entity
    
    entity_id = linking_service.link_mention(
        mention_id="m123",
        canonical_name="OpenAI",
        entity_type="ORG"
    )
    
    # Should add canonical fields to existing entity
    mock_neo_repo.create_canonical_entity.assert_called_once()
    mock_neo_repo.link_mention_to_entity.assert_called_once()


def test_confidence_levels_all_ranges(linking_service):
    """Test that confidence calculations cover all specified ranges."""
    # Exact match: 1.0
    assert linking_service._calculate_confidence("Test", "Test") == 1.0
    
    # Very close fuzzy: 0.95
    conf = linking_service._calculate_confidence("OpenAI Inc", "OpenAI")
    assert conf >= 0.85
    
    # Moderate/Low: 0.65-0.75
    conf = linking_service._calculate_confidence("John Smith", "Jon Smith")
    assert 0.60 <= conf < 0.95


def test_batch_link_handles_duplicates(linking_service, mock_neo_repo):
    """Test batch linking handles duplicate canonical names."""
    mock_neo_repo.get_mention_text.side_effect = ["OpenAI", "OpenAI", "OpenAI"]
    mock_neo_repo.get_entities_by_type.return_value = []
    
    # First call: entity doesn't exist
    # Subsequent calls: entity exists
    mock_neo_repo.get_entity.side_effect = [
        None,  # First mention creates entity
        {"id": "entity123", "canonical_name": "OpenAI", "entity_type": "ORG"},  # Second mention finds it
        {"id": "entity123", "canonical_name": "OpenAI", "entity_type": "ORG"}   # Third mention finds it
    ]
    
    mentions = [
        {"mention_id": "m1", "canonical_name": "OpenAI", "entity_type": "ORG"},
        {"mention_id": "m2", "canonical_name": "OpenAI", "entity_type": "ORG"},
        {"mention_id": "m3", "canonical_name": "OpenAI", "entity_type": "ORG"}
    ]
    
    entity_ids = linking_service.batch_link_mentions(mentions)
    
    # All should link to same entity
    assert len(entity_ids) == 3
    # Only first mention creates entity, rest link to existing
    assert mock_neo_repo.create_canonical_entity.call_count == 1


def test_string_similarity_high_threshold(linking_service):
    """Test string similarity with high similarity threshold."""
    # These should be similar enough for fuzzy matching (>0.8)
    assert linking_service._string_similarity("openai", "openai inc") > 0.8
    assert linking_service._string_similarity("google", "google inc") > 0.8
    assert linking_service._string_similarity("apple", "apple inc") > 0.8


def test_string_similarity_low_threshold(linking_service):
    """Test string similarity below fuzzy match threshold."""
    # These should be too dissimilar (<0.8)
    assert linking_service._string_similarity("apple", "microsoft") < 0.8
    assert linking_service._string_similarity("google", "amazon") < 0.8


def test_link_mention_with_special_characters(linking_service, mock_neo_repo):
    """Test linking mention with special characters."""
    mock_neo_repo.get_mention_text.return_value = "AT&T"
    mock_neo_repo.get_entities_by_type.return_value = []
    mock_neo_repo.get_entity.return_value = None
    
    entity_id = linking_service.link_mention(
        mention_id="m123",
        canonical_name="AT&T",
        entity_type="ORG"
    )
    
    assert entity_id is not None
    mock_neo_repo.create_canonical_entity.assert_called_once()


def test_normalize_text_preserves_meaningful_spaces(linking_service):
    """Test that normalization preserves single spaces between words."""
    normalized = linking_service._normalize_text("Open AI")
    assert normalized == "open ai"
    assert normalized.count(" ") == 1


def test_find_similar_entity_multiple_candidates(linking_service, mock_neo_repo):
    """Test finding similar entity chooses best match from multiple candidates."""
    entities = [
        {"id": "e1", "canonical_name": "OpenAI", "entity_type": "ORG", "text": "OpenAI"},
        {"id": "e2", "canonical_name": "Open AI Inc", "entity_type": "ORG", "text": "Open AI Inc"},
        {"id": "e3", "canonical_name": "OpenAI Corporation", "entity_type": "ORG", "text": "OpenAI Corporation"}
    ]
    mock_neo_repo.get_entities_by_type.return_value = entities
    
    similar = linking_service._find_similar_entity("OpenAI", "ORG")
    
    # Should match e1 (exact match)
    assert similar["id"] == "e1"

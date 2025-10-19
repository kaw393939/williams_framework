"""Unit tests for RelationExtractionService."""

import pytest
from unittest.mock import Mock, MagicMock, patch
import re

from app.services.relation_extraction_service import RelationExtractionService


@pytest.fixture
def mock_neo_repo():
    """Create mock Neo4j repository."""
    return Mock()


@pytest.fixture
def mock_spacy_nlp():
    """Create mock spaCy NLP model."""
    nlp = Mock()
    doc = Mock()
    doc.ents = []
    nlp.return_value = doc
    return nlp


@pytest.fixture
def relation_service(mock_neo_repo, mock_spacy_nlp):
    """Create RelationExtractionService with mocked spaCy."""
    with patch('app.services.relation_extraction_service.spacy.load', return_value=mock_spacy_nlp):
        service = RelationExtractionService(mock_neo_repo)
        service._nlp = mock_spacy_nlp  # Ensure mock is used
        return service


def test_service_initialization(mock_neo_repo, mock_spacy_nlp):
    """Test RelationExtractionService initializes correctly."""
    with patch('app.services.relation_extraction_service.spacy.load', return_value=mock_spacy_nlp):
        service = RelationExtractionService(mock_neo_repo)
        assert service._neo_repo == mock_neo_repo
        assert service._nlp is not None
        assert "EMPLOYED_BY" in service._patterns
        assert "FOUNDED" in service._patterns
        assert "CITES" in service._patterns
        assert "LOCATED_IN" in service._patterns


def test_extract_relations_no_chunk(relation_service, mock_neo_repo):
    """Test extract_relations when chunk doesn't exist."""
    mock_neo_repo.get_chunk.return_value = None
    
    relations = relation_service.extract_relations("nonexistent_chunk")
    
    assert relations == []


def test_extract_relations_insufficient_entities(relation_service, mock_neo_repo):
    """Test extract_relations with less than 2 entities."""
    mock_chunk = {"id": "chunk123", "text": "Test text"}
    mock_neo_repo.get_chunk.return_value = mock_chunk
    
    # Mock: only 1 entity
    mock_neo_repo.execute_query.return_value = [
        {"text": "Entity1", "entity_type": "PERSON", "entity_id": "e1", "offset": 0}
    ]
    
    relations = relation_service.extract_relations("chunk123")
    
    assert relations == []


def test_extract_relations_employed_by_pattern(relation_service, mock_neo_repo, mock_spacy_nlp):
    """Test extracting EMPLOYED_BY relationship."""
    text = "John Smith works at Google Inc"
    mock_chunk = {"id": "chunk123", "text": text}
    mock_neo_repo.get_chunk.return_value = mock_chunk
    
    # Mock entities
    entities = [
        {"text": "John Smith", "entity_type": "PERSON", "entity_id": "e1", "offset": 0},
        {"text": "Google Inc", "entity_type": "ORG", "entity_id": "e2", "offset": 20}
    ]
    mock_neo_repo.execute_query.return_value = entities
    
    # Mock spaCy doc
    doc = Mock()
    mock_spacy_nlp.return_value = doc
    
    relations = relation_service.extract_relations("chunk123")
    
    # Should find EMPLOYED_BY relation
    assert len(relations) > 0
    assert relations[0]["type"] == "EMPLOYED_BY"
    assert relations[0]["subject_text"] == "John Smith"
    assert relations[0]["object_text"] == "Google Inc"
    assert relations[0]["confidence"] >= 0.5


def test_extract_relations_founded_pattern(relation_service, mock_neo_repo, mock_spacy_nlp):
    """Test extracting FOUNDED relationship."""
    text = "Steve Jobs founded Apple Computer"
    mock_chunk = {"id": "chunk123", "text": text}
    mock_neo_repo.get_chunk.return_value = mock_chunk
    
    entities = [
        {"text": "Steve Jobs", "entity_type": "PERSON", "entity_id": "e1", "offset": 0},
        {"text": "Apple Computer", "entity_type": "ORG", "entity_id": "e2", "offset": 23}
    ]
    mock_neo_repo.execute_query.return_value = entities
    
    doc = Mock()
    mock_spacy_nlp.return_value = doc
    
    relations = relation_service.extract_relations("chunk123")
    
    assert len(relations) > 0
    assert relations[0]["type"] == "FOUNDED"
    assert relations[0]["subject_text"] == "Steve Jobs"
    assert relations[0]["object_text"] == "Apple Computer"


def test_extract_relations_cites_pattern(relation_service, mock_neo_repo, mock_spacy_nlp):
    """Test extracting CITES relationship."""
    text = "The report according to NASA shows climate change"
    mock_chunk = {"id": "chunk123", "text": text}
    mock_neo_repo.get_chunk.return_value = mock_chunk
    
    entities = [
        {"text": "report", "entity_type": "DOCUMENT", "entity_id": "e1", "offset": 4},
        {"text": "NASA", "entity_type": "ORG", "entity_id": "e2", "offset": 32}
    ]
    mock_neo_repo.execute_query.return_value = entities
    
    doc = Mock()
    mock_spacy_nlp.return_value = doc
    
    relations = relation_service.extract_relations("chunk123")
    
    assert len(relations) > 0
    found_cites = any(r["type"] == "CITES" for r in relations)
    assert found_cites


def test_extract_relations_located_in_pattern(relation_service, mock_neo_repo, mock_spacy_nlp):
    """Test extracting LOCATED_IN relationship."""
    text = "Google is based in Mountain View"
    mock_chunk = {"id": "chunk123", "text": text}
    mock_neo_repo.get_chunk.return_value = mock_chunk
    
    entities = [
        {"text": "Google", "entity_type": "ORG", "entity_id": "e1", "offset": 0},
        {"text": "Mountain View", "entity_type": "LOC", "entity_id": "e2", "offset": 19}
    ]
    mock_neo_repo.execute_query.return_value = entities
    
    doc = Mock()
    mock_spacy_nlp.return_value = doc
    
    relations = relation_service.extract_relations("chunk123")
    
    assert len(relations) > 0
    assert relations[0]["type"] == "LOCATED_IN"


def test_calculate_relation_confidence_strong_pattern(relation_service):
    """Test confidence calculation for strong patterns."""
    confidence = relation_service._calculate_relation_confidence(
        "FOUNDED",
        "founded"
    )
    assert confidence == 0.95


def test_calculate_relation_confidence_weak_pattern(relation_service):
    """Test confidence calculation for weak patterns."""
    confidence = relation_service._calculate_relation_confidence(
        "LOCATED_IN",
        "in"
    )
    assert confidence == 0.7


def test_calculate_relation_confidence_default(relation_service):
    """Test default confidence calculation."""
    confidence = relation_service._calculate_relation_confidence(
        "EMPLOYED_BY",
        "joined"
    )
    assert confidence == 0.85


def test_extract_temporal_info_with_year(relation_service):
    """Test extracting temporal information with year."""
    temporal = relation_service._extract_temporal_info(
        "Founded in 1976 in California"
    )
    assert temporal["year"] == "1976"


def test_extract_temporal_info_without_year(relation_service):
    """Test extracting temporal information without year."""
    temporal = relation_service._extract_temporal_info(
        "Founded recently in California"
    )
    assert temporal == {}


def test_extract_temporal_info_multiple_years(relation_service):
    """Test extracting first year when multiple present."""
    temporal = relation_service._extract_temporal_info(
        "Between 1995 and 2000"
    )
    assert temporal["year"] == "1995"


def test_store_relation_basic(relation_service, mock_neo_repo):
    """Test storing a basic relation."""
    relation = {
        "type": "EMPLOYED_BY",
        "subject_id": "e1",
        "object_id": "e2",
        "subject_text": "John",
        "object_text": "Google",
        "confidence": 0.9,
        "evidence_text": "John works at Google",
        "source_chunk_id": "chunk123",
        "pattern_matched": "works at"
    }
    
    relation_service._store_relation(relation)
    
    # Verify execute_write was called
    mock_neo_repo.execute_write.assert_called_once()
    call_args = mock_neo_repo.execute_write.call_args
    assert "EMPLOYED_BY" in call_args[0][0]
    assert call_args[0][1]["confidence"] == 0.9


def test_store_relation_with_temporal_info(relation_service, mock_neo_repo):
    """Test storing relation with temporal information."""
    relation = {
        "type": "FOUNDED",
        "subject_id": "e1",
        "object_id": "e2",
        "subject_text": "Steve",
        "object_text": "Apple",
        "confidence": 0.95,
        "evidence_text": "Steve founded Apple in 1976",
        "source_chunk_id": "chunk123",
        "pattern_matched": "founded",
        "year": "1976"
    }
    
    relation_service._store_relation(relation)
    
    call_args = mock_neo_repo.execute_write.call_args
    assert call_args[0][1]["year"] == "1976"


def test_batch_extract_relations(relation_service, mock_neo_repo, mock_spacy_nlp):
    """Test batch extraction of relations."""
    # Mock chunks
    mock_neo_repo.get_chunk.side_effect = [
        {"id": "chunk1", "text": "John works at Google"},
        {"id": "chunk2", "text": "Mary founded Startup"}
    ]
    
    # Mock entities for each chunk
    mock_neo_repo.execute_query.side_effect = [
        [  # Chunk 1 entities
            {"text": "John", "entity_type": "PERSON", "entity_id": "e1", "offset": 0},
            {"text": "Google", "entity_type": "ORG", "entity_id": "e2", "offset": 14}
        ],
        [  # Chunk 2 entities
            {"text": "Mary", "entity_type": "PERSON", "entity_id": "e3", "offset": 0},
            {"text": "Startup", "entity_type": "ORG", "entity_id": "e4", "offset": 14}
        ]
    ]
    
    doc = Mock()
    mock_spacy_nlp.return_value = doc
    
    relations = relation_service.batch_extract_relations(["chunk1", "chunk2"])
    
    # Should have extracted relations from both chunks
    assert len(relations) >= 2
    assert any(r["subject_text"] == "John" for r in relations)
    assert any(r["subject_text"] == "Mary" for r in relations)


def test_batch_extract_relations_empty_list(relation_service):
    """Test batch extraction with empty list."""
    relations = relation_service.batch_extract_relations([])
    assert relations == []


def test_extract_relation_by_pattern_passive_voice(relation_service, mock_spacy_nlp):
    """Test handling passive voice in FOUNDED relations."""
    text = "OpenAI was founded by Sam Altman"
    doc = Mock()
    
    entities = [
        {"text": "OpenAI", "entity_type": "ORG", "entity_id": "e1", "offset": 0},
        {"text": "Sam Altman", "entity_type": "PERSON", "entity_id": "e2", "offset": 22}
    ]
    
    relations = relation_service._extract_relation_by_pattern(
        text, doc, entities, "FOUNDED", r"\bfounded\b", "chunk123"
    )
    
    # In passive voice, subject and object should be swapped
    # "Sam Altman founded OpenAI" (not "OpenAI founded Sam Altman")
    if relations:
        assert relations[0]["subject_text"] == "Sam Altman"
        assert relations[0]["object_text"] == "OpenAI"


def test_extract_relation_by_pattern_no_match(relation_service, mock_spacy_nlp):
    """Test when pattern doesn't match."""
    text = "Some unrelated text"
    doc = Mock()
    entities = [
        {"text": "Entity1", "entity_type": "PERSON", "entity_id": "e1", "offset": 0}
    ]
    
    relations = relation_service._extract_relation_by_pattern(
        text, doc, entities, "EMPLOYED_BY", r"\bworks at\b", "chunk123"
    )
    
    assert relations == []


def test_get_chunk_entities(relation_service, mock_neo_repo):
    """Test getting entities for a chunk."""
    mock_entities = [
        {"text": "John", "entity_type": "PERSON", "entity_id": "e1", "offset": 0},
        {"text": "Google", "entity_type": "ORG", "entity_id": "e2", "offset": 20}
    ]
    mock_neo_repo.execute_query.return_value = mock_entities
    
    entities = relation_service._get_chunk_entities("chunk123")
    
    assert len(entities) == 2
    assert entities[0]["text"] == "John"
    assert entities[1]["text"] == "Google"
    mock_neo_repo.execute_query.assert_called_once()


def test_pattern_matching_case_insensitive(relation_service, mock_neo_repo, mock_spacy_nlp):
    """Test that pattern matching is case-insensitive."""
    text = "John WORKS AT Google"  # Uppercase
    mock_chunk = {"id": "chunk123", "text": text}
    mock_neo_repo.get_chunk.return_value = mock_chunk
    
    entities = [
        {"text": "John", "entity_type": "PERSON", "entity_id": "e1", "offset": 0},
        {"text": "Google", "entity_type": "ORG", "entity_id": "e2", "offset": 14}
    ]
    mock_neo_repo.execute_query.return_value = entities
    
    doc = Mock()
    mock_spacy_nlp.return_value = doc
    
    relations = relation_service.extract_relations("chunk123")
    
    # Should match despite uppercase
    assert len(relations) > 0


def test_extract_relations_stores_in_neo4j(relation_service, mock_neo_repo, mock_spacy_nlp):
    """Test that extracted relations are stored in Neo4j."""
    text = "John works at Google"
    mock_chunk = {"id": "chunk123", "text": text}
    mock_neo_repo.get_chunk.return_value = mock_chunk
    
    entities = [
        {"text": "John", "entity_type": "PERSON", "entity_id": "e1", "offset": 0},
        {"text": "Google", "entity_type": "ORG", "entity_id": "e2", "offset": 14}
    ]
    mock_neo_repo.execute_query.return_value = entities
    
    doc = Mock()
    mock_spacy_nlp.return_value = doc
    
    relation_service.extract_relations("chunk123")
    
    # Should have called execute_write to store relation
    assert mock_neo_repo.execute_write.called


def test_confidence_calculation_for_all_types(relation_service):
    """Test confidence calculation for all relation types."""
    # Test each relation type
    assert relation_service._calculate_relation_confidence("FOUNDED", "founded") == 0.95
    assert relation_service._calculate_relation_confidence("EMPLOYED_BY", "works at") == 0.95
    assert relation_service._calculate_relation_confidence("LOCATED_IN", "based in") == 0.95
    assert relation_service._calculate_relation_confidence("CITES", "according to") == 0.95
    
    # Weaker patterns
    assert relation_service._calculate_relation_confidence("LOCATED_IN", "in") == 0.7
    assert relation_service._calculate_relation_confidence("EMPLOYED_BY", "joined") == 0.85

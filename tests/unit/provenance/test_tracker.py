"""Unit tests for ProvenanceTracker."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from app.provenance.tracker import ProvenanceTracker


@pytest.fixture
def mock_neo4j_driver():
    """Create mock Neo4j driver."""
    driver = Mock()
    driver.close = AsyncMock()  # Make close async
    session = AsyncMock()
    result = AsyncMock()
    
    # Mock session as async context manager
    session_context = AsyncMock()
    session_context.__aenter__ = AsyncMock(return_value=session)
    session_context.__aexit__ = AsyncMock(return_value=None)
    driver.session = Mock(return_value=session_context)
    
    session.run.return_value = result
    
    return driver


@pytest.fixture
def tracker(mock_neo4j_driver):
    """Create ProvenanceTracker instance with mock driver."""
    return ProvenanceTracker(neo4j_driver=mock_neo4j_driver)


@pytest.fixture
def tracker_no_driver():
    """Create ProvenanceTracker instance without driver."""
    return ProvenanceTracker(neo4j_driver=None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_track_import_creates_nodes(tracker, mock_neo4j_driver):
    """Test track_import creates Content and Source nodes."""
    import_data = {
        "content_id": "content123",
        "source_url": "https://youtube.com/watch?v=abc",
        "source_type": "youtube",
        "metadata": {"title": "Test Video", "duration": 120},
        "imported_at": "2025-10-13T10:00:00",
    }
    
    # Mock session and result
    session_context = mock_neo4j_driver.session.return_value
    session = await session_context.__aenter__()
    result = AsyncMock()
    mock_record = {"provenance_id": "prov123"}
    result.single.return_value = mock_record
    session.run.return_value = result
    
    provenance_id = await tracker.track_import(import_data)
    
    assert provenance_id == "prov123"
    assert session.run.called
    
    # Verify query contains CREATE statements
    call_args = session.run.call_args
    query = call_args[0][0]
    assert "CREATE (c:Content" in query
    assert "CREATE (s:Source" in query
    assert "IMPORTED_FROM" in query


@pytest.mark.unit
@pytest.mark.asyncio
async def test_track_import_without_driver(tracker_no_driver):
    """Test track_import works without Neo4j driver."""
    import_data = {
        "content_id": "content123",
        "source_url": "https://youtube.com/watch?v=abc",
        "source_type": "youtube",
    }
    
    provenance_id = await tracker_no_driver.track_import(import_data)
    
    assert provenance_id is not None
    assert len(provenance_id) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_track_import_validates_required_fields(tracker):
    """Test track_import validates required fields."""
    # Missing content_id
    with pytest.raises(ValueError, match="content_id is required"):
        await tracker.track_import({"source_url": "https://example.com"})
    
    # Missing source_url
    with pytest.raises(ValueError, match="source_url is required"):
        await tracker.track_import({"content_id": "content123"})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_track_export_creates_export_node(tracker, mock_neo4j_driver):
    """Test track_export creates Export node and relationships."""
    export_data = {
        "export_id": "export123",
        "source_ids": ["src1", "src2"],
        "export_type": "podcast",
        "scene_attributions": [
            {"scene_index": 0, "source_ids": ["src1"]},
            {"scene_index": 1, "source_ids": ["src2"]},
        ],
        "ai_models_used": ["gpt-4", "whisper-1"],
        "exported_at": "2025-10-13T10:30:00",
    }
    
    # Mock session
    session_context = mock_neo4j_driver.session.return_value
    session = await session_context.__aenter__()
    
    # We need the actual provenance_id that will be generated
    # The function generates a UUID, so we just verify it's returned
    provenance_id = await tracker.track_export(export_data)
    
    assert provenance_id is not None
    assert len(provenance_id) > 0
    assert session.run.called
    
    # Should have multiple queries (export, sources, scenes, models)
    assert session.run.call_count >= 4


@pytest.mark.unit
@pytest.mark.asyncio
async def test_track_export_links_to_sources(tracker, mock_neo4j_driver):
    """Test track_export links to source content."""
    export_data = {
        "export_id": "export123",
        "source_ids": ["src1", "src2"],
        "export_type": "video",
    }
    
    session_context = mock_neo4j_driver.session.return_value
    session = await session_context.__aenter__()
    result = AsyncMock()
    result.single.return_value = {"provenance_id": "prov456"}
    session.run.return_value = result
    
    await tracker.track_export(export_data)
    
    # Check for GENERATED_FROM relationship creation
    calls = session.run.call_args_list
    generated_from_calls = [
        call for call in calls
        if "GENERATED_FROM" in str(call)
    ]
    assert len(generated_from_calls) == 2  # One for each source


@pytest.mark.unit
@pytest.mark.asyncio
async def test_track_export_tracks_scene_attributions(tracker, mock_neo4j_driver):
    """Test track_export creates Scene nodes."""
    export_data = {
        "export_id": "export123",
        "source_ids": ["src1"],
        "scene_attributions": [
            {"scene_index": 0, "source_ids": ["src1"]},
            {"scene_index": 1, "source_ids": ["src1"]},
            {"scene_index": 2, "source_ids": ["src1"]},
        ],
    }
    
    session_context = mock_neo4j_driver.session.return_value
    session = await session_context.__aenter__()
    result = AsyncMock()
    result.single.return_value = {"provenance_id": "prov456"}
    session.run.return_value = result
    
    await tracker.track_export(export_data)
    
    # Check for Scene node creation
    calls = session.run.call_args_list
    scene_calls = [
        call for call in calls
        if "Scene" in str(call) and "HAS_SCENE" in str(call)
    ]
    assert len(scene_calls) == 3  # One for each scene


@pytest.mark.unit
@pytest.mark.asyncio
async def test_track_export_tracks_ai_models(tracker, mock_neo4j_driver):
    """Test track_export creates AIModel nodes."""
    export_data = {
        "export_id": "export123",
        "source_ids": ["src1"],
        "ai_models_used": ["gpt-4", "dall-e-3", "whisper-1"],
    }
    
    session_context = mock_neo4j_driver.session.return_value
    session = await session_context.__aenter__()
    result = AsyncMock()
    result.single.return_value = {"provenance_id": "prov456"}
    session.run.return_value = result
    
    await tracker.track_export(export_data)
    
    # Check for AIModel node creation
    calls = session.run.call_args_list
    model_calls = [
        call for call in calls
        if "AIModel" in str(call) and "GENERATED_BY" in str(call)
    ]
    assert len(model_calls) == 3  # One for each model


@pytest.mark.unit
@pytest.mark.asyncio
async def test_track_export_validates_required_fields(tracker):
    """Test track_export validates required fields."""
    # Missing export_id
    with pytest.raises(ValueError, match="export_id is required"):
        await tracker.track_export({"source_ids": ["src1"]})
    
    # Missing source_ids
    with pytest.raises(ValueError, match="source_ids is required"):
        await tracker.track_export({"export_id": "export123"})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_genealogy_returns_full_lineage(tracker, mock_neo4j_driver):
    """Test get_genealogy returns sources, ancestors, derivatives."""
    session_context = mock_neo4j_driver.session.return_value
    session = await session_context.__aenter__()
    result = AsyncMock()
    
    # Mock genealogy data
    mock_record = {
        "c": {"content_id": "content123"},
        "sources": [{"url": "https://youtube.com/abc", "type": "youtube"}],
        "ancestors": [{"content_id": "parent123"}],
        "derivatives": [{"content_id": "child123"}],
    }
    result.single.return_value = mock_record
    session.run.return_value = result
    
    genealogy = await tracker.get_genealogy("content123")
    
    assert genealogy["content_id"] == "content123"
    assert len(genealogy["sources"]) == 1
    assert genealogy["sources"][0]["url"] == "https://youtube.com/abc"
    assert len(genealogy["ancestors"]) == 1
    assert len(genealogy["derivatives"]) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_genealogy_without_driver(tracker_no_driver):
    """Test get_genealogy works without Neo4j driver."""
    genealogy = await tracker_no_driver.get_genealogy("content123")
    
    assert genealogy["content_id"] == "content123"
    assert genealogy["sources"] == []
    assert genealogy["ancestors"] == []
    assert genealogy["derivatives"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_genealogy_handles_no_results(tracker, mock_neo4j_driver):
    """Test get_genealogy handles content not found."""
    session_context = mock_neo4j_driver.session.return_value
    session = await session_context.__aenter__()
    result = AsyncMock()
    result.single.return_value = None
    session.run.return_value = result
    
    genealogy = await tracker.get_genealogy("nonexistent")
    
    assert genealogy["content_id"] == "nonexistent"
    assert genealogy["sources"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_attribution_text_markdown(tracker):
    """Test get_attribution_text generates markdown."""
    # Mock genealogy data
    with patch.object(tracker, 'get_genealogy') as mock_genealogy:
        mock_genealogy.return_value = {
            "content_id": "content123",
            "sources": [
                {"url": "https://youtube.com/abc", "type": "youtube"},
                {"url": "https://example.com/paper", "type": "pdf"},
            ],
            "ancestors": [
                {"content_id": "parent123"},
            ],
            "derivatives": [],
        }
        
        attribution = await tracker.get_attribution_text("content123", format="markdown")
        
        assert "## Content Attribution" in attribution
        assert "### Original Sources" in attribution
        assert "[Youtube](https://youtube.com/abc)" in attribution
        assert "[Pdf](https://example.com/paper)" in attribution
        assert "### Derived From" in attribution
        assert "`parent123`" in attribution


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_attribution_text_plain(tracker):
    """Test get_attribution_text generates plain text."""
    with patch.object(tracker, 'get_genealogy') as mock_genealogy:
        mock_genealogy.return_value = {
            "content_id": "content123",
            "sources": [{"url": "https://youtube.com/abc", "type": "youtube"}],
            "ancestors": [],
            "derivatives": [],
        }
        
        attribution = await tracker.get_attribution_text("content123", format="plain")
        
        assert "Content Attribution:" in attribution
        assert "Original Sources:" in attribution
        assert "https://youtube.com/abc" in attribution


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_attribution_text_empty(tracker):
    """Test get_attribution_text returns empty for no sources."""
    with patch.object(tracker, 'get_genealogy') as mock_genealogy:
        mock_genealogy.return_value = {
            "content_id": "content123",
            "sources": [],
            "ancestors": [],
            "derivatives": [],
        }
        
        attribution = await tracker.get_attribution_text("content123")
        
        assert attribution == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_license_compliance_compliant(tracker):
    """Test check_license_compliance for compliant licenses."""
    with patch.object(tracker, 'get_genealogy') as mock_genealogy:
        mock_genealogy.return_value = {
            "content_id": "content123",
            "sources": [
                {"url": "https://example.com/1", "license": "CC-BY"},
                {"url": "https://example.com/2", "license": "CC0"},
            ],
            "ancestors": [],
            "derivatives": [],
        }
        
        compliance = await tracker.check_license_compliance("content123", "CC-BY")
        
        assert compliance["compliant"] is True
        assert len(compliance["conflicts"]) == 0
        assert "compatible" in compliance["recommendation"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_license_compliance_conflicts(tracker):
    """Test check_license_compliance detects conflicts."""
    with patch.object(tracker, 'get_genealogy') as mock_genealogy:
        mock_genealogy.return_value = {
            "content_id": "content123",
            "sources": [
                {"url": "https://example.com/1", "license": "CC-BY"},
                {"url": "https://example.com/2", "license": "CC-BY-NC"},
            ],
            "ancestors": [],
            "derivatives": [],
        }
        
        compliance = await tracker.check_license_compliance("content123", "commercial")
        
        assert compliance["compliant"] is False
        assert len(compliance["conflicts"]) == 1
        assert compliance["conflicts"][0]["license"] == "CC-BY-NC"
        assert "Review" in compliance["recommendation"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_impact_metrics_calculates_reach(tracker, mock_neo4j_driver):
    """Test get_impact_metrics calculates derivative and citation counts."""
    session_context = mock_neo4j_driver.session.return_value
    session = await session_context.__aenter__()
    result = AsyncMock()
    mock_record = {
        "derivative_count": 5,
        "citation_count": 3,
    }
    result.single.return_value = mock_record
    session.run.return_value = result
    
    metrics = await tracker.get_impact_metrics("content123")
    
    assert metrics["content_id"] == "content123"
    assert metrics["derivative_count"] == 5
    assert metrics["citation_count"] == 3
    assert metrics["total_reach"] == 8


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_impact_metrics_without_driver(tracker_no_driver):
    """Test get_impact_metrics works without Neo4j driver."""
    metrics = await tracker_no_driver.get_impact_metrics("content123")
    
    assert metrics["content_id"] == "content123"
    assert metrics["derivative_count"] == 0
    assert metrics["citation_count"] == 0
    assert metrics["total_reach"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_citation_network_returns_graph(tracker, mock_neo4j_driver):
    """Test get_citation_network returns nodes and edges."""
    session_context = mock_neo4j_driver.session.return_value
    session = await session_context.__aenter__()
    result = AsyncMock()
    mock_record = {
        "nodes": [
            {"content_id": "content123"},
            {"content_id": "related456"},
        ],
        "edges": [
            {
                "source": "content123",
                "target": "related456",
                "type": "GENERATED_FROM",
            }
        ],
    }
    result.single.return_value = mock_record
    session.run.return_value = result
    
    network = await tracker.get_citation_network("content123", depth=2)
    
    assert network["content_id"] == "content123"
    assert len(network["nodes"]) == 2
    assert len(network["edges"]) == 1
    assert network["edges"][0]["type"] == "GENERATED_FROM"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_citation_network_without_driver(tracker_no_driver):
    """Test get_citation_network works without Neo4j driver."""
    network = await tracker_no_driver.get_citation_network("content123")
    
    assert network["content_id"] == "content123"
    assert network["nodes"] == []
    assert network["edges"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_track_version_creates_relationship(tracker, mock_neo4j_driver):
    """Test track_version creates VERSION_OF relationship."""
    session_context = mock_neo4j_driver.session.return_value
    session = await session_context.__aenter__()
    result = AsyncMock()
    session.run.return_value = result
    
    version_id = await tracker.track_version(
        content_id="content_v2",
        previous_version_id="content_v1",
        changes="Updated transcript with better formatting",
    )
    
    assert version_id is not None
    assert session.run.called
    
    # Verify query contains VERSION_OF relationship
    call_args = session.run.call_args
    query = call_args[0][0]
    assert "VERSION_OF" in query
    assert "changes" in query


@pytest.mark.unit
@pytest.mark.asyncio
async def test_track_version_without_driver(tracker_no_driver):
    """Test track_version works without Neo4j driver."""
    version_id = await tracker_no_driver.track_version(
        content_id="content_v2",
        previous_version_id="content_v1",
        changes="Updated content",
    )
    
    assert version_id is not None
    assert len(version_id) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_closes_driver(tracker, mock_neo4j_driver):
    """Test close method closes Neo4j driver."""
    await tracker.close()
    
    assert mock_neo4j_driver.close.called

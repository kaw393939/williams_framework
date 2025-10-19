"""
Integration tests for video provenance tracking in Neo4j.

These tests use REAL Neo4j connections (no mocks) to verify
complete video genealogy tracking functionality.
"""

import pytest
from app.repositories.neo_repository import NeoRepository


@pytest.fixture
def neo_repo():
    """Fixture providing real Neo4j repository connection."""
    repo = NeoRepository(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="dev_password_change_in_production",
        database="neo4j"
    )
    
    yield repo
    
    # Cleanup: remove test data
    repo.clear_database()


class TestVideoProvenanceTracking:
    """Test video provenance tracking with real Neo4j."""
    
    def test_create_video_node(self, neo_repo):
        """Test creating a video node with provenance tracking."""
        video_id = "test_video_001"
        title = "Test Video: Quantum Computing"
        source_ids = ["paper_001", "paper_002"]
        parameters = {
            "backend": "kling",
            "style": "educational",
            "duration": "5min"
        }
        creator_id = "user_123"
        
        # Create video node
        result_id = neo_repo.create_video_node(
            video_id=video_id,
            title=title,
            source_ids=source_ids,
            parameters=parameters,
            creator_id=creator_id
        )
        
        assert result_id == video_id
        
        # Verify video exists in Neo4j
        query = "MATCH (v:Video {video_id: $video_id}) RETURN v"
        results = neo_repo.execute_query(query, {"video_id": video_id})
        
        assert len(results) == 1
        video = dict(results[0]["v"])
        assert video["video_id"] == video_id
        assert video["title"] == title
        assert video["status"] == "generating"
        # Parameters are stored as JSON string
        import json
        assert json.loads(video["parameters_json"]) == parameters
        
        # Verify creator link
        query = """
        MATCH (u:User {user_id: $creator_id})-[:CREATED]->(v:Video {video_id: $video_id})
        RETURN u, v
        """
        results = neo_repo.execute_query(query, {"creator_id": creator_id, "video_id": video_id})
        assert len(results) == 1
    
    def test_link_video_to_sources(self, neo_repo):
        """Test linking video to source documents."""
        video_id = "test_video_002"
        source_ids = ["paper_001", "paper_002", "paper_003"]
        
        # Create test documents first
        for doc_id in source_ids:
            query = "CREATE (d:Document {doc_id: $doc_id, title: $title})"
            neo_repo.execute_write(query, {"doc_id": doc_id, "title": f"Paper {doc_id}"})
        
        # Create video
        neo_repo.create_video_node(
            video_id=video_id,
            title="Test Video",
            source_ids=source_ids,
            parameters={}
        )
        
        # Link to sources
        neo_repo.link_video_to_sources(video_id, source_ids)
        
        # Verify GENERATED_FROM relationships
        query = """
        MATCH (v:Video {video_id: $video_id})-[:GENERATED_FROM]->(d:Document)
        RETURN collect(d.doc_id) AS source_ids
        """
        results = neo_repo.execute_query(query, {"video_id": video_id})
        
        assert len(results) == 1
        linked_sources = results[0]["source_ids"]
        assert set(linked_sources) == set(source_ids)
    
    def test_create_video_scenes_with_attribution(self, neo_repo):
        """Test creating video scenes with source attribution."""
        video_id = "test_video_003"
        
        # Create documents
        doc_ids = ["paper_001", "paper_002"]
        for doc_id in doc_ids:
            query = "CREATE (d:Document {doc_id: $doc_id})"
            neo_repo.execute_write(query, {"doc_id": doc_id})
        
        # Create video
        neo_repo.create_video_node(
            video_id=video_id,
            title="Test Video with Scenes",
            source_ids=doc_ids,
            parameters={}
        )
        
        # Create scenes with attribution
        scenes = [
            {
                "scene_num": 1,
                "text": "Scene 1: Introduction to quantum computing",
                "source_ids": ["paper_001"],
                "attribution": "Based on Smith et al. (2024)"
            },
            {
                "scene_num": 2,
                "text": "Scene 2: Qubits explained",
                "source_ids": ["paper_002"],
                "attribution": "Based on Johnson (2023)"
            },
            {
                "scene_num": 3,
                "text": "Scene 3: Applications",
                "source_ids": ["paper_001", "paper_002"],
                "attribution": "Based on Smith et al. (2024) and Johnson (2023)"
            }
        ]
        
        for scene in scenes:
            scene_id = neo_repo.create_video_scene(
                video_id=video_id,
                scene_num=scene["scene_num"],
                text=scene["text"],
                source_ids=scene["source_ids"],
                attribution_text=scene["attribution"]
            )
            assert scene_id is not None
        
        # Verify scenes exist
        query = """
        MATCH (v:Video {video_id: $video_id})-[:HAS_SCENE]->(s:VideoScene)
        RETURN s ORDER BY s.scene_num
        """
        results = neo_repo.execute_query(query, {"video_id": video_id})
        
        assert len(results) == 3
        
        for i, result in enumerate(results):
            scene = dict(result["s"])
            assert scene["scene_num"] == scenes[i]["scene_num"]
            assert scene["text"] == scenes[i]["text"]
            assert scene["attribution"] == scenes[i]["attribution"]
        
        # Verify scene-to-source relationships
        query = """
        MATCH (s:VideoScene {scene_num: 1})-[:SOURCED_FROM]->(d:Document)
        RETURN collect(d.doc_id) AS source_ids
        """
        results = neo_repo.execute_query(query, {})
        assert set(results[0]["source_ids"]) == {"paper_001"}
    
    def test_track_ai_model_usage(self, neo_repo):
        """Test tracking AI model usage."""
        video_id = "test_video_004"
        
        # Create video
        neo_repo.create_video_node(
            video_id=video_id,
            title="Test Video",
            source_ids=[],
            parameters={}
        )
        
        # Track AI model
        neo_repo.track_ai_model_usage(
            video_id=video_id,
            model_name="kling",
            model_version="1.5",
            provider="Kuaishou"
        )
        
        # Verify AI model node and relationship
        query = """
        MATCH (v:Video {video_id: $video_id})-[:GENERATED_BY]->(m:AIModel)
        RETURN m
        """
        results = neo_repo.execute_query(query, {"video_id": video_id})
        
        assert len(results) == 1
        model = dict(results[0]["m"])
        assert model["name"] == "kling"
        assert model["version"] == "1.5"
        assert model["provider"] == "Kuaishou"
    
    def test_finalize_video_provenance(self, neo_repo):
        """Test finalizing video provenance with metadata."""
        video_id = "test_video_005"
        
        # Create video
        neo_repo.create_video_node(
            video_id=video_id,
            title="Test Video",
            source_ids=[],
            parameters={}
        )
        
        # Finalize with metadata
        neo_repo.finalize_video_provenance(
            video_id=video_id,
            duration=180.5,
            file_size=15_000_000,
            artifact_id="artifact_123"
        )
        
        # Verify updates
        query = "MATCH (v:Video {video_id: $video_id}) RETURN v"
        results = neo_repo.execute_query(query, {"video_id": video_id})
        
        assert len(results) == 1
        video = dict(results[0]["v"])
        assert video["status"] == "completed"
        assert video["duration"] == 180.5
        assert video["file_size"] == 15_000_000
        assert video["artifact_id"] == "artifact_123"
        assert video["completed_at"] is not None
    
    def test_get_video_genealogy_complete(self, neo_repo):
        """Test retrieving complete video genealogy."""
        video_id = "test_video_006"
        
        # Create complete provenance graph
        # 1. Create documents
        doc_ids = ["paper_001", "paper_002"]
        for doc_id in doc_ids:
            query = "CREATE (d:Document {doc_id: $doc_id, title: $title})"
            neo_repo.execute_write(query, {"doc_id": doc_id, "title": f"Paper {doc_id}"})
        
        # 2. Create video
        neo_repo.create_video_node(
            video_id=video_id,
            title="Complete Genealogy Test",
            source_ids=doc_ids,
            parameters={"backend": "kling"},
            creator_id="user_123"
        )
        
        # 3. Link to sources
        neo_repo.link_video_to_sources(video_id, doc_ids)
        
        # 4. Create scenes
        neo_repo.create_video_scene(
            video_id=video_id,
            scene_num=1,
            text="Scene 1 content",
            source_ids=["paper_001"],
            attribution_text="Based on Paper 1"
        )
        
        neo_repo.create_video_scene(
            video_id=video_id,
            scene_num=2,
            text="Scene 2 content",
            source_ids=["paper_002"],
            attribution_text="Based on Paper 2"
        )
        
        # 5. Track AI model
        neo_repo.track_ai_model_usage(
            video_id=video_id,
            model_name="kling",
            model_version="1.5",
            provider="Kuaishou"
        )
        
        # 6. Finalize
        neo_repo.finalize_video_provenance(
            video_id=video_id,
            duration=120.0,
            file_size=10_000_000,
            artifact_id="artifact_456"
        )
        
        # Get complete genealogy
        genealogy = neo_repo.get_video_genealogy(video_id)
        
        # Verify all components
        assert genealogy is not None
        assert genealogy["video"]["video_id"] == video_id
        assert genealogy["video"]["status"] == "completed"
        
        # Verify sources
        assert len(genealogy["source_documents"]) == 2
        source_ids_returned = {d["doc_id"] for d in genealogy["source_documents"]}
        assert source_ids_returned == set(doc_ids)
        
        # Verify scenes
        assert len(genealogy["scenes"]) == 2
        assert genealogy["scenes"][0]["scene_num"] == 1
        assert genealogy["scenes"][1]["scene_num"] == 2
        
        # Verify AI models
        assert len(genealogy["ai_models"]) == 1
        assert genealogy["ai_models"][0]["name"] == "kling"
        
        # Verify creator
        assert genealogy["creator"] is not None
        assert genealogy["creator"]["user_id"] == "user_123"
    
    def test_get_video_impact(self, neo_repo):
        """Test retrieving video impact metrics."""
        video_id = "test_video_007"
        
        # Create video
        neo_repo.create_video_node(
            video_id=video_id,
            title="Impact Test Video",
            source_ids=[],
            parameters={}
        )
        
        # Create users who viewed/shared
        query = """
        CREATE (u1:User {user_id: 'user_001'})
        CREATE (u2:User {user_id: 'user_002'})
        CREATE (u3:User {user_id: 'user_003'})
        """
        neo_repo.execute_write(query, {})
        
        # Add views
        query = """
        MATCH (v:Video {video_id: $video_id})
        MATCH (u1:User {user_id: 'user_001'})
        MATCH (u2:User {user_id: 'user_002'})
        CREATE (u1)-[:VIEWED {timestamp: datetime()}]->(v)
        CREATE (u2)-[:VIEWED {timestamp: datetime()}]->(v)
        """
        neo_repo.execute_write(query, {"video_id": video_id})
        
        # Add shares
        query = """
        MATCH (v:Video {video_id: $video_id})
        MATCH (u3:User {user_id: 'user_003'})
        CREATE (u3)-[:SHARED {timestamp: datetime()}]->(v)
        """
        neo_repo.execute_write(query, {"video_id": video_id})
        
        # Get impact
        impact = neo_repo.get_video_impact(video_id)
        
        assert impact["video_id"] == video_id
        assert impact["view_count"] == 2
        assert impact["share_count"] == 1
        assert impact["derivative_count"] == 0
        assert impact["citation_count"] == 0
    
    def test_get_generated_content_from_document(self, neo_repo):
        """Test getting all content generated from a document."""
        doc_id = "paper_001"
        
        # Create document
        query = "CREATE (d:Document {doc_id: $doc_id, title: 'Source Paper'})"
        neo_repo.execute_write(query, {"doc_id": doc_id})
        
        # Create multiple videos from this document
        for i in range(3):
            video_id = f"test_video_00{i+8}"
            neo_repo.create_video_node(
                video_id=video_id,
                title=f"Video {i+1}",
                source_ids=[doc_id],
                parameters={}
            )
            neo_repo.link_video_to_sources(video_id, [doc_id])
        
        # Get generated content
        content = neo_repo.get_generated_content_from_document(doc_id)
        
        assert len(content["videos"]) == 3
        video_ids = {v["video_id"] for v in content["videos"]}
        assert video_ids == {"test_video_008", "test_video_009", "test_video_0010"}

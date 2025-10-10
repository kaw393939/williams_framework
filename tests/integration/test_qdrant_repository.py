"""
Integration tests for Qdrant Repository.

Tests use a REAL Qdrant instance running in Docker (NO MOCKS).
Following TDD methodology: RED-GREEN-REFACTOR.
"""
import pytest
from uuid import uuid4
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.repositories.qdrant_repository import QdrantRepository
from app.core.config import settings


@pytest.fixture
def qdrant_client():
    """Create a real Qdrant client for testing."""
    client = QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port
    )
    yield client
    # Cleanup: delete test collections after each test
    try:
        collections = client.get_collections().collections
        for collection in collections:
            if collection.name.startswith("test_"):
                client.delete_collection(collection.name)
    except Exception:
        pass


@pytest.fixture
def qdrant_repo(qdrant_client):
    """Create a QdrantRepository instance with a test collection."""
    test_collection_name = f"test_{uuid4().hex[:8]}"
    repo = QdrantRepository(
        client=qdrant_client,
        collection_name=test_collection_name,
        vector_size=384  # Standard sentence-transformer size
    )
    yield repo
    # Cleanup handled by qdrant_client fixture


class TestQdrantRepositoryInitialization:
    """Test repository initialization and collection creation."""
    
    def test_repository_creates_collection_if_not_exists(self, qdrant_client):
        """Repository should create collection on initialization if it doesn't exist."""
        test_collection_name = f"test_{uuid4().hex[:8]}"
        
        # Verify collection doesn't exist
        collections = qdrant_client.get_collections().collections
        collection_names = [c.name for c in collections]
        assert test_collection_name not in collection_names
        
        # Create repository - should create collection
        repo = QdrantRepository(
            client=qdrant_client,
            collection_name=test_collection_name,
            vector_size=384
        )
        
        # Verify collection was created
        collections = qdrant_client.get_collections().collections
        collection_names = [c.name for c in collections]
        assert test_collection_name in collection_names
        
        # Cleanup
        qdrant_client.delete_collection(test_collection_name)
    
    def test_repository_reuses_existing_collection(self, qdrant_client):
        """Repository should reuse existing collection instead of recreating."""
        test_collection_name = f"test_{uuid4().hex[:8]}"
        
        # Create collection manually
        qdrant_client.create_collection(
            collection_name=test_collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        
        # Create repository - should not fail
        repo = QdrantRepository(
            client=qdrant_client,
            collection_name=test_collection_name,
            vector_size=384
        )
        
        # Verify collection still exists with same config
        collection_info = qdrant_client.get_collection(test_collection_name)
        assert collection_info.config.params.vectors.size == 384
        
        # Cleanup
        qdrant_client.delete_collection(test_collection_name)


class TestQdrantRepositoryAdd:
    """Test adding embeddings to the repository."""
    
    def test_add_single_embedding(self, qdrant_repo):
        """Should add a single embedding with metadata."""
        content_id = str(uuid4())
        vector = [0.1] * 384  # Dummy embedding
        metadata = {
            "url": "https://example.com/article",
            "title": "Test Article",
            "source_type": "web",
            "quality_score": 8.5
        }
        
        # Add embedding
        qdrant_repo.add(
            content_id=content_id,
            vector=vector,
            metadata=metadata
        )
        
        # Verify it was added
        result = qdrant_repo.get_by_id(content_id)
        assert result is not None
        assert result["id"] == content_id
        assert result["metadata"]["url"] == "https://example.com/article"
        assert result["metadata"]["title"] == "Test Article"
        assert result["metadata"]["quality_score"] == 8.5
    
    def test_add_multiple_embeddings_batch(self, qdrant_repo):
        """Should add multiple embeddings in a batch."""
        embeddings = []
        for i in range(5):
            embeddings.append({
                "content_id": str(uuid4()),
                "vector": [0.1 * (i + 1)] * 384,
                "metadata": {
                    "url": f"https://example.com/article{i}",
                    "title": f"Article {i}",
                    "quality_score": 7.0 + i * 0.5
                }
            })
        
        # Add batch
        qdrant_repo.add_batch(embeddings)
        
        # Verify all were added
        for emb in embeddings:
            result = qdrant_repo.get_by_id(emb["content_id"])
            assert result is not None
            assert result["metadata"]["url"] == emb["metadata"]["url"]
    
    def test_add_with_empty_vector_raises_error(self, qdrant_repo):
        """Should raise ValueError when vector is empty."""
        with pytest.raises(ValueError, match="Vector cannot be empty"):
            qdrant_repo.add(
                content_id=str(uuid4()),
                vector=[],
                metadata={}
            )
    
    def test_add_with_wrong_vector_size_raises_error(self, qdrant_repo):
        """Should raise ValueError when vector size doesn't match collection."""
        with pytest.raises(ValueError, match="Vector size"):
            qdrant_repo.add(
                content_id=str(uuid4()),
                vector=[0.1] * 128,  # Wrong size! Should be 384
                metadata={}
            )


class TestQdrantRepositoryQuery:
    """Test querying embeddings by similarity."""
    
    def test_query_returns_similar_embeddings(self, qdrant_repo):
        """Should return embeddings similar to query vector."""
        # Add some embeddings with MORE distinct vectors
        base_vector = [0.8] * 384
        similar_vector = [0.75] * 384
        different_vector = [-0.5] * 384  # Very different!
        
        id_base = str(uuid4())
        id_similar = str(uuid4())
        id_different = str(uuid4())
        
        qdrant_repo.add(id_base, base_vector, {"label": "base"})
        qdrant_repo.add(id_similar, similar_vector, {"label": "similar"})
        qdrant_repo.add(id_different, different_vector, {"label": "different"})
        
        # Query with vector similar to base and similar
        query_vector = [0.8] * 384
        results = qdrant_repo.query(query_vector, limit=3)
        
        # Should return all 3, but base/similar should rank higher than different
        assert len(results) == 3
        result_labels = [r["metadata"]["label"] for r in results]
        # Different vector should have lower score/be last
        assert result_labels[-1] == "different"
        # Base and similar should be in top 2
        assert set(result_labels[:2]) == {"base", "similar"}
    
    def test_query_with_metadata_filter(self, qdrant_repo):
        """Should filter results by metadata."""
        # Add embeddings with different quality scores
        for i in range(5):
            qdrant_repo.add(
                content_id=str(uuid4()),
                vector=[0.5] * 384,
                metadata={
                    "url": f"https://example.com/{i}",
                    "quality_score": 6.0 + i
                }
            )
        
        # Query with filter for high quality only
        query_vector = [0.5] * 384
        results = qdrant_repo.query(
            query_vector,
            limit=10,
            filter_conditions={"quality_score": {"$gte": 8.0}}
        )
        
        # Should only return high quality results
        assert len(results) == 3  # quality_score >= 8.0: items 2, 3, 4
        for result in results:
            assert result["metadata"]["quality_score"] >= 8.0
    
    def test_query_with_limit(self, qdrant_repo):
        """Should respect limit parameter."""
        # Add 10 embeddings
        for i in range(10):
            qdrant_repo.add(
                content_id=str(uuid4()),
                vector=[0.5] * 384,
                metadata={"index": i}
            )
        
        # Query with limit=3
        results = qdrant_repo.query([0.5] * 384, limit=3)
        assert len(results) == 3
    
    def test_query_returns_scores(self, qdrant_repo):
        """Should return similarity scores with results."""
        id1 = str(uuid4())
        qdrant_repo.add(id1, [0.5] * 384, {"label": "test"})
        
        results = qdrant_repo.query([0.5] * 384, limit=1)
        assert len(results) == 1
        assert "score" in results[0]
        assert 0.0 <= results[0]["score"] <= 1.0


class TestQdrantRepositoryDelete:
    """Test deleting embeddings from the repository."""
    
    def test_delete_by_id(self, qdrant_repo):
        """Should delete embedding by content ID."""
        content_id = str(uuid4())
        qdrant_repo.add(content_id, [0.5] * 384, {"label": "test"})
        
        # Verify it exists
        result = qdrant_repo.get_by_id(content_id)
        assert result is not None
        
        # Delete it
        qdrant_repo.delete(content_id)
        
        # Verify it's gone
        result = qdrant_repo.get_by_id(content_id)
        assert result is None
    
    def test_delete_nonexistent_id_does_not_raise(self, qdrant_repo):
        """Deleting non-existent ID should not raise an error."""
        # Should not raise
        qdrant_repo.delete(str(uuid4()))
    
    def test_delete_batch(self, qdrant_repo):
        """Should delete multiple embeddings at once."""
        ids = [str(uuid4()) for _ in range(5)]
        for id in ids:
            qdrant_repo.add(id, [0.5] * 384, {"label": "test"})
        
        # Delete batch
        qdrant_repo.delete_batch(ids[:3])
        
        # Verify first 3 deleted, last 2 remain
        for id in ids[:3]:
            assert qdrant_repo.get_by_id(id) is None
        for id in ids[3:]:
            assert qdrant_repo.get_by_id(id) is not None


class TestQdrantRepositoryUpdate:
    """Test updating embeddings metadata."""
    
    def test_update_metadata(self, qdrant_repo):
        """Should update metadata without changing vector."""
        content_id = str(uuid4())
        original_vector = [0.5] * 384
        qdrant_repo.add(
            content_id,
            original_vector,
            {"quality_score": 7.0, "title": "Original"}
        )
        
        # Update metadata
        qdrant_repo.update_metadata(
            content_id,
            {"quality_score": 9.0, "title": "Updated"}
        )
        
        # Verify metadata updated
        result = qdrant_repo.get_by_id(content_id)
        assert result["metadata"]["quality_score"] == 9.0
        assert result["metadata"]["title"] == "Updated"


class TestQdrantRepositoryCount:
    """Test counting embeddings in collection."""
    
    def test_count_empty_collection(self, qdrant_repo):
        """Should return 0 for empty collection."""
        assert qdrant_repo.count() == 0
    
    def test_count_after_adding_embeddings(self, qdrant_repo):
        """Should return correct count after adding embeddings."""
        # Add 5 embeddings
        for i in range(5):
            qdrant_repo.add(str(uuid4()), [0.5] * 384, {"index": i})
        
        assert qdrant_repo.count() == 5
    
    def test_count_after_deleting(self, qdrant_repo):
        """Should return correct count after deletions."""
        ids = [str(uuid4()) for _ in range(5)]
        for id in ids:
            qdrant_repo.add(id, [0.5] * 384, {})
        
        # Delete 2
        qdrant_repo.delete_batch(ids[:2])
        
        assert qdrant_repo.count() == 3

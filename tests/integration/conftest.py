"""Shared fixtures for integration tests."""
import pytest


def is_neo4j_available() -> bool:
    """Check if Neo4j is running on localhost:7687."""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 7687))
        sock.close()
        return result == 0
    except:
        return False


NEO4J_AVAILABLE = is_neo4j_available()

# Mark all tests that need Neo4j
pytestmark = pytest.mark.skipif(
    not NEO4J_AVAILABLE,
    reason="Neo4j not available (start with: docker-compose up -d neo4j)"
)


@pytest.fixture
def neo_repo():
    """Fixture providing NeoRepository instance with cleanup."""
    from app.repositories.neo_repository import NeoRepository
    
    repo = NeoRepository()
    
    # Verify connection
    assert repo.verify_connectivity(), "Failed to connect to Neo4j"
    
    yield repo
    
    # Cleanup: Clear test data
    try:
        repo.clear_database()
    except Exception as e:
        print(f"Warning: Could not clear database: {e}")
    finally:
        repo.close()

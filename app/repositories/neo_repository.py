"""
Neo4j Repository for Knowledge Graph operations.

Handles connections, Cypher queries, and vector index management.
"""

import logging
from typing import List, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)


class NeoRepository:
    """
    Repository for Neo4j knowledge graph operations.
    
    Manages:
    - Connection lifecycle
    - Cypher query execution
    - Dynamic vector index creation
    - Graph operations (nodes, relationships)
    """
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: Optional[str] = None,
        database: str = "neo4j"
    ):
        """
        Initialize Neo4j repository.
        
        Args:
            uri: Neo4j connection URI
            user: Username
            password: Password (defaults to NEO4J_PASSWORD env var)
            database: Database name
        """
        try:
            from neo4j import GraphDatabase
        except ImportError:
            raise ImportError(
                "neo4j package not installed. "
                "Install with: poetry add neo4j"
            )
        
        if password is None:
            password = os.getenv("NEO4J_PASSWORD", "dev_password_change_in_production")
        
        self.uri = uri
        self.user = user
        self.database = database
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        
        logger.info(f"Connected to Neo4j at {uri}")
    
    def close(self):
        """Close the driver connection."""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def verify_connectivity(self) -> bool:
        """
        Verify connection to Neo4j.
        
        Returns:
            True if connected successfully
            
        Raises:
            RuntimeError: If connection fails
        """
        try:
            with self._driver.session(database=self.database) as session:
                result = session.run("RETURN 1 AS num")
                record = result.single()
                return record["num"] == 1
        except Exception as e:
            logger.error(f"Neo4j connectivity check failed: {e}")
            raise RuntimeError(f"Failed to connect to Neo4j: {e}")
    
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        parameters = parameters or {}
        
        with self._driver.session(database=self.database) as session:
            result = session.run(query, parameters)
            return [dict(record) for record in result]
    
    def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a write query (CREATE, MERGE, etc.).
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records
        """
        parameters = parameters or {}
        
        def _write_tx(tx):
            result = tx.run(query, parameters)
            return [dict(record) for record in result]
        
        with self._driver.session(database=self.database) as session:
            return session.execute_write(_write_tx)
    
    def create_vector_index(
        self,
        index_name: str,
        label: str,
        property_name: str,
        dimensions: int,
        similarity_function: str = "cosine"
    ) -> bool:
        """
        Create a vector index for similarity search.
        
        Args:
            index_name: Name for the index
            label: Node label to index
            property_name: Property containing embedding vector
            dimensions: Vector dimensions (384, 768, 1536, etc.)
            similarity_function: 'cosine' or 'euclidean'
            
        Returns:
            True if created successfully
        """
        # Drop existing index if it exists
        try:
            drop_query = f"DROP INDEX {index_name} IF EXISTS"
            self.execute_write(drop_query)
        except Exception as e:
            logger.debug(f"No existing index to drop: {e}")
        
        # Create new vector index
        create_query = f"""
        CREATE VECTOR INDEX {index_name} IF NOT EXISTS
        FOR (n:{label})
        ON n.{property_name}
        OPTIONS {{
          indexConfig: {{
            `vector.dimensions`: {dimensions},
            `vector.similarity_function`: '{similarity_function}'
          }}
        }}
        """
        
        try:
            self.execute_write(create_query)
            logger.info(
                f"Created vector index '{index_name}' for {label}.{property_name} "
                f"({dimensions} dims, {similarity_function})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create vector index: {e}")
            raise RuntimeError(f"Vector index creation failed: {e}")
    
    def vector_search(
        self,
        index_name: str,
        query_vector: List[float],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.
        
        Args:
            index_name: Name of vector index
            query_vector: Query embedding vector
            limit: Number of results to return
            
        Returns:
            List of similar nodes with scores
        """
        query = f"""
        CALL db.index.vector.queryNodes($index_name, $limit, $query_vector)
        YIELD node, score
        RETURN node, score
        ORDER BY score DESC
        """
        
        parameters = {
            "index_name": index_name,
            "limit": limit,
            "query_vector": query_vector
        }
        
        return self.execute_query(query, parameters)
    
    def create_node(
        self,
        label: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a node with properties.
        
        Args:
            label: Node label
            properties: Node properties
            
        Returns:
            Created node
        """
        query = f"""
        CREATE (n:{label} $props)
        RETURN n
        """
        
        result = self.execute_write(query, {"props": properties})
        return result[0]["n"] if result else {}
    
    def get_node_count(self, label: Optional[str] = None) -> int:
        """
        Get count of nodes.
        
        Args:
            label: Optional node label to filter by
            
        Returns:
            Number of nodes
        """
        if label:
            query = f"MATCH (n:{label}) RETURN count(n) as count"
        else:
            query = "MATCH (n) RETURN count(n) as count"
        
        result = self.execute_query(query)
        return result[0]["count"] if result else 0
    
    def clear_database(self):
        """Clear all nodes and relationships (USE WITH CAUTION!)."""
        query = "MATCH (n) DETACH DELETE n"
        self.execute_write(query)
        logger.warning("Database cleared!")

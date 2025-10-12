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
    
    # ========== SCHEMA INITIALIZATION ==========
    
    def initialize_schema(self):
        """
        Initialize Neo4j schema with constraints and indexes.
        
        Creates:
        - Uniqueness constraints on IDs
        - Indexes for common queries
        - Node labels: Document, Chunk, Mention, Entity
        """
        constraints = [
            # Document constraints
            "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT document_url_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.url IS UNIQUE",
            
            # Chunk constraints
            "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE",
            
            # Entity constraints
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            
            # Mention constraints
            "CREATE CONSTRAINT mention_id_unique IF NOT EXISTS FOR (m:Mention) REQUIRE m.id IS UNIQUE",
        ]
        
        indexes = [
            # Performance indexes
            "CREATE INDEX document_created_idx IF NOT EXISTS FOR (d:Document) ON (d.created_at)",
            "CREATE INDEX chunk_offset_idx IF NOT EXISTS FOR (c:Chunk) ON (c.start_offset)",
            "CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.entity_type)",
            "CREATE INDEX entity_text_idx IF NOT EXISTS FOR (e:Entity) ON (e.text)",
        ]
        
        # Create constraints
        for constraint in constraints:
            try:
                self.execute_write(constraint)
                logger.info(f"Created constraint: {constraint[:60]}...")
            except Exception as e:
                logger.debug(f"Constraint may already exist: {e}")
        
        # Create indexes
        for index in indexes:
            try:
                self.execute_write(index)
                logger.info(f"Created index: {index[:60]}...")
            except Exception as e:
                logger.debug(f"Index may already exist: {e}")
        
        logger.info("Schema initialization complete")
    
    # ========== DOCUMENT OPERATIONS ==========
    
    def create_document(
        self,
        doc_id: str,
        url: str,
        title: str,
        content_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create or update a Document node.
        
        Args:
            doc_id: Deterministic document ID (SHA256 of URL)
            url: Document URL
            title: Document title
            content_hash: Optional content hash for version tracking
            metadata: Additional metadata (author, published_date, etc.)
            
        Returns:
            Created/updated document node
        """
        import json
        
        # Convert metadata dict to JSON string (Neo4j doesn't support nested maps)
        metadata_json = json.dumps(metadata) if metadata else "{}"
        
        query = """
        MERGE (d:Document {id: $doc_id})
        ON CREATE SET
            d.url = $url,
            d.title = $title,
            d.content_hash = $content_hash,
            d.created_at = datetime(),
            d.metadata = $metadata_json
        ON MATCH SET
            d.url = $url,
            d.title = $title,
            d.content_hash = $content_hash,
            d.updated_at = datetime(),
            d.metadata = $metadata_json
        RETURN d
        """
        
        parameters = {
            "doc_id": doc_id,
            "url": url,
            "title": title,
            "content_hash": content_hash,
            "metadata_json": metadata_json
        }
        
        result = self.execute_write(query, parameters)
        if result:
            doc_node = result[0]["d"]
            # Convert Node to dict
            doc = dict(doc_node)
            # Parse metadata JSON back to dict for convenience
            if "metadata" in doc and doc["metadata"]:
                doc["metadata"] = json.loads(doc["metadata"])
            return doc
        return {}
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        import json
        
        query = "MATCH (d:Document {id: $doc_id}) RETURN d"
        result = self.execute_query(query, {"doc_id": doc_id})
        
        if result:
            doc_node = result[0]["d"]
            # Convert Node to dict
            doc = dict(doc_node)
            # Parse metadata JSON back to dict
            if "metadata" in doc and doc["metadata"]:
                doc["metadata"] = json.loads(doc["metadata"])
            return doc
        return None
    
    # ========== CHUNK OPERATIONS ==========
    
    def create_chunk(
        self,
        chunk_id: str,
        doc_id: str,
        text: str,
        start_offset: int,
        end_offset: int,
        page_number: Optional[int] = None,
        heading: Optional[str] = None,
        embedding: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Create a Chunk node and link to Document.
        
        Args:
            chunk_id: Deterministic chunk ID (doc_id + offset)
            doc_id: Parent document ID
            text: Chunk text content
            start_offset: Byte offset where chunk starts
            end_offset: Byte offset where chunk ends
            page_number: Optional page number (for PDFs)
            heading: Optional heading context (for markdown)
            embedding: Optional embedding vector
            
        Returns:
            Created chunk node
        """
        query = """
        MATCH (d:Document {id: $doc_id})
        MERGE (c:Chunk {id: $chunk_id})
        ON CREATE SET
            c.text = $text,
            c.start_offset = $start_offset,
            c.end_offset = $end_offset,
            c.page_number = $page_number,
            c.heading = $heading,
            c.embedding = $embedding,
            c.created_at = datetime()
        MERGE (c)-[:PART_OF]->(d)
        RETURN c
        """
        
        parameters = {
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "text": text,
            "start_offset": start_offset,
            "end_offset": end_offset,
            "page_number": page_number,
            "heading": heading,
            "embedding": embedding
        }
        
        result = self.execute_write(query, parameters)
        return result[0]["c"] if result else {}
    
    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get chunk by ID."""
        query = "MATCH (c:Chunk {id: $chunk_id}) RETURN c"
        result = self.execute_query(query, {"chunk_id": chunk_id})
        return result[0]["c"] if result else None
    
    def get_document_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a document, ordered by offset."""
        query = """
        MATCH (c:Chunk)-[:PART_OF]->(d:Document {id: $doc_id})
        RETURN c
        ORDER BY c.start_offset
        """
        result = self.execute_query(query, {"doc_id": doc_id})
        return [r["c"] for r in result]
    
    # ========== ENTITY OPERATIONS ==========
    
    def create_entity(
        self,
        entity_id: str,
        text: str,
        entity_type: str,
        confidence: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create or update an Entity node.
        
        Args:
            entity_id: Deterministic entity ID (hash of text + type)
            text: Entity text (e.g., "Albert Einstein")
            entity_type: Type (PERSON, ORG, GPE, LAW, DATE, etc.)
            confidence: Optional confidence score from NER
            
        Returns:
            Created/updated entity node
        """
        query = """
        MERGE (e:Entity {id: $entity_id})
        ON CREATE SET
            e.text = $text,
            e.entity_type = $entity_type,
            e.confidence = $confidence,
            e.mention_count = 1,
            e.created_at = datetime()
        ON MATCH SET
            e.mention_count = e.mention_count + 1,
            e.updated_at = datetime()
        RETURN e
        """
        
        parameters = {
            "entity_id": entity_id,
            "text": text,
            "entity_type": entity_type,
            "confidence": confidence
        }
        
        result = self.execute_write(query, parameters)
        return result[0]["e"] if result else {}
    
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID."""
        query = "MATCH (e:Entity {id: $entity_id}) RETURN e"
        result = self.execute_query(query, {"entity_id": entity_id})
        return result[0]["e"] if result else None
    
    # ========== MENTION OPERATIONS ==========
    
    def create_mention(
        self,
        mention_id: str,
        chunk_id: str,
        entity_id: str,
        offset_in_chunk: int,
        confidence: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create a Mention node linking Chunk to Entity.
        
        A "mention" is a specific occurrence of an entity in a chunk.
        
        Args:
            mention_id: Deterministic mention ID
            chunk_id: Chunk where entity appears
            entity_id: Entity that is mentioned
            offset_in_chunk: Character offset within chunk
            confidence: Optional NER confidence score
            
        Returns:
            Created mention node
        """
        query = """
        MATCH (c:Chunk {id: $chunk_id})
        MATCH (e:Entity {id: $entity_id})
        MERGE (m:Mention {id: $mention_id})
        ON CREATE SET
            m.offset_in_chunk = $offset_in_chunk,
            m.confidence = $confidence,
            m.created_at = datetime()
        MERGE (m)-[:FOUND_IN]->(c)
        MERGE (m)-[:REFERS_TO]->(e)
        RETURN m
        """
        
        parameters = {
            "mention_id": mention_id,
            "chunk_id": chunk_id,
            "entity_id": entity_id,
            "offset_in_chunk": offset_in_chunk,
            "confidence": confidence
        }
        
        result = self.execute_write(query, parameters)
        return result[0]["m"] if result else {}
    
    def get_entity_mentions(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all mentions of an entity across all documents."""
        query = """
        MATCH (m:Mention)-[:REFERS_TO]->(e:Entity {id: $entity_id})
        MATCH (m)-[:FOUND_IN]->(c:Chunk)-[:PART_OF]->(d:Document)
        RETURN m, c, d
        ORDER BY d.created_at DESC, c.start_offset
        """
        result = self.execute_query(query, {"entity_id": entity_id})
        return result

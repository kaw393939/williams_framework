"""
Neo4j Repository for Knowledge Graph operations.

Handles connections, Cypher queries, and vector index management.
"""

import logging
import os
from typing import Any

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
        password: str | None = None,
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
        except ImportError as e:
            raise ImportError(
                "neo4j package not installed. "
                "Install with: poetry add neo4j"
            ) from e

        if password is None:
            password = os.getenv("NEO4J_PASSWORD", "dev_password_change_in_production")

        self.uri = uri
        self.user = user
        self.database = database
        # Add a small connection timeout to avoid hangs when Neo4j is unreachable
        self._driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            connection_timeout=5.0,
        )

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
            raise RuntimeError(f"Failed to connect to Neo4j: {e}") from e

    def execute_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
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
            # Add per-query timeout (seconds) to prevent long-running operations from hanging tests
            result = session.run(query, parameters, timeout=5.0)
            return [dict(record) for record in result]

    def execute_write(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
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
            result = tx.run(query, parameters, timeout=5.0)
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
            raise RuntimeError(f"Vector index creation failed: {e}") from e

    def vector_search(
        self,
        index_name: str,
        query_vector: list[float],
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Perform vector similarity search.

        Args:
            index_name: Name of vector index
            query_vector: Query embedding vector
            limit: Number of results to return

        Returns:
            List of similar nodes with scores
        """
        query = """
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
        properties: dict[str, Any]
    ) -> dict[str, Any]:
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

    def get_node_count(self, label: str | None = None) -> int:
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
        content_hash: str | None = None,
        metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
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

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
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
        page_number: int | None = None,
        heading: str | None = None,
        embedding: list[float] | None = None
    ) -> dict[str, Any]:
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

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        """Get chunk by ID with doc_id."""
        query = """
        MATCH (c:Chunk {id: $chunk_id})
        OPTIONAL MATCH (c)-[:PART_OF]->(d:Document)
        RETURN c, d.id as doc_id
        """
        result = self.execute_query(query, {"chunk_id": chunk_id})
        if result:
            chunk = dict(result[0]["c"])
            if result[0]["doc_id"]:
                chunk["doc_id"] = result[0]["doc_id"]
            return chunk
        return None

    def get_document_chunks(self, doc_id: str) -> list[dict[str, Any]]:
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
        confidence: float | None = None
    ) -> dict[str, Any]:
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

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
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
        confidence: float | None = None
    ) -> dict[str, Any]:
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

    def get_entity_mentions(self, entity_id: str) -> list[dict[str, Any]]:
        """Get all mentions of an entity across all documents."""
        query = """
        MATCH (m:Mention)-[:REFERS_TO]->(e:Entity {id: $entity_id})
        MATCH (m)-[:FOUND_IN]->(c:Chunk)-[:PART_OF]->(d:Document)
        RETURN m, c, d
        ORDER BY d.created_at DESC, c.start_offset
        """
        result = self.execute_query(query, {"entity_id": entity_id})
        return result

    # ========== COREFERENCE OPERATIONS (Sprint 6) ==========

    def create_entity_mention(
        self,
        mention_id: str,
        chunk_id: str,
        text: str,
        entity_type: str,
        start_offset: int,
        end_offset: int,
        confidence: float | None = None,
    ) -> str:
        """Create entity and mention in one operation.
        
        Helper method that creates both Entity and Mention nodes and links them.
        Used by tests and entity extraction pipeline.
        
        Args:
            mention_id: Deterministic mention ID
            chunk_id: Chunk where entity appears
            text: Entity text (e.g., "Sam Altman")
            entity_type: Entity type (PERSON, ORG, etc.)
            start_offset: Start character offset in chunk
            end_offset: End character offset in chunk
            confidence: Optional NER confidence score
            
        Returns:
            Entity ID (for linking coreferences)
        """
        from app.core.id_generator import generate_entity_id
        
        # Generate entity ID
        entity_id = generate_entity_id(text, entity_type)
        
        # Create entity node
        self.create_entity(
            entity_id=entity_id,
            text=text,
            entity_type=entity_type,
            confidence=confidence,
        )
        
        # Create mention node and link to entity and chunk
        self.create_mention(
            mention_id=mention_id,
            chunk_id=chunk_id,
            entity_id=entity_id,
            offset_in_chunk=start_offset,
            confidence=confidence,
        )
        
        return entity_id

    def create_pronoun_mention(
        self,
        mention_id: str,
        chunk_id: str,
        text: str,
        start_offset: int,
        end_offset: int,
    ) -> dict[str, Any]:
        """Create a pronoun mention node.

        Args:
            mention_id: Deterministic mention ID
            chunk_id: Chunk where pronoun appears
            text: Pronoun text (e.g., "he", "it")
            start_offset: Start character offset
            end_offset: End character offset

        Returns:
            Created mention node
        """
        query = """
        MATCH (c:Chunk {id: $chunk_id})
        MERGE (m:Mention {id: $mention_id})
        ON CREATE SET
            m.text = $text,
            m.start_offset = $start_offset,
            m.end_offset = $end_offset,
            m.mention_type = 'pronoun',
            m.created_at = datetime()
        MERGE (c)-[:CONTAINS_MENTION]->(m)
        RETURN m
        """

        parameters = {
            "mention_id": mention_id,
            "chunk_id": chunk_id,
            "text": text,
            "start_offset": start_offset,
            "end_offset": end_offset,
        }

        result = self.execute_write(query, parameters)
        return result[0]["m"] if result else {}

    def create_coref_relationship(
        self,
        source_mention_id: str,
        target_mention_id: str,
        cluster_id: str,
    ) -> bool:
        """Create COREF_WITH relationship between mentions.

        Args:
            source_mention_id: Source mention (usually pronoun)
            target_mention_id: Target mention (usually entity)
            cluster_id: Coreference cluster ID

        Returns:
            True if relationship created successfully
        """
        query = """
        MATCH (m1:Mention {id: $source_mention_id})
        MATCH (m2:Mention {id: $target_mention_id})
        MERGE (m1)-[r:COREF_WITH {cluster_id: $cluster_id}]->(m2)
        ON CREATE SET
            r.created_at = datetime(),
            r.text = m1.text
        RETURN r
        """

        parameters = {
            "source_mention_id": source_mention_id,
            "target_mention_id": target_mention_id,
            "cluster_id": cluster_id,
        }

        result = self.execute_write(query, parameters)
        return len(result) > 0

    def get_coref_chains(self, doc_id: str) -> list[dict[str, Any]]:
        """Get all coreference chains for a document.

        Args:
            doc_id: Document ID

        Returns:
            List of coref chains with structure:
            [
                {
                    "cluster_id": "abc123",
                    "mentions": [
                        {"mention_id": "...", "text": "Sam Altman", "type": "entity"},
                        {"mention_id": "...", "text": "He", "type": "pronoun"},
                    ]
                }
            ]
        """
        query = """
        MATCH (d:Document {id: $doc_id})<-[:PART_OF]-(c:Chunk)
        -[:CONTAINS_MENTION]->(m1:Mention)-[r:COREF_WITH]->(m2:Mention)
        RETURN DISTINCT
            r.cluster_id AS cluster_id,
            collect(DISTINCT {
                mention_id: m1.id,
                text: m1.text,
                type: COALESCE(m1.mention_type, 'entity')
            }) + collect(DISTINCT {
                mention_id: m2.id,
                text: m2.text,
                type: COALESCE(m2.mention_type, 'entity')
            }) AS mentions
        """

        result = self.execute_query(query, {"doc_id": doc_id})
        return result

    # ========== ENTITY LINKING OPERATIONS (Sprint 6 - Story S6-602) ==========

    def create_canonical_entity(
        self,
        entity_id: str,
        canonical_name: str,
        entity_type: str,
        aliases: list[str] | None = None,
    ) -> str:
        """Create or update a canonical Entity node for entity linking.

        This merges with existing Entity nodes created by entity extraction,
        adding canonical fields for entity linking.

        Args:
            entity_id: Deterministic entity ID
            canonical_name: Canonical name for the entity
            entity_type: Entity type (PERSON, ORG, etc.)
            aliases: List of alias names

        Returns:
            Entity ID
        """
        query = """
        MERGE (e:Entity {id: $entity_id})
        ON CREATE SET
            e.canonical_name = $canonical_name,
            e.text = $canonical_name,
            e.entity_type = $entity_type,
            e.aliases = $aliases,
            e.mention_count = 1,
            e.created_at = datetime()
        ON MATCH SET
            e.canonical_name = coalesce(e.canonical_name, $canonical_name),
            e.aliases = coalesce(e.aliases, $aliases)
        RETURN e.id as id
        """
        
        parameters = {
            "entity_id": entity_id,
            "canonical_name": canonical_name,
            "entity_type": entity_type,
            "aliases": aliases or [canonical_name],
        }
        
        result = self.execute_write(query, parameters)
        return result[0]["id"] if result else entity_id

    def link_mention_to_entity(
        self,
        mention_id: str,
        entity_id: str,
        confidence: float,
    ) -> None:
        """Link a mention to a canonical entity with LINKED_TO relationship.

        Args:
            mention_id: Mention ID
            entity_id: Canonical entity ID
            confidence: Confidence score (0.0-1.0)
        """
        query = """
        MATCH (m:Mention {id: $mention_id})
        MATCH (e:Entity {id: $entity_id})
        MERGE (m)-[r:LINKED_TO]->(e)
        ON CREATE SET
            r.confidence = $confidence,
            r.linked_at = datetime()
        """
        
        parameters = {
            "mention_id": mention_id,
            "entity_id": entity_id,
            "confidence": confidence,
        }
        
        self.execute_write(query, parameters)

    def increment_entity_mention_count(self, entity_id: str) -> None:
        """Increment the mention count for an entity.

        Args:
            entity_id: Entity ID
        """
        query = """
        MATCH (e:Entity {id: $entity_id})
        SET e.mention_count = COALESCE(e.mention_count, 0) + 1
        """
        
        self.execute_write(query, {"entity_id": entity_id})

    def add_entity_alias(self, entity_id: str, alias: str) -> None:
        """Add an alias to an entity's aliases list.

        Args:
            entity_id: Entity ID
            alias: Alias to add
        """
        query = """
        MATCH (e:Entity {id: $entity_id})
        SET e.aliases = CASE
            WHEN $alias IN COALESCE(e.aliases, []) THEN e.aliases
            ELSE COALESCE(e.aliases, []) + [$alias]
        END
        """
        
        self.execute_write(query, {"entity_id": entity_id, "alias": alias})

    def get_entities_by_type(self, entity_type: str) -> list[dict[str, Any]]:
        """Get all entities of a specific type.

        Args:
            entity_type: Entity type (PERSON, ORG, etc.)

        Returns:
            List of entity nodes
        """
        query = """
        MATCH (e:Entity {entity_type: $entity_type})
        RETURN e
        """
        
        results = self.execute_query(query, {"entity_type": entity_type})
        return [dict(result["e"]) for result in results]
    
    def get_mention_text(self, mention_id: str) -> str | None:
        """Get the text of a mention.

        Args:
            mention_id: Mention ID

        Returns:
            Mention text (from related Entity), or None if not found
        """
        query = """
        MATCH (m:Mention {id: $mention_id})-[:REFERS_TO]->(e:Entity)
        RETURN e.text as text
        """
        
        result = self.execute_query(query, {"mention_id": mention_id})
        return result[0]["text"] if result else None
    
    # ============================================================================
    # Video Provenance Methods
    # ============================================================================
    
    def create_video_node(
        self,
        video_id: str,
        title: str,
        source_ids: list[str],
        parameters: dict[str, Any],
        creator_id: str | None = None
    ) -> str:
        """
        Create a Video node in Neo4j for provenance tracking.
        
        Args:
            video_id: Unique video identifier
            title: Video title
            source_ids: List of source document IDs
            parameters: Generation parameters
            creator_id: User who created the video
            
        Returns:
            video_id
        """
        import json
        
        query = """
        CREATE (v:Video {
            video_id: $video_id,
            title: $title,
            status: 'generating',
            created_at: datetime(),
            parameters_json: $parameters_json,
            requested_sources: $source_ids
        })
        RETURN v.video_id AS video_id
        """
        
        result = self.execute_write(
            query,
            {
                "video_id": video_id,
                "title": title,
                "parameters_json": json.dumps(parameters),
                "source_ids": source_ids
            }
        )
        
        # Link to creator if provided
        if creator_id:
            self.link_video_to_creator(video_id, creator_id)
        
        return result[0]["video_id"] if result else video_id
    
    def link_video_to_creator(self, video_id: str, creator_id: str) -> None:
        """Link a video to its creator."""
        query = """
        MATCH (v:Video {video_id: $video_id})
        MERGE (u:User {user_id: $creator_id})
        CREATE (u)-[:CREATED {timestamp: datetime()}]->(v)
        """
        
        self.execute_write(query, {"video_id": video_id, "creator_id": creator_id})
    
    def link_video_to_sources(self, video_id: str, source_ids: list[str]) -> None:
        """
        Link a video to its source documents with GENERATED_FROM relationships.
        
        Args:
            video_id: Video identifier
            source_ids: List of source document IDs
        """
        query = """
        MATCH (v:Video {video_id: $video_id})
        
        WITH v
        UNWIND $source_ids AS source_id
        
        MATCH (d:Document {doc_id: source_id})
        CREATE (v)-[:GENERATED_FROM {timestamp: datetime()}]->(d)
        """
        
        self.execute_write(query, {"video_id": video_id, "source_ids": source_ids})
    
    def create_video_scene(
        self,
        video_id: str,
        scene_num: int,
        text: str,
        source_ids: list[str],
        attribution_text: str = ""
    ) -> str:
        """
        Create a VideoScene node and link it to sources.
        
        Args:
            video_id: Parent video ID
            scene_num: Scene number
            text: Scene narration text
            source_ids: Source documents used for this scene
            attribution_text: Human-readable attribution
            
        Returns:
            scene_id
        """
        scene_id = f"scene_{video_id}_{scene_num}"
        
        query = """
        MATCH (v:Video {video_id: $video_id})
        
        CREATE (s:VideoScene {
            scene_id: $scene_id,
            scene_num: $scene_num,
            text: $text,
            attribution: $attribution_text,
            created_at: datetime()
        })
        
        CREATE (v)-[:HAS_SCENE]->(s)
        
        WITH s
        UNWIND $source_ids AS source_id
        
        MATCH (d:Document {doc_id: source_id})
        CREATE (s)-[:SOURCED_FROM]->(d)
        
        RETURN s.scene_id AS scene_id
        """
        
        result = self.execute_write(
            query,
            {
                "video_id": video_id,
                "scene_id": scene_id,
                "scene_num": scene_num,
                "text": text,
                "attribution_text": attribution_text,
                "source_ids": source_ids
            }
        )
        
        return result[0]["scene_id"] if result else scene_id
    
    def track_ai_model_usage(
        self,
        video_id: str,
        model_name: str,
        model_version: str,
        provider: str | None = None
    ) -> None:
        """
        Track which AI model was used to generate the video.
        
        Args:
            video_id: Video identifier
            model_name: Model name (e.g., 'kling', 'veo3')
            model_version: Model version
            provider: Provider name (e.g., 'Kuaishou', 'Google')
        """
        query = """
        MATCH (v:Video {video_id: $video_id})
        
        MERGE (m:AIModel {
            name: $model_name,
            version: $model_version
        })
        ON CREATE SET m.provider = $provider, m.created_at = datetime()
        
        CREATE (v)-[:GENERATED_BY {timestamp: datetime()}]->(m)
        """
        
        self.execute_write(
            query,
            {
                "video_id": video_id,
                "model_name": model_name,
                "model_version": model_version,
                "provider": provider
            }
        )
    
    def finalize_video_provenance(
        self,
        video_id: str,
        duration: float | None = None,
        file_size: int | None = None,
        artifact_id: str | None = None
    ) -> None:
        """
        Update video node with final metadata after generation completes.
        
        Args:
            video_id: Video identifier
            duration: Video duration in seconds
            file_size: File size in bytes
            artifact_id: Storage artifact ID
        """
        query = """
        MATCH (v:Video {video_id: $video_id})
        
        SET v.completed_at = datetime(),
            v.status = 'completed'
        """
        
        params: dict[str, Any] = {"video_id": video_id}
        
        if duration is not None:
            query += ", v.duration = $duration"
            params["duration"] = duration
        
        if file_size is not None:
            query += ", v.file_size = $file_size"
            params["file_size"] = file_size
        
        if artifact_id is not None:
            query += ", v.artifact_id = $artifact_id"
            params["artifact_id"] = artifact_id
        
        self.execute_write(query, params)
    
    def get_video_genealogy(self, video_id: str) -> dict[str, Any] | None:
        """
        Get complete genealogy of a video including all provenance relationships.
        
        Args:
            video_id: Video identifier
            
        Returns:
            Dictionary containing video, sources, scenes, models, creator, versions, related content
        """
        query = """
        MATCH (v:Video {video_id: $video_id})
        
        // Get source documents
        OPTIONAL MATCH (v)-[:GENERATED_FROM]->(d:Document)
        OPTIONAL MATCH (d)-[:CITES]->(cited:Document)
        
        // Get scenes and their sources
        OPTIONAL MATCH (v)-[:HAS_SCENE]->(scene:VideoScene)
        OPTIONAL MATCH (scene)-[:SOURCED_FROM]->(scene_doc:Document)
        
        // Get AI models used
        OPTIONAL MATCH (v)-[:GENERATED_BY]->(model:AIModel)
        
        // Get creator
        OPTIONAL MATCH (user:User)-[:CREATED]->(v)
        
        // Get version history
        OPTIONAL MATCH (v)-[:VERSION_OF]->(prev:Video)
        OPTIONAL MATCH (next:Video)-[:VERSION_OF]->(v)
        
        // Get related content
        OPTIONAL MATCH (v)-[:RELATED_TO]->(related)
        
        // Collect scene sources separately to avoid nested aggregates
        WITH v, d, cited, scene, model, user, prev, next, related, 
             collect(DISTINCT scene_doc.doc_id) AS scene_sources
        ORDER BY scene.scene_num
        
        RETURN 
            v AS video,
            collect(DISTINCT d) AS source_documents,
            collect(DISTINCT cited) AS citations,
            collect(DISTINCT {
                scene_num: scene.scene_num,
                scene_id: scene.scene_id,
                text: scene.text,
                attribution: scene.attribution,
                sources: scene_sources
            }) AS scenes,
            collect(DISTINCT model) AS ai_models,
            user,
            prev AS previous_version,
            next AS next_version,
            collect(DISTINCT related) AS related_content
        """
        
        results = self.execute_query(query, {"video_id": video_id})
        
        if not results:
            return None
        
        result = results[0]
        
        # Convert Neo4j nodes to dictionaries
        return {
            "video": dict(result["video"]) if result["video"] else None,
            "source_documents": [dict(d) for d in result["source_documents"] if d],
            "citations": [dict(c) for c in result["citations"] if c],
            "scenes": [s for s in result["scenes"] if s.get("scene_num") is not None],
            "ai_models": [dict(m) for m in result["ai_models"] if m],
            "creator": dict(result["user"]) if result["user"] else None,
            "previous_version": dict(result["previous_version"]) if result["previous_version"] else None,
            "next_version": dict(result["next_version"]) if result["next_version"] else None,
            "related_content": [dict(r) for r in result["related_content"] if r]
        }
    
    def get_video_impact(self, video_id: str) -> dict[str, Any]:
        """
        Get impact metrics for a video (views, shares, derivatives, citations).
        
        Args:
            video_id: Video identifier
            
        Returns:
            Dictionary with impact metrics
        """
        query = """
        MATCH (v:Video {video_id: $video_id})
        
        // Get views
        OPTIONAL MATCH (v)<-[view:VIEWED]-(:User)
        
        // Get shares
        OPTIONAL MATCH (v)<-[share:SHARED]-(:User)
        
        // Get derivative works (videos that used this video as source)
        OPTIONAL MATCH (derivative:Video)-[:GENERATED_FROM]->(v)
        
        // Get citations (other videos that reference this one)
        OPTIONAL MATCH (citing:Video)-[:CITES]->(v)
        
        RETURN 
            v,
            count(DISTINCT view) AS view_count,
            count(DISTINCT share) AS share_count,
            collect(DISTINCT derivative) AS derivative_works,
            collect(DISTINCT citing) AS citing_videos
        """
        
        results = self.execute_query(query, {"video_id": video_id})
        
        if not results:
            return {
                "video_id": video_id,
                "view_count": 0,
                "share_count": 0,
                "derivative_count": 0,
                "citation_count": 0,
                "derivative_works": [],
                "citing_videos": []
            }
        
        result = results[0]
        
        derivatives = [dict(d) for d in result["derivative_works"] if d]
        citations = [dict(c) for c in result["citing_videos"] if c]
        
        return {
            "video_id": video_id,
            "view_count": result["view_count"],
            "share_count": result["share_count"],
            "derivative_count": len(derivatives),
            "citation_count": len(citations),
            "derivative_works": derivatives,
            "citing_videos": citations
        }
    
    def get_generated_content_from_document(self, doc_id: str) -> dict[str, list[dict]]:
        """
        Get all content generated from a source document.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Dictionary with videos, podcasts, and other exports
        """
        query = """
        MATCH (d:Document {doc_id: $doc_id})
        
        // Get videos
        OPTIONAL MATCH (v:Video)-[:GENERATED_FROM]->(d)
        
        // Get podcasts
        OPTIONAL MATCH (p:Podcast)-[:GENERATED_FROM]->(d)
        
        // Get other exports
        OPTIONAL MATCH (e:Export)-[:GENERATED_FROM]->(d)
        
        RETURN 
            d,
            collect(DISTINCT v) AS videos,
            collect(DISTINCT p) AS podcasts,
            collect(DISTINCT e) AS other_exports
        """
        
        results = self.execute_query(query, {"doc_id": doc_id})
        
        if not results:
            return {
                "videos": [],
                "podcasts": [],
                "other_exports": []
            }
        
        result = results[0]
        
        return {
            "videos": [dict(v) for v in result["videos"] if v],
            "podcasts": [dict(p) for p in result["podcasts"] if p],
            "other_exports": [dict(e) for e in result["other_exports"] if e]
        }

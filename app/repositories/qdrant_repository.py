"""Qdrant Repository for vector similarity search."""
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    Range,
    VectorParams,
)


class QdrantRepository:
    """
    Repository for managing content embeddings in Qdrant.

    Provides methods for adding, querying, updating, and deleting vector embeddings
    with associated metadata.
    """

    def __init__(
        self,
        client: QdrantClient,
        collection_name: str,
        vector_size: int = 384
    ):
        """
        Initialize QdrantRepository.

        Args:
            client: Qdrant client instance
            collection_name: Name of the collection to use
            vector_size: Dimensionality of vectors (default: 384 for sentence-transformers)
        """
        self.client = client
        self.collection_name = collection_name
        self.vector_size = vector_size

        # Create collection if it doesn't exist
        self._ensure_collection_exists()

    def _ensure_collection_exists(self) -> None:
        """Create collection if it doesn't exist."""
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            # Collection doesn't exist, create it
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )

    def add(
        self,
        content_id: str,
        vector: list[float],
        metadata: dict[str, Any]
    ) -> None:
        """
        Add a single embedding with metadata.

        Args:
            content_id: Unique identifier for the content
            vector: Embedding vector
            metadata: Associated metadata

        Raises:
            ValueError: If vector is empty or wrong size
        """
        if not vector:
            raise ValueError("Vector cannot be empty")
        if len(vector) != self.vector_size:
            raise ValueError(
                f"Vector size {len(vector)} doesn't match collection size {self.vector_size}"
            )

        point = PointStruct(
            id=content_id,
            vector=vector,
            payload=metadata
        )

        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )

    def add_batch(self, embeddings: list[dict[str, Any]]) -> None:
        """
        Add multiple embeddings in a batch.

        Args:
            embeddings: List of dicts with keys: content_id, vector, metadata
        """
        points = []
        for emb in embeddings:
            point = PointStruct(
                id=emb["content_id"],
                vector=emb["vector"],
                payload=emb["metadata"]
            )
            points.append(point)

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    def get_by_id(self, content_id: str) -> dict[str, Any] | None:
        """
        Retrieve embedding by content ID.

        Args:
            content_id: Content identifier

        Returns:
            Dict with id, vector, and metadata, or None if not found
        """
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[content_id],
                with_vectors=True
            )

            if not result:
                return None

            point = result[0]
            return {
                "id": point.id,
                "vector": point.vector,
                "metadata": point.payload
            }
        except Exception:
            return None

    def query(
        self,
        query_vector: list[float],
        limit: int = 10,
        filter_conditions: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Query for similar embeddings.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            filter_conditions: Optional metadata filters

        Returns:
            List of results with id, score, and metadata
        """
        # Build filter if provided
        query_filter = None
        if filter_conditions:
            query_filter = self._build_filter(filter_conditions)

        try:
            import inspect

            signature = inspect.signature(self.client.query_points)
            kwargs = {
                "collection_name": self.collection_name,
                "query": query_vector,
                "limit": limit,
            }
            if query_filter is not None:
                param_name = "query_filter" if "query_filter" in signature.parameters else "filter"
                kwargs[param_name] = query_filter

            response = self.client.query_points(**kwargs)
            results = getattr(response, "points", response)
        except AttributeError:
            # Older clients expose the deprecated search API.
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=query_filter
            )

        return [
            {
                "id": result.id,
                "score": result.score,
                "metadata": result.payload
            }
            for result in results
        ]

    def _build_filter(self, conditions: dict[str, Any]) -> Filter:
        """
        Build Qdrant filter from conditions dict.

        Args:
            conditions: Filter conditions (e.g., {"quality_score": {"$gte": 8.0}})

        Returns:
            Qdrant Filter object
        """
        field_conditions = []

        for field, condition in conditions.items():
            if isinstance(condition, dict):
                # Handle range conditions like {"$gte": 8.0}
                for operator, value in condition.items():
                    if operator == "$gte":
                        field_conditions.append(
                            FieldCondition(
                                key=field,
                                range=Range(gte=value)
                            )
                        )
                    elif operator == "$lte":
                        field_conditions.append(
                            FieldCondition(
                                key=field,
                                range=Range(lte=value)
                            )
                        )
                    elif operator == "$eq":
                        field_conditions.append(
                            FieldCondition(
                                key=field,
                                match=MatchValue(value=value)
                            )
                        )
            else:
                # Direct value match
                field_conditions.append(
                    FieldCondition(
                        key=field,
                        match=MatchValue(value=condition)
                    )
                )

        return Filter(must=field_conditions)

    def delete(self, content_id: str) -> None:
        """
        Delete embedding by content ID.

        Args:
            content_id: Content identifier
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[content_id]
            )
        except Exception:
            pass  # Silently ignore if doesn't exist

    def delete_batch(self, content_ids: list[str]) -> None:
        """
        Delete multiple embeddings.

        Args:
            content_ids: List of content identifiers
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=content_ids
            )
        except Exception:
            pass

    def update_metadata(
        self,
        content_id: str,
        metadata: dict[str, Any]
    ) -> None:
        """
        Update metadata without changing vector.

        Args:
            content_id: Content identifier
            metadata: New metadata
        """
        self.client.set_payload(
            collection_name=self.collection_name,
            payload=metadata,
            points=[content_id]
        )

    def count(self) -> int:
        """
        Get total number of embeddings in collection.

        Returns:
            Count of embeddings
        """
        collection_info = self.client.get_collection(self.collection_name)
        return collection_info.points_count

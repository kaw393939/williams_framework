"""Citation Service for Story S6-604: RAG with Citations.

Manages citation creation, resolution, and metadata tracking with
pagination, sorting, and filtering support for scalability.
"""

from typing import Any
from datetime import datetime

from app.repositories.neo_repository import NeoRepository


class CitationService:
    """Service for managing citations and their metadata."""

    def __init__(self, neo_repo: NeoRepository):
        """Initialize citation service.
        
        Args:
            neo_repo: Neo4j repository for citation storage
        """
        self._neo_repo = neo_repo
        self._citation_cache: dict[str, dict[str, Any]] = {}

    def create_citation(
        self,
        chunk_id: str,
        quote_text: str,
        citation_number: int,
        max_quote_length: int = 200
    ) -> dict[str, Any]:
        """Create a citation from a chunk.
        
        Args:
            chunk_id: Source chunk ID
            quote_text: Quote text from chunk
            citation_number: Citation number ([1], [2], etc.)
            max_quote_length: Maximum length for quote (default 200)
            
        Returns:
            Citation dictionary with all metadata
        """
        # Get chunk and document info
        chunk = self._neo_repo.get_chunk(chunk_id)
        if not chunk:
            raise ValueError(f"Chunk {chunk_id} not found")
        
        doc_id = chunk.get("doc_id")
        document = self._neo_repo.get_document(doc_id) if doc_id else None
        
        # Truncate quote if needed
        if len(quote_text) > max_quote_length:
            quote_text = quote_text[:max_quote_length] + "..."
        
        # Build citation
        citation_id = f"[{citation_number}]"
        citation = {
            "citation_id": citation_id,
            "citation_number": citation_number,
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "doc_url": document.get("url", "") if document else "",
            "title": document.get("title", "") if document else "",
            "quote_text": quote_text,
            "metadata": document.get("metadata", {}) if document else {},
            "created_at": datetime.now().isoformat(),
        }
        
        # Cache citation
        self._citation_cache[citation_id] = citation
        
        return citation

    def resolve_citations(self, citation_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Resolve multiple citation IDs to full metadata.
        
        Args:
            citation_ids: List of citation IDs ([1], [2], etc.)
            
        Returns:
            Dictionary mapping citation ID to metadata
        """
        resolved = {}
        
        for cit_id in citation_ids:
            if cit_id in self._citation_cache:
                resolved[cit_id] = self._citation_cache[cit_id]
            else:
                # Try to reconstruct from stored data
                # In production, citations could be stored in Neo4j or cache
                resolved[cit_id] = {
                    "citation_id": cit_id,
                    "error": "Citation not found in cache"
                }
        
        return resolved

    def get_citations(
        self,
        sort_by: str = "relevance",
        sort_order: str = "desc",
        limit: int = 100,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get citations with sorting and filtering.
        
        Args:
            sort_by: Sort field (relevance, date, title)
            sort_order: Sort order (asc, desc)
            limit: Maximum number to return
            date_from: Filter by date from (YYYY-MM-DD)
            date_to: Filter by date to (YYYY-MM-DD)
            
        Returns:
            List of citations matching criteria
        """
        citations = list(self._citation_cache.values())
        
        # Filter by date if provided
        if date_from or date_to:
            filtered = []
            for citation in citations:
                pub_date = citation.get("metadata", {}).get("published", "")
                if not pub_date:
                    continue
                
                if date_from and pub_date < date_from:
                    continue
                if date_to and pub_date > date_to:
                    continue
                    
                filtered.append(citation)
            citations = filtered
        
        # Sort
        if sort_by == "relevance":
            citations.sort(
                key=lambda c: c.get("relevance_score", 0),
                reverse=(sort_order == "desc")
            )
        elif sort_by == "date":
            citations.sort(
                key=lambda c: c.get("metadata", {}).get("published", ""),
                reverse=(sort_order == "desc")
            )
        elif sort_by == "title":
            citations.sort(
                key=lambda c: c.get("title", ""),
                reverse=(sort_order == "desc")
            )
        
        return citations[:limit]

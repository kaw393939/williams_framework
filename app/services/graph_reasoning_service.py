"""Graph Reasoning Service for Story S6-605: Graph Reasoning Queries.

Provides Cypher query helpers for entity relationships, path finding,
and "Explain this answer" functionality with pagination and filtering.
"""

from typing import Any
from app.repositories.neo_repository import NeoRepository


class GraphReasoningService:
    """Service for graph traversal and reasoning queries."""

    def __init__(self, neo_repo: NeoRepository):
        """Initialize graph reasoning service.
        
        Args:
            neo_repo: Neo4j repository for graph queries
        """
        self._neo_repo = neo_repo

    def get_entity_relationships(
        self,
        entity_text: str,
        page: int = 1,
        page_size: int = 10,
        relationship_type: str | None = None
    ) -> dict[str, Any]:
        """Get all relationships for an entity with pagination.
        
        Args:
            entity_text: Entity text to search for
            page: Page number (1-indexed)
            page_size: Results per page
            relationship_type: Filter by relationship type (optional)
            
        Returns:
            Dictionary with relationships, pagination info
        """
        # Build query
        rel_filter = f":{relationship_type}" if relationship_type else ""
        
        query = f"""
        MATCH (e:Entity {{text: $entity_text}})-[r{rel_filter}]->(target:Entity)
        RETURN type(r) as type,
               target.text as target_entity,
               target.entity_type as target_type,
               r.confidence as confidence,
               r.evidence_text as evidence
        ORDER BY r.confidence DESC
        """
        
        results = self._neo_repo.execute_query(query, {"entity_text": entity_text})
        all_relationships = [dict(r) for r in results]
        
        # Pagination
        total_count = len(all_relationships)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = all_relationships[start_idx:end_idx]
        
        return {
            "relationships": paginated,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }

    def find_path_between_entities(
        self,
        start_entity: str,
        end_entity: str,
        max_depth: int = 5,
        max_paths: int = 3
    ) -> dict[str, Any]:
        """Find shortest paths between two entities.
        
        Args:
            start_entity: Starting entity text
            end_entity: Ending entity text
            max_depth: Maximum path depth
            max_paths: Maximum number of paths to return
            
        Returns:
            Dictionary with paths found
        """
        query = """
        MATCH path = shortestPath(
            (start:Entity {text: $start_entity})-[*..%d]-(end:Entity {text: $end_entity})
        )
        RETURN [node in nodes(path) | node.text] as nodes,
               [rel in relationships(path) | type(rel)] as relationships,
               length(path) as path_length
        LIMIT $max_paths
        """ % max_depth
        
        results = self._neo_repo.execute_query(query, {
            "start_entity": start_entity,
            "end_entity": end_entity,
            "max_paths": max_paths
        })
        
        paths = []
        for result in results:
            paths.append({
                "nodes": result["nodes"],
                "relationships": result["relationships"],
                "length": result["path_length"]
            })
        
        return {
            "paths": paths,
            "start_entity": start_entity,
            "end_entity": end_entity,
            "max_depth": max_depth
        }

    def explain_answer(
        self,
        answer: str,
        entity_mentions: list[str]
    ) -> dict[str, Any]:
        """Explain answer by showing reasoning graph.
        
        Args:
            answer: Generated answer text
            entity_mentions: Entities mentioned in answer
            
        Returns:
            Dictionary with graph structure and evidence
        """
        if len(entity_mentions) < 2:
            return {
                "graph": {"nodes": [], "edges": []},
                "evidence": []
            }
        
        # Get subgraph connecting mentioned entities
        query = """
        MATCH (e1:Entity)
        WHERE e1.text IN $entity_mentions
        MATCH (e2:Entity)
        WHERE e2.text IN $entity_mentions AND id(e1) < id(e2)
        MATCH path = shortestPath((e1)-[*..3]-(e2))
        RETURN nodes(path) as nodes, relationships(path) as relationships
        LIMIT 10
        """
        
        results = self._neo_repo.execute_query(query, {"entity_mentions": entity_mentions})
        
        # Build graph structure
        nodes = []
        edges = []
        node_ids = set()
        
        for result in results:
            # Add nodes
            for node in result["nodes"]:
                node_id = node.get("id") or node.get("text")
                if node_id not in node_ids:
                    nodes.append({
                        "id": node_id,
                        "text": node.get("text"),
                        "type": node.get("entity_type")
                    })
                    node_ids.add(node_id)
            
            # Add edges
            for i, rel in enumerate(result["relationships"]):
                edges.append({
                    "source": result["nodes"][i].get("text"),
                    "target": result["nodes"][i+1].get("text"),
                    "type": rel.type if hasattr(rel, 'type') else "RELATED",
                    "confidence": rel.get("confidence", 0.5) if hasattr(rel, 'get') else 0.5
                })
        
        return {
            "graph": {
                "nodes": nodes,
                "edges": edges
            },
            "evidence": answer,
            "entity_count": len(nodes)
        }

    def find_related_entities(
        self,
        entity_text: str,
        entity_type_filter: str | None = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "confidence",
        sort_order: str = "desc"
    ) -> dict[str, Any]:
        """Find entities related to a given entity.
        
        Args:
            entity_text: Source entity text
            entity_type_filter: Filter by entity type (PERSON, ORG, etc.)
            page: Page number
            page_size: Results per page
            sort_by: Sort field (confidence, text)
            sort_order: Sort order (asc, desc)
            
        Returns:
            Dictionary with related entities and pagination info
        """
        type_filter = "AND target.entity_type = $entity_type" if entity_type_filter else ""
        
        query = f"""
        MATCH (e:Entity {{text: $entity_text}})-[r]->(target:Entity)
        WHERE 1=1 {type_filter}
        RETURN DISTINCT target.text as text,
               target.entity_type as entity_type,
               max(r.confidence) as confidence,
               type(r) as relationship_type
        ORDER BY {sort_by} {'DESC' if sort_order == 'desc' else 'ASC'}
        """
        
        params = {"entity_text": entity_text}
        if entity_type_filter:
            params["entity_type"] = entity_type_filter
        
        results = self._neo_repo.execute_query(query, params)
        all_entities = [dict(r) for r in results]
        
        # Pagination
        total_count = len(all_entities)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = all_entities[start_idx:end_idx]
        
        return {
            "entities": paginated,
            "total_count": total_count,
            "page": page,
            "page_size": page_size
        }

    def traverse_graph(
        self,
        start_entity: str,
        max_depth: int = 3,
        traversal_type: str = "breadth_first"
    ) -> dict[str, Any]:
        """Traverse graph from starting entity.
        
        Args:
            start_entity: Starting entity text
            max_depth: Maximum traversal depth
            traversal_type: Type of traversal (breadth_first, depth_first)
            
        Returns:
            Dictionary with subgraph (nodes and edges)
        """
        query = """
        MATCH path = (start:Entity {text: $start_entity})-[*..%d]-(connected:Entity)
        RETURN DISTINCT
            [node in nodes(path) | {id: node.id, text: node.text, type: node.entity_type}] as nodes,
            [rel in relationships(path) | {type: type(rel), confidence: rel.confidence}] as edges,
            length(path) as depth
        LIMIT 100
        """ % max_depth
        
        results = self._neo_repo.execute_query(query, {"start_entity": start_entity})
        
        # Collect unique nodes and edges
        all_nodes = []
        all_edges = []
        node_ids = set()
        
        for result in results:
            for node in result["nodes"]:
                node_id = node.get("id") or node.get("text")
                if node_id not in node_ids:
                    all_nodes.append(node)
                    node_ids.add(node_id)
            
            all_edges.extend(result["edges"])
        
        return {
            "nodes": all_nodes,
            "edges": all_edges,
            "max_depth_reached": max_depth,
            "node_count": len(all_nodes),
            "edge_count": len(all_edges)
        }

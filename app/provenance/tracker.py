"""Provenance tracker for content genealogy and attribution."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from neo4j import AsyncGraphDatabase, AsyncDriver


class ProvenanceTracker:
    """
    Tracks content provenance using Neo4j graph database.
    
    Provides genealogy tracking, attribution, license compliance,
    and impact metrics for imported and exported content.
    """
    
    def __init__(self, neo4j_driver: Optional[AsyncDriver] = None):
        """
        Initialize provenance tracker.
        
        Args:
            neo4j_driver: Neo4j async driver instance (optional for testing)
        """
        self.driver = neo4j_driver
        
    async def track_import(self, import_data: Dict[str, Any]) -> str:
        """
        Track imported content in provenance graph.
        
        Args:
            import_data: Import metadata including:
                - content_id: Unique content identifier
                - source_url: Original source URL
                - source_type: Type of source (youtube, pdf, etc.)
                - metadata: Extracted metadata
                - import_parameters: Import parameters
                - imported_at: Import timestamp
                
        Returns:
            Provenance ID
            
        Raises:
            ValueError: If required fields are missing
        """
        if not import_data.get("content_id"):
            raise ValueError("content_id is required")
            
        if not import_data.get("source_url"):
            raise ValueError("source_url is required")
            
        provenance_id = str(uuid4())
        
        if self.driver:
            query = """
            CREATE (c:Content {
                content_id: $content_id,
                provenance_id: $provenance_id,
                source_url: $source_url,
                source_type: $source_type,
                imported_at: $imported_at,
                metadata: $metadata
            })
            CREATE (s:Source {
                url: $source_url,
                type: $source_type
            })
            MERGE (c)-[:IMPORTED_FROM]->(s)
            RETURN c.provenance_id as provenance_id
            """
            
            async with self.driver.session() as session:
                result = await session.run(
                    query,
                    content_id=import_data["content_id"],
                    provenance_id=provenance_id,
                    source_url=import_data["source_url"],
                    source_type=import_data.get("source_type", "unknown"),
                    imported_at=import_data.get("imported_at", datetime.now().isoformat()),
                    metadata=str(import_data.get("metadata", {})),
                )
                record = await result.single()
                if record:
                    return record["provenance_id"]
                    
        return provenance_id
        
    async def track_export(self, export_data: Dict[str, Any]) -> str:
        """
        Track exported content in provenance graph.
        
        Args:
            export_data: Export metadata including:
                - export_id: Unique export identifier
                - source_ids: List of source content IDs
                - export_type: Type of export (podcast, video, etc.)
                - scene_attributions: Scene-level source mappings
                - ai_models_used: List of AI models used
                - export_parameters: Export parameters
                - exported_at: Export timestamp
                
        Returns:
            Provenance ID
            
        Raises:
            ValueError: If required fields are missing
        """
        if not export_data.get("export_id"):
            raise ValueError("export_id is required")
            
        if not export_data.get("source_ids"):
            raise ValueError("source_ids is required")
            
        provenance_id = str(uuid4())
        
        if self.driver:
            # Create export node
            query = """
            CREATE (e:Export {
                export_id: $export_id,
                provenance_id: $provenance_id,
                export_type: $export_type,
                exported_at: $exported_at,
                ai_models_used: $ai_models_used
            })
            RETURN e.provenance_id as provenance_id
            """
            
            async with self.driver.session() as session:
                result = await session.run(
                    query,
                    export_id=export_data["export_id"],
                    provenance_id=provenance_id,
                    export_type=export_data.get("export_type", "unknown"),
                    exported_at=export_data.get("exported_at", datetime.now().isoformat()),
                    ai_models_used=export_data.get("ai_models_used", []),
                )
                await result.single()
                
                # Link to source contents
                for source_id in export_data["source_ids"]:
                    link_query = """
                    MATCH (e:Export {export_id: $export_id})
                    MATCH (c:Content {content_id: $source_id})
                    MERGE (e)-[:GENERATED_FROM]->(c)
                    """
                    await session.run(
                        link_query,
                        export_id=export_data["export_id"],
                        source_id=source_id,
                    )
                    
                # Track scene attributions
                for scene in export_data.get("scene_attributions", []):
                    scene_query = """
                    MATCH (e:Export {export_id: $export_id})
                    CREATE (s:Scene {
                        scene_index: $scene_index,
                        export_id: $export_id,
                        source_ids: $source_ids
                    })
                    MERGE (e)-[:HAS_SCENE]->(s)
                    """
                    await session.run(
                        scene_query,
                        export_id=export_data["export_id"],
                        scene_index=scene.get("scene_index", 0),
                        source_ids=scene.get("source_ids", []),
                    )
                    
                # Track AI models
                for model in export_data.get("ai_models_used", []):
                    model_query = """
                    MATCH (e:Export {export_id: $export_id})
                    MERGE (m:AIModel {name: $model_name})
                    MERGE (e)-[:GENERATED_BY]->(m)
                    """
                    await session.run(
                        model_query,
                        export_id=export_data["export_id"],
                        model_name=model,
                    )
                    
        return provenance_id
        
    async def get_genealogy(self, content_id: str) -> Dict[str, Any]:
        """
        Get complete genealogy for a content item.
        
        Args:
            content_id: Content or export ID
            
        Returns:
            Genealogy data with sources, derivatives, and relationships
        """
        if not self.driver:
            return {
                "content_id": content_id,
                "sources": [],
                "derivatives": [],
                "ancestors": [],
            }
            
        query = """
        MATCH (c {content_id: $content_id})
        OPTIONAL MATCH (c)-[:IMPORTED_FROM]->(source:Source)
        OPTIONAL MATCH (c)-[:GENERATED_FROM]->(ancestor)
        OPTIONAL MATCH (derivative)-[:GENERATED_FROM]->(c)
        RETURN 
            c,
            collect(DISTINCT source) as sources,
            collect(DISTINCT ancestor) as ancestors,
            collect(DISTINCT derivative) as derivatives
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, content_id=content_id)
            record = await result.single()
            
            if not record:
                return {
                    "content_id": content_id,
                    "sources": [],
                    "derivatives": [],
                    "ancestors": [],
                }
                
            return {
                "content_id": content_id,
                "sources": [dict(s) for s in record["sources"] if s],
                "ancestors": [dict(a) for a in record["ancestors"] if a],
                "derivatives": [dict(d) for d in record["derivatives"] if d],
            }
            
    async def get_attribution_text(
        self,
        content_id: str,
        format: str = "markdown",
    ) -> str:
        """
        Generate attribution text for a content item.
        
        Args:
            content_id: Content or export ID
            format: Output format ('markdown', 'plain', 'html')
            
        Returns:
            Formatted attribution text
        """
        genealogy = await self.get_genealogy(content_id)
        
        if not genealogy["sources"] and not genealogy["ancestors"]:
            return ""
            
        lines = []
        
        if format == "markdown":
            lines.append("## Content Attribution\n")
            
            if genealogy["sources"]:
                lines.append("### Original Sources")
                for source in genealogy["sources"]:
                    url = source.get("url", "")
                    source_type = source.get("type", "unknown")
                    lines.append(f"- [{source_type.title()}]({url})")
                lines.append("")
                
            if genealogy["ancestors"]:
                lines.append("### Derived From")
                for ancestor in genealogy["ancestors"]:
                    ancestor_id = ancestor.get("content_id", "")
                    lines.append(f"- Content ID: `{ancestor_id}`")
                lines.append("")
                
        elif format == "plain":
            lines.append("Content Attribution:\n")
            
            if genealogy["sources"]:
                lines.append("Original Sources:")
                for source in genealogy["sources"]:
                    url = source.get("url", "")
                    lines.append(f"  - {url}")
                lines.append("")
                
            if genealogy["ancestors"]:
                lines.append("Derived From:")
                for ancestor in genealogy["ancestors"]:
                    ancestor_id = ancestor.get("content_id", "")
                    lines.append(f"  - {ancestor_id}")
                lines.append("")
                
        return "\n".join(lines)
        
    async def check_license_compliance(
        self,
        content_id: str,
        target_license: str,
    ) -> Dict[str, Any]:
        """
        Check if content complies with target license.
        
        Args:
            content_id: Content or export ID
            target_license: Target license (e.g., 'CC-BY', 'commercial')
            
        Returns:
            Compliance report with conflicts and recommendations
        """
        genealogy = await self.get_genealogy(content_id)
        
        # Simple license compatibility check
        compatible_licenses = {
            "CC-BY": ["CC-BY", "CC0", "public-domain"],
            "CC-BY-SA": ["CC-BY-SA", "CC-BY", "CC0", "public-domain"],
            "CC-BY-NC": ["CC-BY-NC", "CC-BY", "CC0", "public-domain"],
            "commercial": ["CC-BY", "CC0", "public-domain", "commercial"],
        }
        
        conflicts = []
        compatible = compatible_licenses.get(target_license, [])
        
        for source in genealogy["sources"]:
            source_license = source.get("license", "unknown")
            if source_license not in compatible and source_license != "unknown":
                conflicts.append({
                    "source": source.get("url", ""),
                    "license": source_license,
                    "reason": f"Incompatible with {target_license}",
                })
                
        return {
            "content_id": content_id,
            "target_license": target_license,
            "compliant": len(conflicts) == 0,
            "conflicts": conflicts,
            "recommendation": (
                "All sources are compatible"
                if len(conflicts) == 0
                else "Review source licenses before distribution"
            ),
        }
        
    async def get_impact_metrics(self, content_id: str) -> Dict[str, Any]:
        """
        Get impact metrics for content (views, shares, derivatives, citations).
        
        Args:
            content_id: Content or export ID
            
        Returns:
            Impact metrics dictionary
        """
        if not self.driver:
            return {
                "content_id": content_id,
                "derivative_count": 0,
                "citation_count": 0,
                "total_reach": 0,
            }
            
        query = """
        MATCH (c {content_id: $content_id})
        OPTIONAL MATCH (derivative)-[:GENERATED_FROM]->(c)
        OPTIONAL MATCH (citation)-[:CITES]->(c)
        RETURN 
            count(DISTINCT derivative) as derivative_count,
            count(DISTINCT citation) as citation_count
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, content_id=content_id)
            record = await result.single()
            
            if not record:
                return {
                    "content_id": content_id,
                    "derivative_count": 0,
                    "citation_count": 0,
                    "total_reach": 0,
                }
                
            derivative_count = record["derivative_count"] or 0
            citation_count = record["citation_count"] or 0
            
            return {
                "content_id": content_id,
                "derivative_count": derivative_count,
                "citation_count": citation_count,
                "total_reach": derivative_count + citation_count,
            }
            
    async def get_citation_network(self, content_id: str, depth: int = 2) -> Dict[str, Any]:
        """
        Get citation network for content.
        
        Args:
            content_id: Content or export ID
            depth: Network depth (default 2)
            
        Returns:
            Citation network with nodes and edges
        """
        if not self.driver:
            return {
                "content_id": content_id,
                "nodes": [],
                "edges": [],
            }
            
        query = """
        MATCH path = (c {content_id: $content_id})-[:GENERATED_FROM|CITES*1..$depth]-(related)
        RETURN 
            collect(DISTINCT c) + collect(DISTINCT related) as nodes,
            [r in relationships(path) | {
                source: startNode(r).content_id,
                target: endNode(r).content_id,
                type: type(r)
            }] as edges
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, content_id=content_id, depth=depth)
            record = await result.single()
            
            if not record:
                return {
                    "content_id": content_id,
                    "nodes": [],
                    "edges": [],
                }
                
            return {
                "content_id": content_id,
                "nodes": [dict(n) for n in record["nodes"] if n],
                "edges": record["edges"],
            }
            
    async def track_version(
        self,
        content_id: str,
        previous_version_id: str,
        changes: str,
    ) -> str:
        """
        Track version relationship between content items.
        
        Args:
            content_id: New version content ID
            previous_version_id: Previous version content ID
            changes: Description of changes
            
        Returns:
            Version tracking ID
        """
        version_id = str(uuid4())
        
        if self.driver:
            query = """
            MATCH (new {content_id: $content_id})
            MATCH (old {content_id: $previous_version_id})
            CREATE (new)-[:VERSION_OF {
                version_id: $version_id,
                changes: $changes,
                created_at: $created_at
            }]->(old)
            RETURN $version_id as version_id
            """
            
            async with self.driver.session() as session:
                await session.run(
                    query,
                    content_id=content_id,
                    previous_version_id=previous_version_id,
                    version_id=version_id,
                    changes=changes,
                    created_at=datetime.now().isoformat(),
                )
                
        return version_id
        
    async def close(self) -> None:
        """Close Neo4j driver connection."""
        if self.driver:
            await self.driver.close()

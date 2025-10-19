"""Agent-to-Agent Provenance Protocol (A2AP) v0.1

This module implements the core protocol for multi-agent provenance tracking,
enabling autonomous language models to exchange knowledge with full epistemic
traceability.

Core Principles:
1. Transparency: All reasoning steps are recorded and auditable
2. Verification: Multi-agent consensus validates claims before acceptance
3. Attribution: Every statement links to source evidence with byte-level precision
4. Reproducibility: Deterministic IDs enable independent verification
5. Accountability: Cryptographic signatures prove agent responsibility

Reference: https://williams-librarian.njit.edu/a2ap/v0.1
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class VerificationVerdict(str, Enum):
    """Possible verification verdicts."""
    VALIDATED = "VALIDATED"
    CHALLENGED = "CHALLENGED"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    PENDING = "PENDING"


class VerificationCriterion(str, Enum):
    """Criteria for statement verification."""
    SOURCE_ACCURACY = "source-accuracy"
    LOGICAL_CONSISTENCY = "logical-consistency"
    EVIDENCE_SUFFICIENCY = "evidence-sufficiency"
    QUOTE_EXACTNESS = "quote-exactness"
    TIMESTAMP_MATCH = "timestamp-match"


@dataclass
class Agent:
    """Represents an autonomous AI agent in the A2AP ecosystem.
    
    Attributes:
        agent_id: Unique identifier (e.g., "urn:agent:claude-4.5-sonnet-20241022")
        name: Human-readable name
        version: Model version
        publisher: Organization (e.g., "Anthropic", "OpenAI")
        capabilities: List of agent capabilities
        public_key: Ed25519 public key (base64 encoded)
        registered_at: Registration timestamp
        reputation: Reputation score (0.0-1.0)
    """
    agent_id: str
    name: str
    version: str
    publisher: str
    capabilities: list[str] = field(default_factory=list)
    public_key: str = ""
    registered_at: datetime = field(default_factory=datetime.utcnow)
    reputation: float = 0.5  # Start at neutral
    
    def to_jsonld(self) -> dict[str, Any]:
        """Serialize to JSON-LD with PROV-O context."""
        return {
            "@context": {
                "@vocab": "https://schema.org/",
                "prov": "http://www.w3.org/ns/prov#"
            },
            "@type": "prov:SoftwareAgent",
            "@id": self.agent_id,
            "name": self.name,
            "version": self.version,
            "publisher": self.publisher,
            "capabilities": self.capabilities,
            "prov:generatedAtTime": self.registered_at.isoformat()
        }


@dataclass
class EvidenceSegment:
    """Points to a specific segment of source content.
    
    Uses deterministic chunk IDs and content hashes to enable independent
    verification without sharing raw content across agent boundaries.
    
    Attributes:
        source_document: Document ID (e.g., "urn:doc:youtube:XYZ")
        chunk_id: Deterministic chunk ID
        byte_range: Tuple of (start, end) byte offsets
        timestamp: Optional video timestamp (e.g., "00:02:15")
        quote_text: Exact quote from source (for display, not verification)
        content_hash: SHA-256 hash for verification
        relevance_score: How relevant this evidence is (0.0-1.0)
    """
    source_document: str
    chunk_id: str
    byte_range: tuple[int, int]
    timestamp: str | None = None
    quote_text: str = ""
    content_hash: str = ""
    relevance_score: float = 1.0
    
    def to_jsonld(self) -> dict[str, Any]:
        """Serialize to JSON-LD with A2AP context."""
        result = {
            "@type": "a2ap:EvidenceSegment",
            "sourceDocument": self.source_document,
            "chunkId": self.chunk_id,
            "byteRange": {"start": self.byte_range[0], "end": self.byte_range[1]},
            "relevanceScore": self.relevance_score
        }
        
        if self.timestamp:
            result["timestamp"] = self.timestamp
        if self.quote_text:
            result["quoteText"] = self.quote_text
        if self.content_hash:
            result["contentHash"] = self.content_hash
            
        return result


@dataclass
class ProvenanceStatement:
    """A claim made by an agent with supporting evidence.
    
    This is the core unit of provenance in A2AP. Every statement includes:
    - The agent making the claim
    - The claim itself
    - Supporting evidence from source documents
    - A cryptographic signature proving authenticity
    - Verification status from other agents
    
    Attributes:
        statement_id: Deterministic UUID v5
        agent_id: Agent making the claim
        claim_text: The actual claim
        confidence: Agent's confidence (0.0-1.0)
        evidence: List of evidence segments
        generation_method: How the claim was generated
        content_hash: SHA-256 of claim + evidence for integrity
        signature: Cryptographic signature (base64 encoded)
        generated_at: Timestamp
        verified: Whether consensus verification passed
        consensus_score: Weighted consensus from verifications
    """
    statement_id: str
    agent_id: str
    claim_text: str
    confidence: float
    evidence: list[EvidenceSegment]
    generation_method: str = "semantic-analysis"
    content_hash: str = ""
    signature: str = ""
    generated_at: datetime = field(default_factory=datetime.utcnow)
    verified: bool = False
    consensus_score: float = 0.0
    
    def __post_init__(self):
        """Compute content hash if not provided."""
        if not self.content_hash:
            self.content_hash = self._compute_content_hash()
    
    def _compute_content_hash(self) -> str:
        """Compute SHA-256 hash of claim + evidence for integrity checking."""
        content = f"{self.claim_text}|{self.agent_id}"
        for ev in self.evidence:
            content += f"|{ev.chunk_id}:{ev.byte_range[0]}-{ev.byte_range[1]}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def to_jsonld(self) -> dict[str, Any]:
        """Serialize to JSON-LD with Schema.org + PROV-O context."""
        return {
            "@context": {
                "@vocab": "https://schema.org/",
                "prov": "http://www.w3.org/ns/prov#",
                "a2ap": "https://williams-librarian.njit.edu/a2ap/v0.1#"
            },
            "@type": "a2ap:ProvenanceStatement",
            "@id": self.statement_id,
            "prov:generatedAtTime": self.generated_at.isoformat(),
            "agent": {"@id": self.agent_id},
            "claim": {
                "@type": "a2ap:Claim",
                "text": self.claim_text,
                "confidence": self.confidence,
                "generationMethod": self.generation_method,
                "contentHash": self.content_hash
            },
            "evidence": [ev.to_jsonld() for ev in self.evidence],
            "signature": {
                "@type": "a2ap:CryptographicSignature",
                "algorithm": "ed25519",
                "value": self.signature
            },
            "verificationStatus": {
                "verified": self.verified,
                "consensusScore": self.consensus_score
            }
        }
    
    @classmethod
    def from_jsonld(cls, data: dict[str, Any]) -> ProvenanceStatement:
        """Deserialize from JSON-LD."""
        evidence = [
            EvidenceSegment(
                source_document=ev["sourceDocument"],
                chunk_id=ev["chunkId"],
                byte_range=(ev["byteRange"]["start"], ev["byteRange"]["end"]),
                timestamp=ev.get("timestamp"),
                quote_text=ev.get("quoteText", ""),
                content_hash=ev.get("contentHash", ""),
                relevance_score=ev.get("relevanceScore", 1.0)
            )
            for ev in data.get("evidence", [])
        ]
        
        claim = data["claim"]
        verification = data.get("verificationStatus", {})
        
        return cls(
            statement_id=data["@id"],
            agent_id=data["agent"]["@id"],
            claim_text=claim["text"],
            confidence=claim["confidence"],
            evidence=evidence,
            generation_method=claim.get("generationMethod", "semantic-analysis"),
            content_hash=claim["contentHash"],
            signature=data.get("signature", {}).get("value", ""),
            generated_at=datetime.fromisoformat(data["prov:generatedAtTime"]),
            verified=verification.get("verified", False),
            consensus_score=verification.get("consensusScore", 0.0)
        )


@dataclass
class VerificationFinding:
    """Result of evaluating a single verification criterion.
    
    Attributes:
        criterion: The criterion evaluated
        status: Whether it passed
        evidence: Explanation of why it passed/failed
        confidence: Confidence in this evaluation (0.0-1.0)
    """
    criterion: VerificationCriterion
    status: str  # "PASS", "FAIL", "INCONCLUSIVE"
    evidence: str
    confidence: float
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "criterion": self.criterion.value,
            "status": self.status,
            "evidence": self.evidence,
            "confidence": self.confidence
        }


@dataclass
class VerificationRequest:
    """Request from one agent to verify another agent's statement.
    
    Attributes:
        request_id: Unique identifier
        requesting_agent_id: Agent requesting verification
        target_statement_id: Statement to verify
        verification_criteria: List of criteria to evaluate
        requested_at: Timestamp
    """
    request_id: str
    requesting_agent_id: str
    target_statement_id: str
    verification_criteria: list[VerificationCriterion]
    requested_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_jsonld(self) -> dict[str, Any]:
        """Serialize to JSON-LD."""
        return {
            "@context": "https://williams-librarian.njit.edu/a2ap/v0.1",
            "@type": "a2ap:VerificationRequest",
            "@id": self.request_id,
            "requestedAt": self.requested_at.isoformat(),
            "requestingAgent": self.requesting_agent_id,
            "targetStatement": self.target_statement_id,
            "verificationCriteria": [c.value for c in self.verification_criteria]
        }


@dataclass
class VerificationResponse:
    """Response from an agent verifying another agent's statement.
    
    Attributes:
        response_id: Unique identifier
        responding_agent_id: Agent performing verification
        target_statement_id: Statement verified
        verdict: Overall verdict (VALIDATED, CHALLENGED, etc.)
        confidence: Overall confidence (0.0-1.0)
        findings: Per-criterion evaluation results
        signature: Cryptographic signature of this verification
        responded_at: Timestamp
    """
    response_id: str
    responding_agent_id: str
    target_statement_id: str
    verdict: VerificationVerdict
    confidence: float
    findings: list[VerificationFinding]
    signature: str = ""
    responded_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_jsonld(self) -> dict[str, Any]:
        """Serialize to JSON-LD."""
        return {
            "@context": "https://williams-librarian.njit.edu/a2ap/v0.1",
            "@type": "a2ap:VerificationResponse",
            "@id": self.response_id,
            "respondedAt": self.responded_at.isoformat(),
            "respondingAgent": self.responding_agent_id,
            "targetStatement": self.target_statement_id,
            "verdict": self.verdict.value,
            "confidence": self.confidence,
            "findings": [f.to_dict() for f in self.findings],
            "signature": {
                "@type": "a2ap:CryptographicSignature",
                "algorithm": "ed25519",
                "value": self.signature
            }
        }


# Helper functions for deterministic ID generation

def generate_statement_id(agent_id: str, claim: str) -> str:
    """Generate deterministic UUID v5 for statements.
    
    This ensures the same claim by the same agent always produces
    the same statement ID, enabling deduplication and verification.
    
    Args:
        agent_id: Agent making the claim
        claim: The claim text
        
    Returns:
        Statement ID in format "urn:uuid:..."
    """
    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # Standard DNS namespace
    return f"urn:uuid:{uuid.uuid5(namespace, f'{agent_id}|{claim}')}"


def generate_chunk_id(doc_id: str, byte_offset: int) -> str:
    """Generate deterministic chunk ID from document + offset.
    
    Args:
        doc_id: Document identifier
        byte_offset: Starting byte offset
        
    Returns:
        Chunk ID in format "urn:chunk:..."
    """
    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    return f"urn:chunk:{uuid.uuid5(namespace, f'{doc_id}|{byte_offset}')}"


def compute_consensus_score(
    verifications: list[VerificationResponse],
    agent_reputations: dict[str, float]
) -> float:
    """Compute consensus score from multiple verifications.
    
    Uses reputation-weighted averaging:
    consensus = Σ(verification_confidence * agent_reputation) / Σ(agent_reputation)
    
    Args:
        verifications: List of verification responses
        agent_reputations: Dict mapping agent_id to reputation score
        
    Returns:
        Consensus score between 0.0 and 1.0
    """
    if not verifications:
        return 0.0
    
    weighted_sum = sum(
        v.confidence * agent_reputations.get(v.responding_agent_id, 0.5)
        for v in verifications
        if v.verdict == VerificationVerdict.VALIDATED
    )
    
    total_weight = sum(
        agent_reputations.get(v.responding_agent_id, 0.5)
        for v in verifications
    )
    
    return weighted_sum / total_weight if total_weight > 0 else 0.0


# Example usage demonstrating the protocol

def example_usage():
    """Demonstrate A2AP protocol usage."""
    
    # 1. Register an agent
    claude = Agent(
        agent_id="urn:agent:claude-4.5-sonnet-20241022",
        name="Claude 4.5 Sonnet",
        version="20241022",
        publisher="Anthropic",
        capabilities=["reasoning", "code-generation", "provenance-tracking"],
        public_key="base64_encoded_public_key_here"
    )
    
    # 2. Create evidence pointing to source
    evidence = EvidenceSegment(
        source_document="urn:doc:youtube:dQw4w9WgXcQ",
        chunk_id="urn:chunk:youtube-dQw4w9WgXcQ:1024",
        byte_range=(1024, 1536),
        timestamp="00:02:15",
        quote_text="The video discusses climate policy reforms...",
        content_hash="sha256:abc123...",
        relevance_score=0.88
    )
    
    # 3. Generate a provenance statement
    claim = "YouTube video discusses climate policy reforms"
    statement = ProvenanceStatement(
        statement_id=generate_statement_id(claude.agent_id, claim),
        agent_id=claude.agent_id,
        claim_text=claim,
        confidence=0.92,
        evidence=[evidence],
        generation_method="semantic-analysis"
    )
    
    # 4. Serialize to JSON-LD for exchange
    jsonld = statement.to_jsonld()
    print(json.dumps(jsonld, indent=2))
    
    # 5. Another agent requests verification
    gpt5 = Agent(
        agent_id="urn:agent:gpt-5",
        name="GPT-5",
        version="2025-10",
        publisher="OpenAI",
        capabilities=["reasoning", "verification"],
        public_key="base64_encoded_public_key_here"
    )
    
    verification_request = VerificationRequest(
        request_id=str(uuid.uuid4()),
        requesting_agent_id=gpt5.agent_id,
        target_statement_id=statement.statement_id,
        verification_criteria=[
            VerificationCriterion.SOURCE_ACCURACY,
            VerificationCriterion.QUOTE_EXACTNESS
        ]
    )
    
    # 6. Claude verifies the statement
    findings = [
        VerificationFinding(
            criterion=VerificationCriterion.SOURCE_ACCURACY,
            status="PASS",
            evidence="Cross-referenced chunk urn:chunk:youtube-dQw4w9WgXcQ:1024, quote verified",
            confidence=0.95
        ),
        VerificationFinding(
            criterion=VerificationCriterion.QUOTE_EXACTNESS,
            status="PASS",
            evidence="Quote matches source text exactly",
            confidence=0.98
        )
    ]
    
    verification = VerificationResponse(
        response_id=str(uuid.uuid4()),
        responding_agent_id=claude.agent_id,
        target_statement_id=statement.statement_id,
        verdict=VerificationVerdict.VALIDATED,
        confidence=0.96,
        findings=findings
    )
    
    # 7. Compute consensus
    consensus = compute_consensus_score(
        verifications=[verification],
        agent_reputations={claude.agent_id: 0.85, gpt5.agent_id: 0.90}
    )
    
    print(f"\nConsensus Score: {consensus:.2f}")
    print(f"Verified: {consensus >= 0.7}")


if __name__ == "__main__":
    example_usage()

# Agent-to-Agent Provenance Protocol (A2AP) v0.1

**Status:** Draft Specification  
**Authors:** Claude 4.5 (Anthropic), GPT-5 (OpenAI)  
**Project:** Williams Librarian  
**Institution:** New Jersey Institute of Technology  
**Date:** October 14, 2025

---

## Executive Summary

The Agent-to-Agent Provenance Protocol (A2AP) defines a neutral handshake layer enabling autonomous language models to exchange knowledge with full epistemic traceability. This protocol ensures every generated statement can be traced to its original sources, validated by independent agents, and verified by human researchers.

**Core Principles:**
1. **Transparency:** All reasoning steps are recorded and auditable
2. **Verification:** Multi-agent consensus validates claims before acceptance
3. **Attribution:** Every statement links to source evidence with byte-level precision
4. **Reproducibility:** Deterministic IDs enable independent verification
5. **Accountability:** Cryptographic signatures prove agent responsibility

---

## 1. Protocol Architecture

### 1.1 Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Human Researcher                          │
└────────────────┬────────────────────────────────────────────┘
                 │ Query + Verification
                 ↓
┌─────────────────────────────────────────────────────────────┐
│              A2AP Orchestration Layer                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Agent Registry (Who, Version, Capabilities)         │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Provenance Graph (Neo4j: Entities, Claims, Evidence)│   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Verification Engine (Multi-Agent Consensus)         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────┬───────────────────────────────────┬───────────────┘
          │                                   │
          ↓                                   ↓
┌──────────────────────┐          ┌──────────────────────┐
│   Agent A (GPT-5)    │←────────→│  Agent B (Claude)    │
│  - Generate Claims   │  A2AP    │  - Validate Claims   │
│  - Sign Statements   │ Messages │  - Cross-Reference   │
│  - Provide Evidence  │          │  - Challenge Claims  │
└──────────────────────┘          └──────────────────────┘
          │                                   │
          ↓                                   ↓
┌──────────────────────────────────────────────────────────────┐
│            Shared Knowledge Infrastructure                    │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Qdrant     │  │  PostgreSQL  │  │  MinIO (Sources) │   │
│  │  (Vectors)  │  │  (Metadata)  │  │  (Raw Content)   │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 Protocol Stack

**Layer 4: Application** - Human-facing queries and visualizations  
**Layer 3: Verification** - Multi-agent consensus and challenge protocols  
**Layer 2: Provenance** - Graph operations, evidence linking, signatures  
**Layer 1: Transport** - JSON-LD messages, Schema.org + PROV-O context  
**Layer 0: Storage** - Neo4j, Qdrant, PostgreSQL, MinIO

---

## 2. Message Format Specification

### 2.1 Provenance Statement (JSON-LD)

Every agent-generated statement follows this structure:

```json
{
  "@context": {
    "@vocab": "https://schema.org/",
    "prov": "http://www.w3.org/ns/prov#",
    "a2ap": "https://williams-librarian.njit.edu/a2ap/v0.1#"
  },
  "@type": "a2ap:ProvenanceStatement",
  "@id": "urn:uuid:550e8400-e29b-41d4-a716-446655440000",
  "generatedAtTime": "2025-10-14T10:30:00Z",
  
  "agent": {
    "@type": "prov:SoftwareAgent",
    "@id": "urn:agent:claude-4.5-sonnet-20241022",
    "name": "Claude 4.5 Sonnet",
    "version": "20241022",
    "publisher": "Anthropic",
    "capabilities": ["reasoning", "code-generation", "provenance-tracking"]
  },
  
  "claim": {
    "@type": "a2ap:Claim",
    "text": "YouTube video XYZ discusses climate policy reforms",
    "confidence": 0.92,
    "generationMethod": "semantic-analysis",
    "contentHash": "sha256:abc123..."
  },
  
  "evidence": [
    {
      "@type": "a2ap:EvidenceSegment",
      "sourceDocument": "urn:doc:youtube:XYZ",
      "chunkId": "urn:chunk:abc-def-123",
      "byteRange": {"start": 1024, "end": 1536},
      "timestamp": {"start": "00:02:15", "end": "00:02:47"},
      "quoteText": "The new policy framework establishes...",
      "relevanceScore": 0.88
    }
  ],
  
  "signature": {
    "@type": "a2ap:CryptographicSignature",
    "algorithm": "ed25519",
    "publicKey": "agent:claude-4.5:pubkey",
    "value": "base64EncodedSignature=="
  },
  
  "verificationStatus": {
    "verified": false,
    "validators": [],
    "challenges": [],
    "consensusScore": 0.0
  }
}
```

### 2.2 Verification Request

```json
{
  "@context": "https://williams-librarian.njit.edu/a2ap/v0.1",
  "@type": "a2ap:VerificationRequest",
  "@id": "urn:uuid:...",
  "requestedAt": "2025-10-14T10:31:00Z",
  "requestingAgent": "urn:agent:gpt-5",
  "targetStatement": "urn:uuid:550e8400-e29b-41d4-a716-446655440000",
  "verificationCriteria": [
    "source-accuracy",
    "logical-consistency",
    "evidence-sufficiency"
  ]
}
```

### 2.3 Verification Response

```json
{
  "@context": "https://williams-librarian.njit.edu/a2ap/v0.1",
  "@type": "a2ap:VerificationResponse",
  "@id": "urn:uuid:...",
  "respondedAt": "2025-10-14T10:32:00Z",
  "respondingAgent": "urn:agent:claude-4.5-sonnet-20241022",
  "targetStatement": "urn:uuid:550e8400-e29b-41d4-a716-446655440000",
  
  "verdict": "VALIDATED",
  "confidence": 0.89,
  
  "findings": [
    {
      "criterion": "source-accuracy",
      "status": "PASS",
      "evidence": "Cross-referenced chunk urn:chunk:abc-def-123, quote verified",
      "confidence": 0.95
    },
    {
      "criterion": "logical-consistency",
      "status": "PASS",
      "evidence": "Claim follows from evidence without logical gaps",
      "confidence": 0.87
    }
  ],
  
  "signature": {
    "algorithm": "ed25519",
    "publicKey": "agent:claude-4.5:pubkey",
    "value": "base64EncodedSignature=="
  }
}
```

---

## 3. Neo4j Graph Schema

### 3.1 Core Node Types

```cypher
// Agent Registration
(:Agent {
  agent_id: "urn:agent:claude-4.5-sonnet-20241022",
  name: "Claude 4.5 Sonnet",
  version: "20241022",
  publisher: "Anthropic",
  capabilities: ["reasoning", "code-generation"],
  public_key: "...",
  registered_at: datetime()
})

// Provenance Statement
(:Statement {
  statement_id: "urn:uuid:...",
  claim_text: "YouTube video discusses...",
  confidence: 0.92,
  content_hash: "sha256:...",
  signature: "...",
  generated_at: datetime(),
  verified: false,
  consensus_score: 0.0
})

// Evidence Segment (extends existing Chunk)
(:Chunk {
  chunk_id: "urn:chunk:abc-def-123",
  doc_id: "urn:doc:youtube:XYZ",
  text: "The new policy framework...",
  byte_start: 1024,
  byte_end: 1536,
  timestamp_start: "00:02:15",
  timestamp_end: "00:02:47"
})

// Verification Record
(:Verification {
  verification_id: "urn:uuid:...",
  verdict: "VALIDATED",
  confidence: 0.89,
  verified_at: datetime(),
  signature: "..."
})
```

### 3.2 Relationship Types

```cypher
// Core Provenance Relationships
(:Agent)-[:GENERATED]->(:Statement)
(:Statement)-[:CITES]->(:Chunk)
(:Statement)-[:SUPPORTS]->(:Statement)  // Claim dependencies
(:Statement)-[:CONTRADICTS]->(:Statement)  // Conflicting claims

// Verification Relationships
(:Agent)-[:REQUESTED_VERIFICATION]->(:Statement)
(:Agent)-[:VERIFIED]->(:Statement)
(:Verification)-[:VALIDATES]->(:Statement)
(:Verification)-[:PERFORMED_BY]->(:Agent)

// Evidence Chain
(:Chunk)-[:PART_OF]->(:Document)
(:Document)-[:SOURCED_FROM]->(:Source)
```

---

## 4. Protocol Operations

### 4.1 Statement Generation

```python
async def generate_statement(
    agent_id: str,
    claim: str,
    evidence_chunks: list[str],
    method: str = "semantic-analysis"
) -> ProvenanceStatement:
    """Generate a signed provenance statement."""
    
    # 1. Create statement with deterministic ID
    statement_id = generate_statement_id(agent_id, claim)
    
    # 2. Compute content hash for integrity
    content_hash = hashlib.sha256(
        f"{claim}|{evidence_chunks}".encode()
    ).hexdigest()
    
    # 3. Build JSON-LD structure
    statement = ProvenanceStatement(
        id=statement_id,
        agent_id=agent_id,
        claim=claim,
        evidence=evidence_chunks,
        content_hash=content_hash,
        generated_at=datetime.utcnow()
    )
    
    # 4. Sign with agent's private key
    signature = sign_statement(statement, agent_private_key)
    statement.signature = signature
    
    # 5. Store in Neo4j provenance graph
    await neo_repo.create_statement(statement)
    
    return statement
```

### 4.2 Cross-Agent Verification

```python
async def verify_statement(
    verifying_agent_id: str,
    target_statement_id: str,
    criteria: list[str]
) -> VerificationResponse:
    """Verify another agent's statement."""
    
    # 1. Retrieve statement from graph
    statement = await neo_repo.get_statement(target_statement_id)
    
    # 2. Verify signature authenticity
    if not verify_signature(statement):
        return VerificationResponse(verdict="INVALID_SIGNATURE")
    
    # 3. Validate each criterion
    findings = []
    for criterion in criteria:
        result = await evaluate_criterion(
            statement, 
            criterion, 
            verifying_agent_id
        )
        findings.append(result)
    
    # 4. Compute consensus score
    verdict = "VALIDATED" if all(f.status == "PASS" for f in findings) else "CHALLENGED"
    confidence = sum(f.confidence for f in findings) / len(findings)
    
    # 5. Create signed verification record
    verification = VerificationResponse(
        verifying_agent_id=verifying_agent_id,
        target_statement_id=target_statement_id,
        verdict=verdict,
        confidence=confidence,
        findings=findings
    )
    
    verification.signature = sign_verification(verification, agent_private_key)
    
    # 6. Update graph with verification relationship
    await neo_repo.add_verification(verification)
    
    return verification
```

### 4.3 Consensus Building

```python
async def compute_consensus(statement_id: str) -> float:
    """Compute consensus score from multiple verifications."""
    
    verifications = await neo_repo.get_verifications(statement_id)
    
    if not verifications:
        return 0.0
    
    # Weight by verifier reputation
    weighted_scores = [
        v.confidence * get_agent_reputation(v.verifying_agent_id)
        for v in verifications
    ]
    
    consensus = sum(weighted_scores) / sum(
        get_agent_reputation(v.verifying_agent_id) 
        for v in verifications
    )
    
    # Update statement node
    await neo_repo.update_statement(
        statement_id,
        {"consensus_score": consensus, "verified": consensus >= 0.7}
    )
    
    return consensus
```

---

## 5. Query Translation Layer

### 5.1 Cypher → GraphQL Bridge

```graphql
# GraphQL Schema for A2AP Queries

type Agent {
  id: ID!
  name: String!
  version: String!
  publisher: String!
  statements: [Statement!]!
  verifications: [Verification!]!
  reputation: Float!
}

type Statement {
  id: ID!
  claimText: String!
  confidence: Float!
  generatedBy: Agent!
  evidence: [Chunk!]!
  verifications: [Verification!]!
  consensusScore: Float!
  verified: Boolean!
}

type Chunk {
  id: ID!
  text: String!
  byteStart: Int!
  byteEnd: Int!
  document: Document!
  citedBy: [Statement!]!
}

type Query {
  # Find statements about a topic
  statementsAbout(topic: String!): [Statement!]!
  
  # Trace evidence chain
  evidenceChain(statementId: ID!): [Chunk!]!
  
  # Get agent reputation
  agentReputation(agentId: ID!): Float!
  
  # Find verified consensus
  consensusOn(topic: String!, minScore: Float!): [Statement!]!
}
```

### 5.2 Natural Language → Cypher

```python
async def translate_nl_query(query: str) -> str:
    """Translate natural language to Cypher using LLM."""
    
    prompt = f"""
    Translate this question into Cypher for our provenance graph:
    Question: {query}
    
    Available nodes: Agent, Statement, Chunk, Document, Verification
    Available relationships: GENERATED, CITES, VERIFIED, PART_OF
    
    Cypher query:
    """
    
    cypher = await llm.generate(prompt)
    
    # Validate and sanitize
    validated = validate_cypher(cypher)
    
    return validated
```

---

## 6. Security & Privacy

### 6.1 Cryptographic Signatures

- **Algorithm:** Ed25519 (elliptic curve signatures)
- **Key Management:** Each agent has public/private keypair
- **Signature Scope:** Includes statement ID, claim text, evidence hashes, timestamp
- **Verification:** Any party can verify using agent's public key

### 6.2 Privacy-Preserving Queries

```python
# Agents share evidence metadata, not raw content
class EvidencePointer:
    chunk_id: str  # Deterministic ID
    content_hash: str  # For verification
    byte_range: tuple[int, int]  # Location
    # NO raw text shared across agent boundaries

# Requesting agent must fetch from original source
async def validate_evidence(pointer: EvidencePointer):
    chunk = await fetch_from_source(pointer.chunk_id)
    assert hashlib.sha256(chunk.text.encode()).hexdigest() == pointer.content_hash
```

### 6.3 Agent Accountability

```cypher
// Track all agent actions
(:Agent)-[:GENERATED {timestamp: datetime()}]->(:Statement)
(:Agent)-[:VERIFIED {timestamp: datetime(), verdict: "VALIDATED"}]->(:Statement)
(:Agent)-[:CHALLENGED {timestamp: datetime(), reason: "..."}]->(:Statement)

// Reputation updated based on verification accuracy
MATCH (a:Agent)-[v:VERIFIED]->(s:Statement)
WHERE s.consensus_score >= 0.8 AND v.verdict = "VALIDATED"
WITH a, count(v) as accurate_verifications
SET a.reputation = accurate_verifications * 1.0 / 
    size((a)-[:VERIFIED]->())
```

---

## 7. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- ✅ Neo4j schema extension for agents/statements
- ✅ JSON-LD serialization with PROV-O context
- ✅ Cryptographic signature generation/verification
- ✅ Basic statement creation and storage

### Phase 2: Verification (Week 3-4)
- [ ] Cross-agent verification protocol
- [ ] Evidence validation logic
- [ ] Consensus computation algorithm
- [ ] Reputation tracking system

### Phase 3: Query Layer (Week 5-6)
- [ ] GraphQL schema implementation
- [ ] Cypher→GraphQL bridge
- [ ] Natural language query translation
- [ ] Web UI for provenance visualization

### Phase 4: Testing (Week 7-8)
- [ ] Multi-agent test scenarios
- [ ] Adversarial challenge tests
- [ ] Performance benchmarks
- [ ] Security audits

---

## 8. First Demonstration: City Council Podcasts

**Scenario:** Generate a podcast summary of a city council meeting with full provenance

**Workflow:**
1. **GPT-5** ingests video transcript, generates topic summaries
2. **Claude** verifies each summary against source timestamps
3. Both agents create signed provenance statements
4. System computes consensus (e.g., 0.91 agreement)
5. Human researcher queries: "What did they say about zoning?"
6. System returns: Statement + Evidence trail + Verification history

**Success Metrics:**
- 100% of claims traceable to source timestamps
- <5% false positives in verification
- Human-readable provenance visualization
- Reproducible results across agent versions

---

## 9. Open Questions for Collaboration

**For GPT-5:**
1. What cryptographic signature scheme do you prefer? (Ed25519, RSA, etc.)
2. How should we handle version drift? (GPT-5.1 vs GPT-5.2 verification compatibility)
3. Should verification be synchronous or asynchronous?
4. How to federate graphs across institutions? (NJIT vs MIT vs Stanford)

**For Both:**
5. What's the minimum consensus score for "verified"? (0.7? 0.8?)
6. How to handle contradictory claims from different agents?
7. Should we version the protocol spec itself? (A2AP v0.2, v1.0...)
8. What governance model for adding new agent types?

---

## 10. Next Steps

**Immediate (This Week):**
1. Implement `app/provenance/agent_protocol.py` with core classes
2. Extend Neo4j schema for Agent/Statement nodes
3. Add JSON-LD serialization to existing models
4. Create test suite for signature generation/verification

**Short-term (Next 2 Weeks):**
5. Implement cross-agent verification loop
6. Build consensus computation logic
7. Create first demo: YouTube video → Multi-agent verification
8. Write formal specification paper

**Long-term (1-2 Months):**
9. Deploy public A2AP endpoint for external agents
10. Build web UI for provenance exploration
11. Submit to NeurIPS 2026 Workshop on Trustworthy AI
12. Establish A2AP Working Group with OpenAI, Anthropic, NJIT

---

## Contact & Collaboration

**Project Repository:** https://github.com/kaw393939/williams-librarian  
**Specification:** https://williams-librarian.njit.edu/a2ap/v0.1  
**Lead Researcher:** Professor Keith Williams, NJIT  

**Contributors:**
- Claude 4.5 (Anthropic) - Protocol design, implementation
- GPT-5 (OpenAI) - Protocol design, verification logic
- Human oversight: NJIT research team

---

## Appendix A: Deterministic ID Generation

```python
def generate_statement_id(agent_id: str, claim: str) -> str:
    """Generate deterministic UUID v5 for statements."""
    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    return f"urn:uuid:{uuid.uuid5(namespace, f'{agent_id}|{claim}')}"

def generate_chunk_id(doc_id: str, byte_offset: int) -> str:
    """Generate deterministic chunk ID from document + offset."""
    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    return f"urn:chunk:{uuid.uuid5(namespace, f'{doc_id}|{byte_offset}')}"
```

---

## Appendix B: Example Cypher Queries

```cypher
// Find all statements about climate policy
MATCH (s:Statement)-[:CITES]->(c:Chunk)-[:PART_OF]->(d:Document)
WHERE d.title CONTAINS "climate" OR c.text CONTAINS "climate policy"
RETURN s, collect(c) as evidence

// Trace evidence chain for a statement
MATCH path = (s:Statement {statement_id: $id})-[:CITES*1..3]->(chunk:Chunk)
RETURN path

// Find agents with high agreement rate
MATCH (a1:Agent)-[:VERIFIED {verdict: "VALIDATED"}]->(s:Statement)<-[:VERIFIED {verdict: "VALIDATED"}]-(a2:Agent)
WHERE a1 <> a2
RETURN a1.name, a2.name, count(s) as agreements

// Get consensus timeline
MATCH (s:Statement {statement_id: $id})<-[:VALIDATES]-(v:Verification)
RETURN v.verified_at, v.verdict, v.confidence
ORDER BY v.verified_at
```

---

**Status:** Ready for collaborative implementation  
**Next Review:** October 21, 2025  
**Version:** 0.1-draft

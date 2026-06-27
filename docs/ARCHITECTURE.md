# Security Copilot - System Architecture

## Overview

Security Copilot is built as a modular, scalable RAG (Retrieval-Augmented Generation) system designed for enterprise security operations. This document details the architectural decisions, data flows, and component interactions.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Web UI     │  │  API Client  │  │   CLI Tool   │         │
│  │  (React)     │  │  (Python)    │  │   (Future)   │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │ HTTPS/REST API
┌─────────────────────────────▼─────────────────────────────────┐
│                      API Gateway Layer                         │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              FastAPI Application                          │ │
│  │  - CORS Middleware                                        │ │
│  │  - Authentication Middleware (JWT)                        │ │
│  │  - Rate Limiting                                          │ │
│  │  - Request Logging                                        │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬─────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────┐
│                    Business Logic Layer                        │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                  RAG Pipeline Orchestrator                │ │
│  │                                                            │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │ │
│  │  │   Input      │→ │   Hybrid     │→ │  Reranking   │  │ │
│  │  │ Validation   │  │   Search     │  │              │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │ │
│  │         ↓                  ↓                  ↓          │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │ │
│  │  │   Context    │→ │     LLM      │→ │   Output     │  │ │
│  │  │   Building   │  │  Generation  │  │ Validation   │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Ingestion Pipeline                           │ │
│  │  - MITRE ATT&CK Ingestor                                 │ │
│  │  - CVE/NVD Ingestor                                      │ │
│  │  - Security Log Ingestor                                 │ │
│  │  - Playbook Ingestor                                     │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬─────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────┐
│                      Data Layer                                │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐ │
│  │  Qdrant          │  │  PostgreSQL      │  │   Redis     │ │
│  │  (Vector DB)     │  │  (Metadata)      │  │  (Cache)    │ │
│  │                  │  │                  │  │             │ │
│  │  - Embeddings    │  │  - Documents     │  │  - Query    │ │
│  │  - Collections   │  │  - Techniques    │  │    Cache    │ │
│  │  - Indexes       │  │  - CVEs          │  │  - Session  │ │
│  │                  │  │  - Logs          │  │    Data     │ │
│  │                  │  │  - Playbooks     │  │             │ │
│  │                  │  │  - Query History │  │             │ │
│  └──────────────────┘  └──────────────────┘  └─────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. API Gateway Layer

**FastAPI Application** (`app/main.py`)
- Async request handling
- Automatic API documentation (Swagger/ReDoc)
- Request validation with Pydantic
- Middleware stack for cross-cutting concerns

**Middleware Stack:**
1. CORS - Cross-origin resource sharing
2. Authentication - JWT token validation
3. Rate Limiting - Request throttling
4. Logging - Structured request/response logging
5. Error Handling - Centralized exception handling

### 2. RAG Pipeline

**Pipeline Stages:**

```
User Query
    ↓
┌───────────────────────┐
│  1. Input Validation  │
│  - Sanitization       │
│  - Injection Detection│
│  - Length Check       │
└──────────┬────────────┘
           ↓
┌───────────────────────┐
│  2. Query Processing  │
│  - Classification     │
│  - Embedding Gen      │
└──────────┬────────────┘
           ↓
┌───────────────────────┐
│  3. Hybrid Search     │
│  - Semantic (Vector)  │
│  - Keyword (BM25)     │
│  - Score Fusion       │
└──────────┬────────────┘
           ↓
┌───────────────────────┐
│  4. Reranking         │
│  - Cross-Encoder      │
│  - Score Refinement   │
└──────────┬────────────┘
           ↓
┌───────────────────────┐
│  5. Context Building  │
│  - Source Selection   │
│  - Citation Format    │
│  - Truncation         │
└──────────┬────────────┘
           ↓
┌───────────────────────┐
│  6. LLM Generation    │
│  - Prompt Assembly    │
│  - API Call           │
│  - Streaming          │
└──────────┬────────────┘
           ↓
┌───────────────────────┐
│  7. Output Validation │
│  - Hallucination Check│
│  - Citation Verify    │
│  - Confidence Score   │
└──────────┬────────────┘
           ↓
    Response to User
```

### 3. Data Ingestion Pipeline

**Ingestion Flow:**

```
Data Source (MITRE/CVE/Logs/Playbooks)
    ↓
┌───────────────────────┐
│  Fetch Raw Data       │
│  - API Calls          │
│  - File Reading       │
└──────────┬────────────┘
           ↓
┌───────────────────────┐
│  Validation           │
│  - Schema Check       │
│  - Required Fields    │
└──────────┬────────────┘
           ↓
┌───────────────────────┐
│  Semantic Chunking    │
│  - Context Preserve   │
│  - Overlap            │
└──────────┬────────────┘
           ↓
┌───────────────────────┐
│  Embedding Generation │
│  - Batch Processing   │
│  - OpenAI/Local       │
└──────────┬────────────┘
           ↓
┌───────────────────────┐
│  Storage              │
│  - Qdrant (Vectors)   │
│  - PostgreSQL (Meta)  │
└───────────────────────┘
```

## Data Models

### Vector Database (Qdrant)

**Collections:**
- `mitre_techniques` - MITRE ATT&CK techniques
- `cve_entries` - CVE vulnerabilities
- `security_logs` - Security event logs
- `soc_playbooks` - Incident response playbooks

**Point Structure:**
```python
{
    "id": "mitre_T1059_chunk_0",
    "vector": [0.123, 0.456, ...],  # 384 or 1536 dimensions
    "payload": {
        "doc_id": "mitre_T1059",
        "content": "Technique description...",
        "source_type": "mitre",
        "metadata": {
            "technique_id": "T1059",
            "technique_name": "Command and Scripting Interpreter",
            "tactic": "Execution",
            "platforms": ["Windows", "Linux", "macOS"]
        },
        "chunk_index": 0
    }
}
```

### Relational Database (PostgreSQL)

**Key Tables:**
- `documents` - All ingested documents
- `mitre_techniques` - MITRE ATT&CK metadata
- `cve_entries` - CVE vulnerability metadata
- `security_logs` - Security log metadata
- `soc_playbooks` - Playbook metadata
- `query_history` - Query analytics
- `ingestion_jobs` - Job tracking

## Search Strategy

### Hybrid Search Algorithm

```python
def hybrid_search(query, vector_weight=0.7):
    # 1. Generate query embedding
    query_vector = embed(query)
    
    # 2. Semantic search (vector similarity)
    semantic_results = qdrant.search(
        vector=query_vector,
        limit=20
    )
    
    # 3. Keyword search (BM25-style)
    keyword_results = qdrant.search(
        filter=text_match(query),
        limit=20
    )
    
    # 4. Score fusion
    combined = {}
    for result in semantic_results:
        combined[result.id] = {
            'semantic': result.score,
            'keyword': 0.0
        }
    
    for result in keyword_results:
        if result.id in combined:
            combined[result.id]['keyword'] = result.score
        else:
            combined[result.id] = {
                'semantic': 0.0,
                'keyword': result.score
            }
    
    # 5. Weighted combination
    for doc_id, scores in combined.items():
        combined[doc_id]['final'] = (
            vector_weight * scores['semantic'] +
            (1 - vector_weight) * scores['keyword']
        )
    
    # 6. Sort and return
    return sorted(combined.items(), 
                  key=lambda x: x[1]['final'], 
                  reverse=True)
```

### Reranking Strategy

```python
def rerank(query, results, top_k=5):
    # 1. Prepare query-document pairs
    pairs = [(query, result.content) for result in results]
    
    # 2. Cross-encoder scoring
    scores = cross_encoder.predict(pairs)
    
    # 3. Combine with original scores
    for result, score in zip(results, scores):
        result.rerank_score = score
        result.fused_score = (
            0.4 * result.original_score +
            0.6 * score
        )
    
    # 4. Sort and return top-k
    return sorted(results, 
                  key=lambda x: x.fused_score, 
                  reverse=True)[:top_k]
```

## Security Architecture

### Defense in Depth

**Layer 1: Network Security**
- HTTPS/TLS encryption
- Firewall rules
- VPC isolation (cloud)

**Layer 2: Application Security**
- Input validation
- Prompt injection detection
- Output sanitization
- Rate limiting

**Layer 3: Data Security**
- Encryption at rest
- Encryption in transit
- Access control
- Audit logging

**Layer 4: LLM Security**
- Guardrails
- Hallucination detection
- Citation verification
- Confidence scoring

### Guardrails Implementation

```python
class Guardrails:
    def check_input(self, user_input):
        # Detect prompt injection
        if self.detect_injection(user_input):
            raise SecurityError("Prompt injection detected")
        
        # Sanitize input
        sanitized = self.sanitize(user_input)
        
        return sanitized
    
    def check_output(self, llm_output, sources):
        issues = []
        
        # Check for hallucinated CVE IDs
        output_cves = extract_cves(llm_output)
        source_cves = extract_cves_from_sources(sources)
        hallucinated = output_cves - source_cves
        
        if hallucinated:
            issues.append({
                'type': 'hallucinated_cve',
                'severity': 'critical',
                'details': hallucinated
            })
        
        # Check for hallucinated MITRE techniques
        # Similar logic...
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
```

## Scalability Considerations

### Horizontal Scaling

**API Layer:**
- Multiple FastAPI instances behind load balancer
- Stateless design for easy scaling
- Session data in Redis

**Database Layer:**
- Qdrant: Horizontal scaling with sharding
- PostgreSQL: Read replicas for queries
- Redis: Cluster mode for caching

### Performance Optimization

**Caching Strategy:**
```
┌─────────────────────────────────────┐
│  Cache Layers                       │
├─────────────────────────────────────┤
│  L1: In-Memory (LRU)                │
│  - Frequent queries                 │
│  - Embeddings                       │
├─────────────────────────────────────┤
│  L2: Redis                          │
│  - Query results                    │
│  - Session data                     │
├─────────────────────────────────────┤
│  L3: Database                       │
│  - Persistent storage               │
└─────────────────────────────────────┘
```

**Batch Processing:**
- Batch embedding generation
- Batch database operations
- Parallel ingestion workers

## Monitoring & Observability

### Metrics to Track

**Application Metrics:**
- Request rate (req/sec)
- Response time (P50, P95, P99)
- Error rate
- Cache hit rate

**RAG Metrics:**
- Retrieval accuracy
- Reranking effectiveness
- Confidence scores distribution
- Hallucination rate

**Infrastructure Metrics:**
- CPU/Memory usage
- Database connections
- Vector DB query time
- LLM API latency

### Logging Strategy

```python
# Structured logging
logger.info(
    "RAG query processed",
    extra={
        "query_id": query_id,
        "query_type": "alert_explanation",
        "response_time_ms": 1234,
        "confidence_score": 0.87,
        "num_sources": 5,
        "hallucination_detected": False
    }
)
```

## Deployment Architectures

### Development
```
Single Machine:
- Docker Compose
- All services on localhost
- SQLite option for PostgreSQL
```

### Production (Small)
```
Single Server:
- Docker Compose with resource limits
- Nginx reverse proxy
- SSL/TLS termination
- Backup strategy
```

### Production (Large)
```
Kubernetes Cluster:
- Multiple API pods (auto-scaling)
- Qdrant StatefulSet
- PostgreSQL with replication
- Redis cluster
- Ingress controller
- Monitoring stack (Prometheus/Grafana)
```

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API | FastAPI | Async web framework |
| LLM | OpenAI GPT-4 / Ollama | Text generation |
| Embeddings | OpenAI / sentence-transformers | Vector generation |
| Vector DB | Qdrant | Similarity search |
| Relational DB | PostgreSQL | Metadata storage |
| Cache | Redis | Query caching |
| Container | Docker | Deployment |
| Orchestration | Docker Compose / K8s | Service management |
| Monitoring | Prometheus + Grafana | Observability |

## Design Patterns Used

1. **Repository Pattern** - Database access abstraction
2. **Strategy Pattern** - Different chunking strategies
3. **Factory Pattern** - LLM provider creation
4. **Pipeline Pattern** - RAG processing stages
5. **Singleton Pattern** - Shared resource instances
6. **Observer Pattern** - Event-driven ingestion
7. **Adapter Pattern** - Multi-provider LLM interface

---

This architecture is designed for:
- ✅ Scalability
- ✅ Maintainability
- ✅ Security
- ✅ Performance
- ✅ Extensibility

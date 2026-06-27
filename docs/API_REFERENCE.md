# Security Copilot - API Reference

## Base URL
```
http://localhost:8000
```

## Authentication
Currently no authentication required for local development. In production, implement JWT-based authentication.

---

## Query Endpoints

### 1. General RAG Query

**Endpoint:** `POST /api/v1/query`

**Description:** General purpose security query with RAG

**Request Body:**
```json
{
  "query": "What is MITRE technique T1059?",
  "top_k": 10,
  "rerank_top_k": 5,
  "source_types": ["mitre", "cve", "logs", "playbooks"],
  "filters": {},
  "stream": false
}
```

**Parameters:**
- `query` (string, required): The security question or query
- `top_k` (integer, optional): Number of documents to retrieve (default: 10)
- `rerank_top_k` (integer, optional): Number of documents after reranking (default: 5)
- `source_types` (array, optional): Filter by source types
- `filters` (object, optional): Additional metadata filters
- `stream` (boolean, optional): Enable streaming response (default: false)

**Response:**
```json
{
  "success": true,
  "answer": "MITRE technique T1059 is Command and Scripting Interpreter...",
  "sources": [
    {
      "index": 1,
      "doc_id": "mitre_T1059",
      "title": "MITRE T1059: Command and Scripting Interpreter",
      "source_type": "mitre",
      "content": "...",
      "relevance_score": 0.95,
      "metadata": {
        "technique_id": "T1059",
        "tactic": "Execution"
      }
    }
  ],
  "confidence_score": 0.87,
  "token_count": 450,
  "response_time_ms": 1234,
  "metadata": {
    "query_type": "threat_intel",
    "num_sources": 5
  }
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is MITRE technique T1059?",
    "top_k": 5
  }'
```

---

### 2. Streaming Query

**Endpoint:** `POST /api/v1/query/stream`

**Description:** Stream RAG responses in real-time

**Request:** Same as general query with `stream: true`

**Response:** Server-Sent Events (SSE) stream

```
data: {"type": "metadata", "sources": [...], "num_sources": 5}

data: {"type": "content", "content": "MITRE technique"}

data: {"type": "content", "content": " T1059 is"}

data: {"type": "complete", "confidence_score": 0.87}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/query/stream" \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain T1059", "stream": true}'
```

---

### 3. Alert Explanation

**Endpoint:** `POST /api/v1/alert/explain`

**Description:** Explain security alerts with MITRE mapping

**Request Body:**
```json
{
  "query": "Suspicious PowerShell execution with encoded command detected on WORKSTATION01",
  "top_k": 5
}
```

**Response:** Same format as general query

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/alert/explain" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Multiple failed SSH login attempts from 192.168.1.100"
  }'
```

---

### 4. CVE Lookup

**Endpoint:** `POST /api/v1/cve/lookup`

**Description:** Get detailed CVE vulnerability information

**Request Body:**
```json
{
  "query": "CVE-2024-1234",
  "top_k": 5
}
```

**Response:** Same format as general query with CVE-specific sources

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/cve/lookup" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "CVE-2024-1234"
  }'
```

---

### 5. Incident Response Guidance

**Endpoint:** `POST /api/v1/incident/guidance`

**Description:** Get incident response procedures and playbook guidance

**Request Body:**
```json
{
  "query": "Ransomware detected on file server, files being encrypted",
  "top_k": 5
}
```

**Response:** Same format with playbook sources

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/incident/guidance" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Phishing email with malicious attachment clicked by user"
  }'
```

---

### 6. Threat Intelligence

**Endpoint:** `POST /api/v1/threat/intel`

**Description:** Query threat intelligence and MITRE ATT&CK

**Request Body:**
```json
{
  "query": "What are common lateral movement techniques?",
  "top_k": 10
}
```

**Response:** Same format with MITRE and threat intel sources

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/threat/intel" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain credential dumping techniques"
  }'
```

---

## Ingestion Endpoints

### 7. Start Ingestion

**Endpoint:** `POST /api/v1/ingest`

**Description:** Start data ingestion for a source type

**Request Body:**
```json
{
  "source_type": "mitre",
  "force_refresh": false,
  "batch_size": 100
}
```

**Parameters:**
- `source_type` (string, required): One of: "mitre", "cve", "logs", "playbooks"
- `force_refresh` (boolean, optional): Force re-ingestion (default: false)
- `batch_size` (integer, optional): Batch size for processing (default: 100)

**Response:**
```json
{
  "job_id": "job_mitre_12345",
  "status": "started",
  "message": "Ingestion job started for mitre"
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "mitre",
    "batch_size": 50
  }'
```

---

### 8. Get Ingestion Status

**Endpoint:** `GET /api/v1/ingest/{job_id}`

**Description:** Check status of ingestion job

**Response:**
```json
{
  "job_id": "job_mitre_12345",
  "source_type": "mitre",
  "status": "running",
  "progress": 0.65,
  "total_items": 100,
  "processed_items": 65,
  "failed_items": 2,
  "error_message": null
}
```

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/ingest/job_mitre_12345"
```

---

### 9. List Available Sources

**Endpoint:** `GET /api/v1/ingest/sources`

**Description:** List all available data sources

**Response:**
```json
{
  "sources": [
    {
      "name": "mitre",
      "description": "MITRE ATT&CK techniques and tactics",
      "enabled": true
    },
    {
      "name": "cve",
      "description": "CVE vulnerability database",
      "enabled": true
    },
    {
      "name": "logs",
      "description": "Security logs (Sysmon, Windows Event, etc.)",
      "enabled": true
    },
    {
      "name": "playbooks",
      "description": "SOC incident response playbooks",
      "enabled": true
    }
  ]
}
```

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/ingest/sources"
```

---

## Health Endpoints

### 10. Basic Health Check

**Endpoint:** `GET /api/v1/health`

**Description:** Basic health check

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000",
  "service": "security-copilot",
  "version": "0.1.0"
}
```

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/health"
```

---

### 11. Detailed Health Check

**Endpoint:** `GET /api/v1/health/detailed`

**Description:** Detailed health check with service status

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000",
  "service": "security-copilot",
  "version": "0.1.0",
  "services": {
    "postgres": {
      "status": "healthy",
      "description": "PostgreSQL metadata database"
    },
    "qdrant": {
      "status": "healthy",
      "description": "Qdrant vector database"
    }
  }
}
```

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/health/detailed"
```

---

### 12. Readiness Check

**Endpoint:** `GET /api/v1/health/ready`

**Description:** Kubernetes-style readiness probe

**Response:**
```json
{
  "status": "ready"
}
```

**cURL Example:**
```bash
curl "http://localhost:8000/api/v1/health/ready"
```

---

## Error Responses

All endpoints return standard error responses:

**400 Bad Request:**
```json
{
  "detail": "Invalid source type: unknown"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Query processing failed: Connection timeout"
}
```

---

## Rate Limiting

Currently no rate limiting in development. In production:
- 100 requests per minute per IP
- 1000 requests per hour per IP

---

## Python Client Example

```python
import httpx
import asyncio

class SecurityCopilotClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def query(self, query: str, top_k: int = 10):
        response = await self.client.post(
            f"{self.base_url}/api/v1/query",
            json={"query": query, "top_k": top_k}
        )
        return response.json()
    
    async def explain_alert(self, alert: str):
        response = await self.client.post(
            f"{self.base_url}/api/v1/alert/explain",
            json={"query": alert}
        )
        return response.json()
    
    async def lookup_cve(self, cve_id: str):
        response = await self.client.post(
            f"{self.base_url}/api/v1/cve/lookup",
            json={"query": cve_id}
        )
        return response.json()
    
    async def close(self):
        await self.client.aclose()

# Usage
async def main():
    client = SecurityCopilotClient()
    
    # Query
    result = await client.query("What is T1059?")
    print(result['answer'])
    
    # Explain alert
    alert_result = await client.explain_alert(
        "Suspicious PowerShell execution detected"
    )
    print(alert_result['answer'])
    
    await client.close()

asyncio.run(main())
```

---

## Interactive API Documentation

Visit these URLs for interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## WebSocket Support (Future)

Planned for real-time updates:
- `/ws/query` - Real-time query streaming
- `/ws/status` - Real-time ingestion status updates

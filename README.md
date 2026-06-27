# Security Copilot

**Production-Grade RAG-based Security Analysis System for SOC Analysts**

Security Copilot is an enterprise-ready AI assistant designed specifically for Security Operations Center (SOC) analysts. It leverages Retrieval-Augmented Generation (RAG) to provide intelligent, grounded responses about security alerts, vulnerabilities, incident response procedures, and threat intelligence.

## 🎯 Key Features

### Core Capabilities
- **Alert Explanation**: Understand security alerts and map them to MITRE ATT&CK techniques
- **CVE Lookup**: Get detailed vulnerability information with mitigation recommendations
- **Incident Response Advisor**: Access SOC playbooks and step-by-step response procedures
- **Threat Intelligence**: Query MITRE ATT&CK framework and security knowledge base

### Technical Features
- **Hybrid Search**: Combines semantic (vector) and keyword (BM25) search for optimal retrieval
- **Cross-Encoder Reranking**: Refines search results for maximum precision
- **Multi-Provider LLM Support**: Works with OpenAI GPT-4 and local models via Ollama
- **Hallucination Detection**: Validates CVE IDs, MITRE technique IDs, and prevents fabricated information
- **Source Citations**: All responses include verifiable source references
- **Streaming Responses**: Real-time response generation via Server-Sent Events

### Security Features
- **Authentication**: JWT token-based and API key authentication
- **Authorization**: Role-based access control (admin/user roles)
- **Rate Limiting**: Configurable rate limits per user/IP
- **Security Headers**: CORS, CSP, and other security headers
- **Input Validation**: Guardrails for query sanitization and length limits
- **Error Sanitization**: Sensitive information redacted from error messages

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface                          │
│              (React + TailwindCSS + Vite)                   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │Query Endpoint│  │Ingest Endpoint│  │Auth Endpoint │     │
│  │(Streaming)   │  │(Admin Only)   │  │(JWT/API Key) │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼──────────────────┼──────────────────┼────────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼────────────┐
│              Security & Middleware Layer                     │
│  - Rate Limiting (SlowAPI + Redis)                          │
│  - Security Headers (CORS, CSP)                             │
│  - Request Size Limits                                       │
│  - Error Sanitization                                       │
└─────────┬──────────────────┬──────────────────────────────┘
          │                  │
┌─────────▼──────────────────▼──────────────────────────────┐
│                   RAG Pipeline                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ 1. Input Validation (Guardrails)                     │ │
│  │ 2. Hybrid Search (Semantic + Keyword)                │ │
│  │ 3. Cross-Encoder Reranking                           │ │
│  │ 4. Context Building with Citations                   │ │
│  │ 5. LLM Generation (OpenAI/Ollama)                    │ │
│  │ 6. Output Validation & Hallucination Detection       │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────┬──────────────────┬──────────────────────────────┘
          │                  │
┌─────────▼──────────┐  ┌────▼────────────────────────────┐
│  Qdrant (Vectors)  │  │  PostgreSQL (Metadata)          │
│  - MITRE ATT&CK    │  │  - Users & API Keys             │
│  - CVE Database    │  │  - Documents                    │
│  - Security Logs   │  │  - Query History                │
│  - SOC Playbooks   │  │  - Ingestion Jobs               │
└────────────────────┘  └─────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Node.js 20+ (for frontend)
- OpenAI API key (or Ollama for local models)
- 8GB+ RAM recommended

### Quick Start with Docker

The fastest way to get started is using Docker Compose:

```bash
# 1. Clone the repository
git clone <repository-url>
cd Security_CoPilot

# 2. Set up environment variables
cp .env.example .env
# Edit .env and add your OpenAI API key and other settings

# 3. Start all services
cd docker
docker-compose up -d

# 4. Initialize database and create admin user
docker-compose exec backend python -m app.database.bootstrap

# 5. Run data ingestion (via API)
curl -X POST http://localhost:8000/api/ingest/mitre \
  -H "X-API-Key: your-api-key"

# 6. Access the application
# Frontend: http://localhost
# API Docs: http://localhost:8000/docs (disable in production)
```

### Manual Development Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd Security_CoPilot
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key and other settings
```

3. **Start infrastructure (Qdrant + PostgreSQL + Redis)**
```bash
cd docker
docker-compose up -d qdrant postgres redis
```

4. **Create virtual environment and install dependencies**
```bash
python -m venv venv

# On Windows
.\venv\Scripts\activate

# On Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

5. **Initialize database and create admin user**
```bash
python -m app.database.bootstrap
```

6. **Run data ingestion**
```bash
# Ingest MITRE ATT&CK data
python -m app.ingestion.mitre_ingestion

# Ingest sample CVE data
python -m app.ingestion.cve_ingestion

# Ingest sample playbooks
python -m app.ingestion.playbook_ingestion
```

7. **Start the backend**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

8. **Start the frontend (optional)**
```bash
cd frontend
npm install
npm run dev
```

9. **Access the application**
- Frontend: http://localhost:5173
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## 📝 Configuration

### Environment Variables

```bash
# Application
APP_NAME=Security Copilot
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Security
JWT_SECRET_KEY=your-secret-key-minimum-32-characters-long
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Ollama Configuration (Optional)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Vector Database (Qdrant)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Optional

# PostgreSQL
POSTGRES_URL=postgresql://user:password@localhost:5432/seccopilot

# Redis (Optional - for caching and rate limiting)
REDIS_URL=redis://localhost:6379/0

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60

# Retrieval Configuration
DEFAULT_TOP_K=10
RERANK_TOP_K=5
EMBEDDING_MODEL=all-MiniLM-L6-v2
USE_OPENAI=true  # Set to false to use local embeddings
```

## 🔍 Usage Examples

### Authentication

```bash
# Login to get JWT token
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-password"
  }'

# Use API key for authentication
curl -X GET "http://localhost:8000/api/auth/current" \
  -H "X-API-Key: your-api-key"
```

### Query API

```bash
# Query with streaming (recommended)
curl -X POST "http://localhost:8000/api/query/stream" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "What is MITRE technique T1059?",
    "sources": ["mitre", "cve", "logs", "playbooks"],
    "top_k": 5
  }'

# Query without streaming
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "Explain Sysmon Event ID 1 with suspicious PowerShell command line",
    "sources": ["mitre", "logs"],
    "top_k": 10
  }'
```

### Ingestion API (Admin Only)

```bash
# Trigger MITRE data ingestion
curl -X POST "http://localhost:8000/api/ingest/mitre" \
  -H "X-API-Key: admin-api-key"

# Trigger CVE data ingestion
curl -X POST "http://localhost:8000/api/ingest/cve" \
  -H "X-API-Key: admin-api-key"

# Check ingestion job status
curl -X GET "http://localhost:8000/api/ingest/status/job-id" \
  -H "X-API-Key: admin-api-key"
```

## 🏗️ Project Structure

```
security-copilot/
├── app/
│   ├── core/               # Core utilities
│   │   ├── logging_config.py
│   │   ├── security.py     # Password hashing, JWT
│   │   ├── cache.py        # Redis caching
│   │   ├── middleware.py   # Security headers, rate limiting
│   │   ├── limiter.py      # Rate limiting
│   │   ├── errors.py       # Error handling
│   │   └── guardrails.py   # Input validation
│   ├── ingestion/          # Data ingestion pipeline
│   │   ├── base.py         # Base ingestor interface
│   │   ├── mitre_ingestion.py
│   │   ├── cve_ingestion.py
│   │   ├── log_ingestion.py
│   │   ├── playbook_ingestion.py
│   │   ├── chunking.py     # Semantic chunking
│   │   └── embeddings.py   # Embedding generation
│   ├── retrieval/          # RAG retrieval system
│   │   ├── vector_store.py # Qdrant interface
│   │   ├── hybrid_search.py
│   │   ├── reranker.py     # Cross-encoder reranking
│   │   ├── context_builder.py
│   │   └── rag_pipeline.py # Complete RAG orchestration
│   ├── llm/                # LLM providers
│   │   ├── provider.py     # Abstract provider
│   │   ├── openai_provider.py
│   │   ├── ollama_provider.py
│   │   └── prompts.py      # Prompt templates
│   ├── api/                # FastAPI routes
│   │   ├── dependencies.py # Auth dependencies
│   │   └── routes/
│   │       ├── auth.py     # Authentication endpoints
│   │       ├── query.py    # Query endpoints
│   │       └── ingest.py   # Ingestion endpoints
│   ├── database/           # Database models
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── postgres.py     # PostgreSQL connection
│   │   └── bootstrap.py    # Database initialization
│   ├── config.py           # Configuration management
│   └── main.py             # FastAPI application
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── nginx.conf
│   └── init.sql
├── frontend/               # React frontend
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
├── data/                   # Data storage
│   ├── raw/
│   ├── processed/
│   ├── sample_logs/
│   └── playbooks/
├── tests/                  # Test suite
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── pytest.ini
└── README.md
```

## 🔐 Security Features

### Authentication & Authorization
- **JWT Token Authentication**: Secure token-based auth with configurable expiration
- **API Key Authentication**: Alternative auth method for service accounts
- **Role-Based Access Control**: Admin and user roles with different permissions
- **Secure Password Hashing**: Using bcrypt with salt

### Input Validation
- **Query Length Limits**: Prevent abuse with maximum query length
- **Input Sanitization**: Remove potentially dangerous patterns
- **Guardrails**: Validate and sanitize user inputs
- **Prompt Injection Detection**: Basic protection against prompt injection

### Rate Limiting
- **Per-User Rate Limits**: Configurable limits per user/IP
- **Redis-backed**: Distributed rate limiting with Redis
- **SlowAPI Integration**: Easy-to-configure rate limiting middleware

### Security Headers
- **CORS Configuration**: Configurable cross-origin resource sharing
- **Content Security Policy**: Prevent XSS attacks
- **Security Headers**: X-Frame-Options, X-Content-Type-Options, etc.

### Output Validation
- **CVE ID Verification**: Validate CVE IDs against sources
- **MITRE Technique ID Validation**: Ensure technique IDs exist
- **Citation Accuracy**: Check that citations are valid
- **Hallucination Detection**: Detect and prevent fabricated information

### Error Sanitization
- **Sensitive Data Redaction**: Remove passwords, API keys, paths from errors
- **Generic Error Messages**: Prevent information leakage
- **Structured Logging**: Secure logging without sensitive data

## 📊 Evaluation Metrics

The system tracks multiple quality metrics:

- **Retrieval Quality**: Top-K accuracy, MRR, NDCG
- **Response Quality**: Groundedness score, citation accuracy, hallucination rate
- **Performance**: P50/P95/P99 latency, throughput
- **User Satisfaction**: Feedback scores, query success rate

## 🛠️ Development

### Running Tests
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test categories
pytest tests/unit/ -m unit
pytest tests/integration/ -m integration
```

### Code Formatting
```bash
# Format code with black
black app/ tests/

# Lint with ruff
ruff check app/ tests/

# Type checking with mypy
mypy app/
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

## 🚢 Deployment

### Docker Deployment

```bash
# Build and start all services
cd docker
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Production Considerations
- **Environment Variables**: Use environment-specific `.env` files
- **HTTPS/TLS**: Enable SSL/TLS for production
- **Secrets Management**: Use AWS Secrets Manager, HashiCorp Vault, or similar
- **Monitoring**: Set up Prometheus/Grafana for metrics
- **Logging**: Configure centralized logging (ELK, CloudWatch, etc.)
- **Rate Limiting**: Adjust rate limits based on traffic
- **Database Backups**: Regular PostgreSQL backups
- **Vector Store Backups**: Qdrant snapshots
- **API Documentation**: Disable `/docs` in production
- **CORS**: Restrict CORS origins to trusted domains
- **Health Checks**: Configure proper health check endpoints

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- **MITRE ATT&CK**: For the comprehensive threat framework
- **NVD**: For CVE vulnerability data
- **OpenAI**: For GPT-4 and embedding models
- **Qdrant**: For the excellent vector database
- **FastAPI**: For the modern Python web framework

## 📞 Support

For issues, questions, or contributions:
- GitHub Issues: [Create an issue]
- Documentation: See `/docs` directory
- Email: security-copilot@example.com

---

**Built with ❤️ for SOC Analysts**

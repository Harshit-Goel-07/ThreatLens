# Security Copilot - Setup Guide

This guide will walk you through setting up Security Copilot from scratch.

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Quick Start with Docker](#quick-start-with-docker)
3. [Manual Development Setup](#manual-development-setup)
4. [Configuration](#configuration)
5. [Authentication Setup](#authentication-setup)
6. [Data Ingestion](#data-ingestion)
7. [Testing the System](#testing-the-system)
8. [Troubleshooting](#troubleshooting)

## System Requirements

### Hardware
- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 10GB+ free space
- **Network**: Internet connection for API calls and data downloads

### Software
- **Python**: 3.11 or higher
- **Docker**: Latest version
- **Docker Compose**: v2.0+
- **Node.js**: 20+ (for frontend development)
- **Git**: For cloning the repository

### API Keys
- **OpenAI API Key**: Required for GPT-4 and embeddings (or use Ollama for local models)

## Quick Start with Docker

The fastest way to get Security Copilot running is using Docker Compose.

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Security_CoPilot
```

### 2. Set Up Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your favorite editor
# Windows: notepad .env
# Linux/Mac: nano .env or vim .env
```

**Required Configuration:**
```bash
# OpenAI Configuration (Required)
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Security (Required)
JWT_SECRET_KEY=your-secret-key-minimum-32-characters-long

# Database Configuration (Use defaults for local development)
QDRANT_URL=http://localhost:6333
POSTGRES_URL=postgresql://seccopilot:secure_password@localhost:5432/seccopilot
REDIS_URL=redis://localhost:6379/0
```

### 3. Start All Services

```bash
# Navigate to docker directory
cd docker

# Start all services (backend, frontend, qdrant, postgres, redis)
docker-compose up -d

# Verify services are running
docker-compose ps

# Check logs if needed
docker-compose logs -f backend
```

**Expected Output:**
```
NAME                    STATUS              PORTS
seccopilot-qdrant      Up 10 seconds       0.0.0.0:6333->6333/tcp
seccopilot-postgres    Up 10 seconds       0.0.0.0:5432->5432/tcp
seccopilot-redis      Up 10 seconds       0.0.0.0:6379->6379/tcp
seccopilot-backend     Up 10 seconds       0.0.0.0:8000->8000/tcp
seccopilot-frontend    Up 10 seconds       0.0.0.0:80->80/tcp
```

### 4. Initialize Database and Create Admin User

```bash
# Initialize database and create bootstrap admin user
docker-compose exec backend python -m app.database.bootstrap
```

This will create an admin user with:
- Username: `admin`
- Password: `admin123` (change this immediately after first login)
- API Key: Generated and displayed in output

### 5. Access the Application

- **Frontend**: http://localhost
- **API Documentation**: http://localhost:8000/docs (disable in production)
- **Health Check**: http://localhost:8000/health

## Manual Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Security_CoPilot
```

### 2. Set Up Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your favorite editor
# Windows: notepad .env
# Linux/Mac: nano .env or vim .env
```

**Required Configuration:**
```bash
# OpenAI Configuration (Required)
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Security (Required)
JWT_SECRET_KEY=your-secret-key-minimum-32-characters-long

# Database Configuration (Use defaults for local development)
QDRANT_URL=http://localhost:6333
POSTGRES_URL=postgresql://seccopilot:secure_password@localhost:5432/seccopilot
REDIS_URL=redis://localhost:6379/0
```

### 3. Start Infrastructure Services

```bash
# Navigate to docker directory
cd docker

# Start Qdrant, PostgreSQL, and Redis
docker-compose up -d qdrant postgres redis

# Verify services are running
docker-compose ps

# Check logs if needed
docker-compose logs qdrant
docker-compose logs postgres
```

**Expected Output:**
```
NAME                    STATUS              PORTS
seccopilot-qdrant      Up 10 seconds       0.0.0.0:6333->6333/tcp
seccopilot-postgres    Up 10 seconds       0.0.0.0:5432->5432/tcp
seccopilot-redis      Up 10 seconds       0.0.0.0:6379->6379/tcp
```

### 4. Set Up Python Environment

#### On Windows:
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

#### On Linux/Mac:
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 5. Initialize Database and Create Admin User

```bash
# Initialize database and create bootstrap admin user
python -m app.database.bootstrap
```

This will create an admin user with:
- Username: `admin`
- Password: `admin123` (change this immediately after first login)
- API Key: Generated and displayed in output

### 6. Set Up Frontend (Optional)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at http://localhost:5173

## Configuration

### OpenAI vs Ollama

#### Using OpenAI (Recommended for Production)
- Requires API key
- Best quality responses
- Costs per API call
- No local GPU needed

**Configuration:**
```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
USE_OPENAI=true
```

#### Using Ollama (Local Models)
- Free to use
- Runs locally
- Requires GPU for good performance
- Lower quality than GPT-4

**Setup:**
```bash
# Install Ollama
# Visit: https://ollama.ai/download

# Pull a model
ollama pull llama2

# Update .env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
USE_OPENAI=false
```

### Embedding Models

#### OpenAI Embeddings (Default)
```bash
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
USE_OPENAI=true
```

#### Local Embeddings (sentence-transformers)
```bash
EMBEDDING_MODEL=all-MiniLM-L6-v2
USE_OPENAI=false
```

### Rate Limiting

Rate limiting is enabled by default using Redis. Configure in `.env`:

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
```

If Redis is not available, rate limiting will fall back to in-memory limiting.

## Data Ingestion

### Automated Ingestion via API (Recommended)

After starting the backend, use the ingestion API:

```bash
# Trigger MITRE data ingestion (requires admin API key)
curl -X POST "http://localhost:8000/api/ingest/mitre" \
  -H "X-API-Key: your-admin-api-key"

# Trigger CVE data ingestion
curl -X POST "http://localhost:8000/api/ingest/cve" \
  -H "X-API-Key: your-admin-api-key"

# Trigger security log ingestion
curl -X POST "http://localhost:8000/api/ingest/logs" \
  -H "X-API-Key: your-admin-api-key"

# Trigger playbook ingestion
curl -X POST "http://localhost:8000/api/ingest/playbooks" \
  -H "X-API-Key: your-admin-api-key"

# Check ingestion job status
curl -X GET "http://localhost:8000/api/ingest/status/<job-id>" \
  -H "X-API-Key: your-admin-api-key"
```

### Manual Ingestion (Development)

You can also ingest data sources directly:

```bash
# Make sure virtual environment is activated

# MITRE ATT&CK
python -m app.ingestion.mitre_ingestion

# CVE Data
python -m app.ingestion.cve_ingestion

# Security Logs
python -m app.ingestion.log_ingestion

# Playbooks
python -m app.ingestion.playbook_ingestion
```

### Verify Ingestion

```bash
# Check Qdrant collections
curl http://localhost:6333/collections

# Expected output should show collections:
# - mitre_techniques
# - cve_entries
# - security_logs
# - soc_playbooks
```

## Testing the System

### 1. Start the Backend (Manual Setup Only)

```bash
# Make sure virtual environment is activated
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 2. Access API Documentation

Open your browser and navigate to:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 3. Test Health Endpoint

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000",
  "service": "security-copilot",
  "version": "0.1.0"
}
```

### 4. Test Authentication

```bash
# Test login
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'

# Test API key authentication
curl -X GET "http://localhost:8000/api/auth/current" \
  -H "X-API-Key: your-api-key"
```

### 5. Test Query Endpoint

```bash
# Test with API key
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "What is MITRE technique T1059?",
    "sources": ["mitre"],
    "top_k": 5
  }'
```

**Expected Response:**
```json
{
  "answer": "MITRE technique T1059 is Command and Scripting Interpreter...",
  "sources": [...],
  "confidence_score": 0.85
}
```

### 6. Test Streaming Query

```bash
# Test streaming with API key
curl -X POST "http://localhost:8000/api/query/stream" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "Explain MITRE technique T1059",
    "sources": ["mitre"],
    "top_k": 5
  }'
```

### 7. Run Test Suite

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## Troubleshooting

### Issue: Docker containers won't start

**Solution:**
```bash
# Check if ports are already in use
# Windows
netstat -ano | findstr :6333
netstat -ano | findstr :5432

# Linux/Mac
lsof -i :6333
lsof -i :5432

# Stop conflicting services or change ports in docker-compose.yml
```

### Issue: Authentication fails

**Symptoms:** 401 Unauthorized errors

**Solutions:**
1. Verify JWT_SECRET_KEY is at least 32 characters in `.env`
2. Check that admin user was created via bootstrap
3. Verify API key is correct
4. Check token expiration time

```bash
# Re-run bootstrap to recreate admin user
python -m app.database.bootstrap
```

### Issue: OpenAI API errors

**Symptoms:** `AuthenticationError` or `RateLimitError`

**Solutions:**
1. Verify API key is correct in `.env`
2. Check API key has sufficient credits
3. Verify API key has access to GPT-4 and embeddings
4. Check rate limits: https://platform.openai.com/account/rate-limits

### Issue: Ingestion fails

**Symptoms:** Errors during data ingestion

**Solutions:**
1. Check internet connection
2. Verify Qdrant and PostgreSQL are running
3. Check logs for specific errors
4. Try ingesting one source at a time

```bash
# Check Qdrant
curl http://localhost:6333/collections

# Check PostgreSQL
docker-compose logs postgres
```

### Issue: Rate limiting errors

**Symptoms:** 429 Too Many Requests

**Solutions:**
1. Adjust `RATE_LIMIT_PER_MINUTE` in `.env`
2. Check Redis is running if using Redis-backed rate limiting
3. Verify rate limiting is not misconfigured

```bash
# Check Redis
docker-compose logs redis
```

### Issue: Slow response times

**Causes:**
- Large number of documents
- Slow embedding generation
- Network latency to OpenAI

**Solutions:**
1. Reduce `top_k` parameter
2. Use local embeddings instead of OpenAI
3. Enable caching (Redis)
4. Optimize Qdrant index settings

### Issue: Import errors

**Symptoms:** `ModuleNotFoundError`

**Solution:**
```bash
# Ensure virtual environment is activated
# Windows
.\venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Database connection errors

**Solution:**
```bash
# Restart Docker containers
cd docker
docker-compose restart

# Check container logs
docker-compose logs qdrant
docker-compose logs postgres

# Verify connection strings in .env
```

### Issue: Frontend not connecting to backend

**Solution:**
1. Verify backend is running on port 8000
2. Check CORS configuration in `.env`
3. Verify frontend proxy configuration in `vite.config.js`
4. Check browser console for CORS errors

## Next Steps

After successful setup:

1. **Explore the API**: Use Swagger UI at http://localhost:8000/docs
2. **Test Different Queries**: Try alert explanations, CVE lookups, etc.
3. **Add Custom Data**: Add your own playbooks and logs to `data/` directories
4. **Configure for Production**: See production considerations in README
5. **Set Up Monitoring**: Configure logging and metrics
6. **Change Default Password**: Update admin password immediately

## Getting Help

- **Documentation**: Check README.md and other docs in `/docs` directory
- **GitHub Issues**: Report bugs or request features
- **Logs**: Check application logs for detailed error messages

```bash
# View application logs (manual setup)
tail -f logs/security-copilot.log

# View Docker logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Security Best Practices

1. **Change Default Password**: Change the admin password immediately after first login
2. **Secure JWT Secret**: Use a strong, randomly generated JWT_SECRET_KEY
3. **Disable API Docs in Production**: Remove or restrict access to `/docs` endpoint
4. **Use HTTPS**: Enable TLS/SSL for production deployments
5. **Restrict CORS**: Limit CORS origins to trusted domains
6. **Regular Updates**: Keep dependencies updated for security patches
7. **Backup Data**: Regular backups of PostgreSQL and Qdrant data
8. **Monitor Logs**: Set up centralized logging and monitoring

---

**Setup Complete! 🎉**

You're now ready to use Security Copilot. Try querying the system with security-related questions!

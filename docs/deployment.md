# Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Monitoring & Observability](#monitoring--observability)
6. [Backup & Recovery](#backup--recovery)
7. [Scaling](#scaling)

## Prerequisites

### System Requirements

**Minimum**:
- CPU: 2 cores
- RAM: 4 GB
- Disk: 20 GB (plus storage for library content)
- OS: Linux, macOS, or Windows with WSL2

**Recommended**:
- CPU: 4+ cores
- RAM: 8+ GB
- Disk: 100+ GB SSD
- OS: Linux (Ubuntu 22.04 or similar)

### Software Requirements

- Python 3.11+
- Docker 24.0+
- Docker Compose 2.20+
- PostgreSQL 15+
- Redis 7+
- Git

### API Keys

- **OpenAI API Key** (required)
- **OpenAI Organization ID** (optional)
- Plugin-specific keys (optional, based on enabled plugins)

## Local Development

### 1. Clone Repository

```bash
git clone https://github.com/kevinwilliams/williams-librarian.git
cd williams-librarian
```

### 2. Install Dependencies

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install

# Activate virtual environment
poetry shell
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your configuration
nano .env
```

**.env** file:
```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-...
OPENAI_ORG_ID=org-...  # Optional

# Model Configuration
SCREENING_MODEL=gpt-5-nano
SUMMARIZATION_MODEL=gpt-5-mini
ANALYSIS_MODEL=gpt-5

# Cost Management
MONTHLY_API_BUDGET=100.0

# Database URLs
POSTGRES_URL=postgresql://librarian:password@localhost:5432/librarian
REDIS_URL=redis://localhost:6379/0

# Storage Paths
LIBRARY_ROOT=./library
CHROMA_PERSIST_DIR=./data/chroma

# Feature Flags
ENABLE_WEB_SEARCH=false
ENABLE_FILE_SEARCH=true
ENABLE_KG_BUILDING=true
ENABLE_CODE_INTERPRETER=false

# Logging
LOG_LEVEL=INFO
LOG_FILE=./data/logs/app.log

# UI Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost
```

### 4. Start Services

```bash
# Start PostgreSQL and Redis using Docker
docker-compose up -d postgres redis

# Initialize databases
poetry run python scripts/init_db.py

# Verify services
docker-compose ps
```

### 5. Run Application

```bash
# Start Streamlit UI
poetry run streamlit run app/presentation/app.py

# In separate terminals, start workers
poetry run python -m app.workers.digest_worker
poetry run python -m app.workers.ingestion_worker
```

### 6. Access Application

Open browser to: http://localhost:8501

## Docker Deployment

### Docker Compose (All-in-One)

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: librarian-postgres
    environment:
      POSTGRES_DB: librarian
      POSTGRES_USER: librarian
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U librarian"]
      interval: 10s
      timeout: 5s
      retries: 5
  
  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: librarian-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
  
  # Main Application
  app:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: librarian-app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      OPENAI_ORG_ID: ${OPENAI_ORG_ID}
      POSTGRES_URL: postgresql://librarian:${POSTGRES_PASSWORD}@postgres:5432/librarian
      REDIS_URL: redis://redis:6379/0
      LIBRARY_ROOT: /data/library
      CHROMA_PERSIST_DIR: /data/chroma
    volumes:
      - library_data:/data/library
      - chroma_data:/data/chroma
      - logs:/data/logs
    ports:
      - "8501:8501"
    restart: unless-stopped
  
  # Digest Worker
  digest-worker:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: librarian-digest-worker
    depends_on:
      - postgres
      - redis
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      POSTGRES_URL: postgresql://librarian:${POSTGRES_PASSWORD}@postgres:5432/librarian
      REDIS_URL: redis://redis:6379/0
      LIBRARY_ROOT: /data/library
      CHROMA_PERSIST_DIR: /data/chroma
    volumes:
      - library_data:/data/library
      - chroma_data:/data/chroma
      - logs:/data/logs
    command: python -m app.workers.digest_worker
    restart: unless-stopped
  
  # Ingestion Worker
  ingestion-worker:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: librarian-ingestion-worker
    depends_on:
      - postgres
      - redis
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      POSTGRES_URL: postgresql://librarian:${POSTGRES_PASSWORD}@postgres:5432/librarian
      REDIS_URL: redis://redis:6379/0
      LIBRARY_ROOT: /data/library
      CHROMA_PERSIST_DIR: /data/chroma
    volumes:
      - library_data:/data/library
      - chroma_data:/data/chroma
      - logs:/data/logs
    command: python -m app.workers.ingestion_worker
    restart: unless-stopped
  
  # Prometheus (Monitoring)
  prometheus:
    image: prom/prometheus:latest
    container_name: librarian-prometheus
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
  
  # Grafana (Visualization)
  grafana:
    image: grafana/grafana:latest
    container_name: librarian-grafana
    depends_on:
      - prometheus
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3000:3000"

volumes:
  postgres_data:
  redis_data:
  library_data:
  chroma_data:
  logs:
  prometheus_data:
  grafana_data:
```

### Dockerfile

**docker/Dockerfile**:
```dockerfile
# Multi-stage build for production

# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN /root/.local/bin/poetry export -f requirements.txt --output requirements.txt --without-hashes
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ ./app/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create data directories
RUN mkdir -p /data/library /data/chroma /data/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8501/_stcore/health')"

# Default command (can be overridden)
CMD ["streamlit", "run", "app/presentation/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Build and Run

```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Check status
docker-compose ps

# Stop services
docker-compose down
```

## Production Deployment

### 1. Server Setup (Ubuntu 22.04)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin

# Install monitoring tools
sudo apt install htop iotop nethogs

# Configure firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. SSL/TLS Setup (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot certonly --standalone -d librarian.yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

### 3. Nginx Reverse Proxy

**/etc/nginx/sites-available/librarian**:
```nginx
upstream streamlit {
    server 127.0.0.1:8501;
}

server {
    listen 80;
    server_name librarian.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name librarian.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/librarian.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/librarian.yourdomain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://streamlit;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_read_timeout 86400;
    }
    
    location /_stcore/stream {
        proxy_pass http://streamlit/_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/librarian /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 4. Systemd Services

**/etc/systemd/system/librarian.service**:
```ini
[Unit]
Description=Williams Framework AI Librarian
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/williams-librarian
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
User=librarian
Group=librarian

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable librarian
sudo systemctl start librarian
sudo systemctl status librarian
```

### 5. Environment Variables (Production)

**/opt/williams-librarian/.env**:
```bash
# CRITICAL: Use strong passwords!
POSTGRES_PASSWORD=<strong-random-password>
GRAFANA_PASSWORD=<strong-random-password>

# OpenAI
OPENAI_API_KEY=sk-proj-...
OPENAI_ORG_ID=org-...

# Models
SCREENING_MODEL=gpt-5-nano
SUMMARIZATION_MODEL=gpt-5-mini
ANALYSIS_MODEL=gpt-5

# Cost Management
MONTHLY_API_BUDGET=100.0

# Feature Flags
ENABLE_WEB_SEARCH=false
ENABLE_FILE_SEARCH=true
ENABLE_KG_BUILDING=true

# Logging
LOG_LEVEL=INFO
```

Set secure permissions:
```bash
chmod 600 /opt/williams-librarian/.env
chown librarian:librarian /opt/williams-librarian/.env
```

## Monitoring & Observability

### Prometheus Configuration

**config/prometheus.yml**:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'librarian-app'
    static_configs:
      - targets: ['app:8501']
  
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
  
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
```

### Grafana Dashboards

**config/grafana/dashboards/librarian.json**:
```json
{
  "dashboard": {
    "title": "Williams Librarian Dashboard",
    "panels": [
      {
        "title": "API Cost (Last 30 Days)",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(librarian_api_cost_total)"
          }
        ]
      },
      {
        "title": "Content Processing Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(librarian_content_processed_total[5m])"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "type": "gauge",
        "targets": [
          {
            "expr": "librarian_cache_hit_rate"
          }
        ]
      }
    ]
  }
}
```

### Application Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Cost metrics
api_cost_total = Counter(
    'librarian_api_cost_total',
    'Total API cost in USD',
    ['model']
)

# Processing metrics
content_processed = Counter(
    'librarian_content_processed_total',
    'Total content items processed',
    ['content_type', 'quality_tier']
)

# Latency metrics
processing_duration = Histogram(
    'librarian_processing_duration_seconds',
    'Content processing duration',
    ['stage']
)

# Cache metrics
cache_hit_rate = Gauge(
    'librarian_cache_hit_rate',
    'Cache hit rate percentage'
)
```

### Logging Configuration

**config/logging.yaml**:
```yaml
version: 1
disable_existing_loggers: false

formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  json:
    class: pythonjsonlogger.jsonlogger.JsonFormatter
    format: '%(asctime)s %(name)s %(levelname)s %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: default
    stream: ext://sys.stdout
  
  file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: json
    filename: /data/logs/app.log
    maxBytes: 10485760  # 10MB
    backupCount: 10
  
  error_file:
    class: logging.handlers.RotatingFileHandler
    level: ERROR
    formatter: json
    filename: /data/logs/errors.log
    maxBytes: 10485760
    backupCount: 10
  
  cost_file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: json
    filename: /data/logs/costs.log
    maxBytes: 10485760
    backupCount: 10

loggers:
  app:
    level: INFO
    handlers: [console, file, error_file]
    propagate: false
  
  app.intelligence.cost_optimizer:
    level: INFO
    handlers: [console, cost_file]
    propagate: false

root:
  level: INFO
  handlers: [console, file]
```

## Backup & Recovery

### Backup Strategy

**Automated Daily Backups**:

**scripts/backup.sh**:
```bash
#!/bin/bash

BACKUP_DIR="/backups/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL
docker exec librarian-postgres pg_dump -U librarian librarian > "$BACKUP_DIR/postgres.sql"

# Backup library files
tar -czf "$BACKUP_DIR/library.tar.gz" /opt/williams-librarian/data/library

# Backup ChromaDB
tar -czf "$BACKUP_DIR/chroma.tar.gz" /opt/williams-librarian/data/chroma

# Backup configuration
cp /opt/williams-librarian/.env "$BACKUP_DIR/.env"
cp /opt/williams-librarian/config/*.yaml "$BACKUP_DIR/"

# Upload to S3 (optional)
aws s3 sync "$BACKUP_DIR" s3://your-bucket/backups/$(date +%Y-%m-%d)/

# Cleanup old backups (keep 30 days)
find /backups -type d -mtime +30 -exec rm -rf {} \;
```

**Cron job**:
```bash
# Daily backup at 2 AM
0 2 * * * /opt/williams-librarian/scripts/backup.sh
```

### Recovery

```bash
# Restore PostgreSQL
docker exec -i librarian-postgres psql -U librarian librarian < /backups/2024-01-15/postgres.sql

# Restore library files
tar -xzf /backups/2024-01-15/library.tar.gz -C /opt/williams-librarian/data/

# Restore ChromaDB
tar -xzf /backups/2024-01-15/chroma.tar.gz -C /opt/williams-librarian/data/

# Restart services
docker-compose restart
```

## Scaling

### Horizontal Scaling

**docker-compose.scale.yml** (overlay):
```yaml
version: '3.8'

services:
  ingestion-worker:
    deploy:
      replicas: 3  # Scale to 3 workers
  
  app:
    deploy:
      replicas: 2  # Scale to 2 app instances
    ports:
      - "8501-8502:8501"  # Different ports
```

Run with:
```bash
docker-compose -f docker-compose.yml -f docker-compose.scale.yml up -d
```

### Load Balancing (Nginx)

```nginx
upstream streamlit_backend {
    least_conn;
    server 127.0.0.1:8501;
    server 127.0.0.1:8502;
}

server {
    listen 443 ssl http2;
    server_name librarian.yourdomain.com;
    
    location / {
        proxy_pass http://streamlit_backend;
        # ... other proxy settings
    }
}
```

### Database Optimization

**PostgreSQL tuning** (/etc/postgresql/15/main/postgresql.conf):
```ini
# Memory
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 50MB
maintenance_work_mem = 512MB

# Connections
max_connections = 100

# Autovacuum
autovacuum = on
autovacuum_max_workers = 4
```

**Redis tuning** (redis.conf):
```ini
maxmemory 1gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## Troubleshooting

### Check Service Health

```bash
# Docker containers
docker-compose ps
docker-compose logs -f app

# System resources
htop
docker stats

# Database connections
docker exec librarian-postgres psql -U librarian -c "SELECT count(*) FROM pg_stat_activity;"

# Redis status
docker exec librarian-redis redis-cli INFO
```

### Common Issues

**Issue: Out of Memory**
```bash
# Check memory usage
docker stats

# Solution: Increase memory limits in docker-compose.yml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 4G
```

**Issue: API Budget Exceeded**
```bash
# Check cost logs
tail -f data/logs/costs.log

# Solution: Adjust budget or optimize usage
# Edit .env: MONTHLY_API_BUDGET=200.0
```

**Issue: Slow Search**
```bash
# Check ChromaDB size
du -sh data/chroma/

# Solution: Rebuild index or upgrade hardware
poetry run python scripts/rebuild_chroma_index.py
```

## Security Checklist

- [ ] Strong passwords for all services
- [ ] `.env` file has restrictive permissions (600)
- [ ] SSL/TLS enabled for all public endpoints
- [ ] Firewall configured (only 22, 80, 443 open)
- [ ] Regular security updates (`apt upgrade`)
- [ ] Backups tested and verified
- [ ] Monitoring alerts configured
- [ ] API keys rotated regularly
- [ ] Logs monitored for suspicious activity
- [ ] Non-root user for application

## Maintenance Schedule

- **Daily**: Automated backups, log rotation
- **Weekly**: Review cost reports, check disk space
- **Monthly**: Security updates, performance optimization
- **Quarterly**: Backup restoration test, disaster recovery drill

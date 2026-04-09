# Deployment Guide

## Overview

This guide covers deploying the EWS Retention Platform in various environments.

## Environments

### 1. Local Development

```bash
# Backend
cd /path/to/ews-retention-platform
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm start
```

### 2. Docker Compose (Recommended for Small Deployments)

```bash
cd docker
docker-compose up -d

# Services:
# - Backend API: http://localhost:8000
# - Frontend: http://localhost:3000
# - Redis: localhost:6379
```

**Production considerations:**
- Set `ENVIRONMENT=production` in docker-compose.yml
- Change default `SECRET_KEY`
- Mount persistent volume for SQLite database
- Use external Redis or PostgreSQL

### 3. Production Deployment Checklist

#### Pre-Deployment

- [ ] Run all tests: `pytest backend/tests -v`
- [ ] Check security: `bandit -r backend/`
- [ ] Verify no secrets in code: `detect-secrets scan`
- [ ] Review `.env` configuration
- [ ] Set strong `SECRET_KEY` (32+ chars)
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Set `ENVIRONMENT=production`

#### Environment Variables

Required for production:
```bash
SECRET_KEY=<32-char-random-string>
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@localhost/ews
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=https://your-domain.com
```

#### Database Migration

```bash
# Run Alembic migrations
alembic upgrade head

# Or for fresh install:
python -c "from backend.database.connection import init_db; init_db()"
```

#### SSL/TLS Configuration

Using nginx reverse proxy:

```nginx
server {
    listen 443 ssl http2;
    server_name api.your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4. Cloud Deployment

#### AWS (ECS/Fargate)

```yaml
# Example task definition
family: ews-retention-platform
networkMode: awsvpc
requiresCompatibilities: [FARGATE]
cpu: 1024
memory: 2048
containerDefinitions:
  - name: backend
    image: your-registry/ews-backend:latest
    portMappings:
      - containerPort: 8000
    environment:
      - name: ENVIRONMENT
        value: production
    secrets:
      - name: SECRET_KEY
        valueFrom: arn:aws:secretsmanager:region:account:secret:ews-secret-key
```

#### Google Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/ews-backend

# Deploy
gcloud run deploy ews-backend \
  --image gcr.io/PROJECT_ID/ews-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="ENVIRONMENT=production" \
  --set-secrets="SECRET_KEY=ews-secret-key:latest"
```

#### Heroku

```bash
# Create app
heroku create ews-retention-platform

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Set config
heroku config:set ENVIRONMENT=production
heroku config:set SECRET_KEY=<your-secret-key>

# Deploy
git push heroku main
```

## Monitoring & Logging

### Health Checks

```bash
# API health
curl https://your-domain.com/health

# Expected response:
# {"status": "healthy", "database": "connected", "redis": "connected"}
```

### Log Aggregation

The application uses JSON structured logging. Configure log aggregation:

```python
# In production, logs go to:
# - File: backend/backend.log (configurable via LOG_FILE)
# - Stdout: For container environments
# - PII is automatically masked
```

## Backup & Recovery

### SQLite (Development)

```bash
# Backup
cp backend/data/sql_app.db backup/$(date +%Y%m%d)_sql_app.db

# Restore
cp backup/20240409_sql_app.db backend/data/sql_app.db
```

### PostgreSQL (Production)

```bash
# Backup
pg_dump -U user -h localhost ews > backup_$(date +%Y%m%d).sql

# Restore
psql -U user -h localhost ews < backup_20240409.sql
```

## Troubleshooting

### Common Issues

**Issue**: "Unable to connect to Redis"
- Check `REDIS_URL` in `.env`
- Verify Redis is running: `redis-cli ping`

**Issue**: "Database locked" (SQLite)
- SQLite doesn't support concurrent writes
- Consider PostgreSQL for multi-worker deployments

**Issue**: "CORS errors in frontend"
- Add frontend origin to `CORS_ORIGINS`
- Format: `http://localhost:3000,https://your-domain.com`

**Issue**: "Rate limit exceeded"
- Default: 200 requests/minute
- Adjust `RATE_LIMIT_DEFAULT` in `.env`
- Use Redis for distributed rate limiting

## Security Checklist

- [ ] HTTPS enabled with valid SSL certificate
- [ ] `SECRET_KEY` is strong and unique
- [ ] `ENVIRONMENT=production` set
- [ ] Debug mode disabled
- [ ] Rate limiting configured
- [ ] Security headers enabled (HSTS, CSP, etc.)
- [ ] Database credentials secured
- [ ] API key hashes stored (not raw keys)
- [ ] Audit logging enabled
- [ ] PII masking active in logs

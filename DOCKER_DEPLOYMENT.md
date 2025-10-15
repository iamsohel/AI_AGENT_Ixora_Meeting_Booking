# Docker Deployment Guide

Complete guide for deploying Ixora AI Assistant using Docker - includes RAG system, booking agent, PostgreSQL, Redis, and admin panel.

---

## 📦 What's Included

The Docker setup includes:
- **Backend API** (FastAPI with RAG + Booking)
- **Frontend** (React chat interface + Admin panel)
- **PostgreSQL** (Production database)
- **Redis** (Session management)
- **Volume Mounts** (Persistent storage for Chroma DB, documents, uploads)

---

## 🚀 Quick Start (Development)

### 1. Prerequisites

- Docker 20.10+ and Docker Compose 1.29+
- At least 4GB RAM available for Docker
- `.env` file configured (copy from `.env.example`)

### 2. Build and Run

```bash
# Copy environment file
cp .env.example .env

# Edit .env with your API keys
nano .env

# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service health
docker-compose ps
```

### 3. Access the Application

- **Frontend**: http://localhost
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Admin Panel**: http://localhost/admin.html

### 4. Initialize Data

```bash
# Initialize database
docker-compose exec backend uv run python database/init_db.py

# Initialize vector store with documents
docker-compose exec backend uv run python rag/init_vectorstore.py
```

---

## 🏭 Production Deployment

### 1. Prepare Environment

```bash
# Copy production environment template
cp .env.production .env

# Edit with production values
nano .env
```

**IMPORTANT**: Change ALL default passwords and secrets:
- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `ADMIN_PASSWORD`
- `JWT_SECRET_KEY` (generate with: `openssl rand -hex 32`)

### 2. Update Configuration

Edit `docker-compose.yml` for production:

```yaml
# Change ports to use reverse proxy
backend:
  ports:
    - "127.0.0.1:8000:8000"  # Only localhost

frontend:
  ports:
    - "127.0.0.1:80:80"      # Only localhost
```

### 3. Deploy with Docker Compose

```bash
# Build with no cache
docker-compose build --no-cache

# Start in detached mode
docker-compose up -d

# Verify all services are healthy
docker-compose ps

# Check logs
docker-compose logs -f backend
```

### 4. Initialize Production Database

```bash
# Run database initialization
docker-compose exec backend uv run python database/init_db.py

# Verify admin user created
docker-compose exec backend uv run python -c "from database.database import get_db; from database.models import AdminUser; db = next(get_db()); print('Admin exists:', db.query(AdminUser).first() is not None)"
```

### 5. Load Documents

```bash
# Copy documents to volume
docker cp ./ixora.pdf ixora-booking-api:/app/documents/

# Initialize vector store
docker-compose exec backend uv run python rag/init_vectorstore.py
```

---

## 🔧 Service Management

### Start Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d backend

# Start with logs
docker-compose up
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (CAUTION: deletes data!)
docker-compose down -v
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Execute Commands

```bash
# Access backend shell
docker-compose exec backend /bin/bash

# Run Python script
docker-compose exec backend uv run python main.py

# Access PostgreSQL
docker-compose exec postgres psql -U ixora -d ixora_chat

# Access Redis CLI
docker-compose exec redis redis-cli -a changeme
```

---

## 💾 Data Persistence

### Volumes

The following data is persisted in Docker volumes:

- `postgres_data` - PostgreSQL database
- `redis_data` - Redis cache
- `chroma_data` - Vector store embeddings
- `documents` - PDF documents for RAG
- `uploads` - Admin uploaded files

### Backup

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U ixora ixora_chat > backup.sql

# Backup all volumes
docker run --rm -v ixora-meeting-booking_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
docker run --rm -v ixora-meeting-booking_chroma_data:/data -v $(pwd):/backup alpine tar czf /backup/chroma_backup.tar.gz -C /data .
```

### Restore

```bash
# Restore PostgreSQL
docker-compose exec -T postgres psql -U ixora ixora_chat < backup.sql

# Restore volumes
docker run --rm -v ixora-meeting-booking_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /data
```

---

## 🔒 Security Hardening

### 1. Change Default Credentials

```bash
# In .env file
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
ADMIN_PASSWORD=$(openssl rand -base64 16)
JWT_SECRET_KEY=$(openssl rand -hex 32)
```

### 2. Use HTTPS

Set up nginx reverse proxy with SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Network Security

```yaml
# In docker-compose.yml
services:
  backend:
    ports:
      - "127.0.0.1:8000:8000"  # Bind to localhost only
```

### 4. Limit Resources

```yaml
# In docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

---

## 📊 Monitoring & Debugging

### Health Checks

```bash
# Check all health statuses
docker-compose ps

# API health
curl http://localhost:8000/api/health

# Database connection
docker-compose exec backend uv run python -c "from database.database import engine; engine.connect(); print('DB OK')"
```

### Logs

```bash
# Follow all logs
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Search logs
docker-compose logs backend | grep ERROR
```

### Debug Mode

Add to `docker-compose.yml`:

```yaml
backend:
  environment:
    - DEBUG=true
    - LOG_LEVEL=DEBUG
```

---

## 🔄 Updates & Maintenance

### Update Application Code

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose build backend
docker-compose up -d backend

# Check logs
docker-compose logs -f backend
```

### Update Dependencies

```bash
# Update pyproject.toml
# Rebuild with no cache
docker-compose build --no-cache backend
docker-compose up -d backend
```

### Database Migrations

```bash
# Run migration scripts
docker-compose exec backend uv run python database/migrate.py

# Or use Alembic
docker-compose exec backend alembic upgrade head
```

---

## 🧪 Testing in Docker

### Run Tests

```bash
# Unit tests
docker-compose exec backend uv run pytest

# Integration tests
docker-compose exec backend uv run pytest tests/integration/

# With coverage
docker-compose exec backend uv run pytest --cov=.
```

---

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs backend

# Rebuild
docker-compose build --no-cache backend
docker-compose up -d backend

# Check environment
docker-compose exec backend env | grep GOOGLE_API_KEY
```

### Database Connection Issues

```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec backend uv run python -c "from database.database import engine; engine.connect()"

# Reset database
docker-compose down -v
docker-compose up -d postgres
# Wait for healthy status
docker-compose exec backend uv run python database/init_db.py
```

### Vector Store Issues

```bash
# Recreate vector store
docker-compose exec backend rm -rf /app/chroma_db
docker-compose exec backend uv run python rag/init_vectorstore.py
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Increase memory limits in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G
```

### Clean Slate

```bash
# Remove everything and start fresh
docker-compose down -v
docker system prune -a
docker-compose up -d
```

---

## 📝 Production Checklist

Before deploying to production:

- [ ] Changed all default passwords
- [ ] Generated secure JWT_SECRET_KEY
- [ ] Configured HTTPS/SSL
- [ ] Set up database backups
- [ ] Configured monitoring/alerting
- [ ] Set resource limits
- [ ] Enabled health checks
- [ ] Configured CORS for production domain
- [ ] Set up log rotation
- [ ] Tested disaster recovery
- [ ] Documented runbooks
- [ ] Set up firewall rules

---

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend    │────▶│  PostgreSQL  │
│   (Nginx)    │     │   (FastAPI)  │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐     ┌──────────────┐
                     │    Redis     │     │  Chroma DB   │
                     │  (Sessions)  │     │  (Vectors)   │
                     └──────────────┘     └──────────────┘
```

---

## 🔗 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Guide](https://hub.docker.com/_/postgres)
- [Redis Docker Guide](https://hub.docker.com/_/redis)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

---

## 📞 Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Review health checks: `docker-compose ps`
3. Verify environment: `docker-compose exec backend env`
4. Check troubleshooting section above

---

*Last updated: January 2025*
*Version: 2.0.0*

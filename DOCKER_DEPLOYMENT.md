# Docker Deployment Guide

This guide explains how to deploy the iXora Meeting Booking AI Agent using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+ installed
- Docker Compose V2+ installed
- At least 4GB of free RAM
- Ports 80 and 8000 available

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ixora-meeting-booking
```

### 2. Configure Environment Variables

Create a `.env` file from the example:

```bash
cp .env.docker.example .env
```

Edit `.env` and set your values:

```env
GOOGLE_API_KEY=your_actual_google_api_key
IXORA_BOOKING_URL=https://outlook.office.com/bookwithme/user/your-booking-id
VITE_API_URL=http://your-server-ip:8000
```

### 3. Deploy with One Command

```bash
docker compose up -d
```

That's it! The application will be available at:
- **Frontend**: http://localhost (port 80)
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Deployment Commands

### Start the Application

```bash
# Start in detached mode (background)
docker compose up -d

# Start with logs visible
docker compose up
```

### Stop the Application

```bash
docker compose down
```

### Stop and Remove Volumes

```bash
docker compose down -v
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart backend
```

### Rebuild Images

```bash
# Rebuild all images
docker compose build

# Rebuild specific service
docker compose build backend

# Rebuild and restart
docker compose up -d --build
```

## Architecture

```
┌─────────────────┐      ┌──────────────────┐
│   Frontend      │      │    Backend       │
│   (Nginx)       │─────▶│   (FastAPI)      │
│   Port 80       │      │   Port 8000      │
└─────────────────┘      └──────────────────┘
        │                         │
        └─────────────────────────┘
            ixora-network
```

### Services

1. **Backend** (`ixora-booking-api`)
   - FastAPI application
   - Handles AI agent logic
   - Browser automation for slot fetching
   - Health check endpoint: `/api/health`

2. **Frontend** (`ixora-booking-frontend`)
   - React application
   - Served by Nginx
   - Communicates with backend via API

## Production Considerations

### 1. Use Custom Ports

Edit `docker-compose.yml` to change port mappings:

```yaml
services:
  backend:
    ports:
      - "8080:8000"  # Change 8080 to your desired port

  frontend:
    ports:
      - "3000:80"    # Change 3000 to your desired port
```

### 2. Use Domain Names

Update environment variables for your domain:

```env
VITE_API_URL=https://api.yourdomain.com
```

### 3. Add SSL/TLS

Use a reverse proxy like Nginx or Traefik in front of Docker Compose:

```yaml
services:
  nginx-proxy:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./ssl:/etc/nginx/ssl
      - ./nginx.conf:/etc/nginx/nginx.conf
```

### 4. Resource Limits

Add resource constraints to prevent excessive resource usage:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 5. Logging Configuration

Configure log rotation:

```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Monitoring

### Check Service Status

```bash
docker compose ps
```

### Check Health

```bash
# Backend health
curl http://localhost:8000/api/health

# Frontend health
curl http://localhost/
```

### Resource Usage

```bash
docker stats
```

## Troubleshooting

### Backend Not Starting

1. Check logs:
   ```bash
   docker compose logs backend
   ```

2. Verify environment variables:
   ```bash
   docker compose config
   ```

3. Check if Playwright dependencies installed:
   ```bash
   docker compose exec backend uv run playwright --version
   ```

### Frontend Not Loading

1. Check if build succeeded:
   ```bash
   docker compose logs frontend
   ```

2. Verify nginx is running:
   ```bash
   docker compose exec frontend nginx -t
   ```

### Connection Issues

1. Check network:
   ```bash
   docker network ls
   docker network inspect ixora-meeting-booking_ixora-network
   ```

2. Test backend from frontend:
   ```bash
   docker compose exec frontend wget -O- http://backend:8000/api/health
   ```

## Updating the Application

### Update Code and Redeploy

```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose up -d --build
```

### Update Only Backend

```bash
docker compose up -d --build backend
```

### Update Only Frontend

```bash
docker compose up -d --build frontend
```

## Backup and Restore

### Backup Configuration

```bash
# Backup environment and compose files
tar -czf ixora-backup-$(date +%Y%m%d).tar.gz .env docker-compose.yml
```

### Export Logs

```bash
docker compose logs > logs-$(date +%Y%m%d).txt
```

## Security Best Practices

1. **Never commit `.env` file** - Keep secrets out of version control
2. **Use strong API keys** - Rotate keys regularly
3. **Enable firewall** - Only expose necessary ports
4. **Update regularly** - Keep Docker and images updated
5. **Scan images** - Use Docker Scout or Trivy for vulnerability scanning

```bash
docker scout cves ixora-booking-api
```

## Scaling

### Horizontal Scaling (Multiple Instances)

```yaml
services:
  backend:
    deploy:
      replicas: 3
```

### Load Balancer

Add Nginx or HAProxy as load balancer:

```yaml
services:
  loadbalancer:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./lb.conf:/etc/nginx/nginx.conf
    depends_on:
      - backend
```

## Development vs Production

### Development

```bash
docker compose -f docker-compose.dev.yml up
```

### Production

```bash
docker compose -f docker-compose.yml up -d
```

## Support

For issues or questions:
- Check logs: `docker compose logs`
- Review health checks: `docker compose ps`
- Restart services: `docker compose restart`

---

**Note**: This deployment uses production-grade configurations with:
- Multi-stage builds for smaller images
- Non-root users for security
- Health checks for reliability
- Proper networking and isolation
- Resource optimization

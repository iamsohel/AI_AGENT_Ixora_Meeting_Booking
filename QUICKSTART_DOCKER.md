# 🚀 Quick Start with Docker

Deploy the iXora Meeting Booking AI Agent in under 2 minutes!

## Prerequisites

- Docker and Docker Compose installed
- Ports 80 and 8000 available

## Steps

### 1️⃣ Clone Repository

```bash
git clone https://github.com/iamsohel/AI_AGENT_Ixora_Meeting_Booking.git
cd AI_AGENT_Ixora_Meeting_Booking
```

### 2️⃣ Configure Environment

```bash
# Copy environment template
cp .env.docker.example .env

# Edit .env and add your API keys
nano .env  # or use your favorite editor
```

Required values in `.env`:
```env
GOOGLE_API_KEY=your_google_api_key_here
IXORA_BOOKING_URL=https://outlook.office.com/bookwithme/user/your-booking-id
```

### 3️⃣ Deploy

```bash
docker compose up -d
```

That's it! ✅

## Access the Application

- **Chat Widget**: http://localhost
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

## Verify Deployment

```bash
# Check if services are running
docker compose ps

# View logs
docker compose logs -f
```

Expected output:
```
NAME                      STATUS          PORTS
ixora-booking-api         Up (healthy)    0.0.0.0:8000->8000/tcp
ixora-booking-frontend    Up (healthy)    0.0.0.0:80->80/tcp
```

## Common Commands

```bash
# Stop services
docker compose down

# Restart services
docker compose restart

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Rebuild and restart
docker compose up -d --build
```

## Troubleshooting

### Services Won't Start?

1. Check if ports are available:
   ```bash
   sudo lsof -i :80
   sudo lsof -i :8000
   ```

2. Check logs:
   ```bash
   docker compose logs
   ```

### Need Help?

See [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md) for detailed documentation.

## Next Steps

- Customize the chat widget design
- Add your branding
- Configure production domain
- Set up SSL/TLS
- Enable monitoring

---

**🎉 Congratulations!** Your AI meeting booking agent is now live!

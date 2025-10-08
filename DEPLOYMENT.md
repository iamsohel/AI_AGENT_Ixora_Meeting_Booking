# Production Deployment Guide

This guide explains how to run the Ixora Meeting Booking application in production with React.js frontend and FastAPI backend.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌────────────────────┐
│                 │         │                  │         │                    │
│  React Frontend │────────▶│  FastAPI Backend │────────▶│  Microsoft Bookings│
│  (Port 3000)    │  HTTP   │  (Port 8000)     │  API    │                    │
│                 │         │                  │         │                    │
└─────────────────┘         └──────────────────┘         └────────────────────┘
```

## Prerequisites

- Python 3.10 or higher
- Node.js 18+ and npm
- Google API Key (for Gemini)
- Microsoft Bookings URL

## Backend Setup

### 1. Install Python Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
uv run playwright install chromium
# or
playwright install chromium
```

### 3. Configure Environment Variables

Create a `.env` file in the root directory:

```env
# Required
GOOGLE_API_KEY=your_google_api_key_here
IXORA_BOOKING_URL=https://outlook.office365.com/book/...

# Optional
GEMINI_MODEL=gemini-2.0-flash-exp
TEMPERATURE=0.7
```

### 4. Start the Backend Server

```bash
# Development mode (with auto-reload)
uv run python api.py

# Or with uvicorn directly
uv run uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs (Swagger UI)
- **Health**: http://localhost:8000/api/health

## Frontend Setup

### 1. Navigate to Frontend Directory

```bash
cd frontend
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Configure Environment (Optional)

Create a `.env` file in the `frontend` directory:

```env
VITE_API_URL=http://localhost:8000
```

### 4. Start the Development Server

```bash
npm run dev
```

The React app will be available at:
- **Frontend**: http://localhost:3000

## Running Both Servers

You need to run both servers simultaneously:

### Terminal 1 (Backend):
```bash
uv run python api.py
```

### Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

## API Endpoints

### Health Check
```bash
GET http://localhost:8000/api/health
```

### Create Session
```bash
POST http://localhost:8000/api/session
```

Response:
```json
{
  "session_id": "uuid",
  "message": "Session created successfully"
}
```

### Send Message
```bash
POST http://localhost:8000/api/chat
Content-Type: application/json

{
  "message": "I want to book a meeting on Oct 12 at 10:30 AM",
  "session_id": "uuid"
}
```

Response:
```json
{
  "message": "Great! I found a slot at 10:30 AM...",
  "session_id": "uuid",
  "timestamp": "2025-10-08T..."
}
```

### Reset Session
```bash
POST http://localhost:8000/api/reset
Content-Type: application/json

{
  "session_id": "uuid"
}
```

### Delete Session
```bash
DELETE http://localhost:8000/api/session/{session_id}
```

### Get Statistics
```bash
GET http://localhost:8000/api/stats
```

## Production Deployment

### Backend (FastAPI)

#### Option 1: Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --no-dev

# Copy app
COPY . .

# Install Playwright
RUN uv run playwright install --with-deps chromium

# Expose port
EXPOSE 8000

# Run
CMD ["uv", "run", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t ixora-booking-api .
docker run -p 8000:8000 --env-file .env ixora-booking-api
```

#### Option 2: Traditional Server

```bash
# Install gunicorn
uv pip install gunicorn

# Run with gunicorn
uv run gunicorn api:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

#### Option 3: systemd Service

Create `/etc/systemd/system/ixora-booking.service`:
```ini
[Unit]
Description=Ixora Meeting Booking API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/ixora-meeting-booking
Environment="PATH=/path/to/.venv/bin"
ExecStart=/path/to/.venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable ixora-booking
sudo systemctl start ixora-booking
```

### Frontend (React)

#### Build for Production

```bash
cd frontend
npm run build
```

This creates a `dist` folder with optimized static files.

#### Option 1: Serve with Nginx

Install Nginx and configure:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /path/to/frontend/dist;
    index index.html;

    # Frontend
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API proxy
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

#### Option 2: Serve with Apache

Enable required modules:
```bash
sudo a2enmod proxy proxy_http rewrite
```

Configure virtual host:
```apache
<VirtualHost *:80>
    ServerName your-domain.com
    DocumentRoot /path/to/frontend/dist

    <Directory /path/to/frontend/dist>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
        RewriteEngine On
        RewriteBase /
        RewriteRule ^index\.html$ - [L]
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule . /index.html [L]
    </Directory>

    ProxyPass /api http://localhost:8000/api
    ProxyPassReverse /api http://localhost:8000/api
</VirtualHost>
```

#### Option 3: Deploy to Vercel/Netlify

**Vercel:**
```bash
cd frontend
npm install -g vercel
vercel --prod
```

Update `vite.config.js` to use production API URL:
```javascript
export default defineConfig({
  plugins: [react()],
  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify('https://your-api-domain.com')
  }
})
```

## Environment Variables (Production)

### Backend
```env
GOOGLE_API_KEY=your_production_key
IXORA_BOOKING_URL=your_booking_url
GEMINI_MODEL=gemini-2.0-flash-exp
TEMPERATURE=0.7
```

### Frontend
```env
VITE_API_URL=https://your-api-domain.com
```

## Security Considerations

1. **CORS**: Update allowed origins in `api.py`:
```python
allow_origins=["https://your-frontend-domain.com"]
```

2. **HTTPS**: Always use HTTPS in production
   - Use Let's Encrypt for free SSL certificates
   - Configure Nginx/Apache with SSL

3. **API Keys**: Never commit API keys to git
   - Use environment variables
   - Use secrets management (AWS Secrets Manager, etc.)

4. **Rate Limiting**: Add rate limiting to prevent abuse:
```bash
uv pip install slowapi
```

5. **Session Storage**: For production, use Redis instead of in-memory:
```bash
uv pip install redis
```

## Monitoring

### Health Checks

```bash
# Backend
curl http://localhost:8000/api/health

# Frontend
curl http://localhost:3000
```

### Logs

Backend logs (systemd):
```bash
sudo journalctl -u ixora-booking -f
```

Nginx access/error logs:
```bash
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

## Troubleshooting

### Backend won't start
- Check environment variables are set
- Verify Playwright browsers are installed
- Check port 8000 is not in use

### Frontend build fails
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`
- Clear npm cache: `npm cache clean --force`

### CORS errors
- Verify backend CORS settings include frontend URL
- Check browser console for exact error

### Session not persisting
- Check backend session storage
- Verify cookies are enabled in browser

## Performance Optimization

1. **Backend**:
   - Use multiple workers: `--workers 4`
   - Enable response compression
   - Implement caching for slot data

2. **Frontend**:
   - Enable code splitting
   - Compress images
   - Use CDN for static assets

## Scaling

For high traffic:
- Deploy backend behind load balancer
- Use Redis for session storage
- Scale horizontally with multiple backend instances
- Use CDN for frontend assets

## Support

For issues:
- Check logs first
- Review API documentation: http://localhost:8000/docs
- GitHub Issues: https://github.com/iamsohel/AI_AGENT_Ixora_Meeting_Booking/issues

# Quick Start Guide - Web Interface

Get the Ixora Meeting Booking web application running in 5 minutes!

## Prerequisites

- Python 3.10+
- Node.js 18+
- Google API Key

## Step 1: Backend Setup (2 minutes)

```bash
# 1. Install Python dependencies
uv sync

# 2. Install Playwright browsers
uv run playwright install chromium

# 3. Create .env file
cat > .env << EOL
GOOGLE_API_KEY=your_google_api_key_here
IXORA_BOOKING_URL=https://outlook.office365.com/book/...
EOL

# 4. Start the backend
uv run python api.py
```

✅ Backend running at http://localhost:8000

## Step 2: Frontend Setup (2 minutes)

Open a new terminal:

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```

✅ Frontend running at http://localhost:3000

## Step 3: Use the Application

1. Open your browser to http://localhost:3000
2. You'll see a beautiful chat interface
3. Start chatting with the AI assistant:
   - "I want to book a meeting on Oct 12 at 10:30 AM"
   - Provide your name, email, and phone when asked
   - Confirm the booking

## Features

✨ **Modern UI**
- Beautiful gradient design
- Smooth animations
- Mobile responsive

🤖 **Smart AI**
- Natural language understanding
- Auto-date parsing
- Context-aware conversations

⚡ **Real-time**
- Instant responses
- Session persistence
- Auto-scroll

## API Documentation

Visit http://localhost:8000/docs for interactive API documentation (Swagger UI).

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Verify environment variables
cat .env
```

### Frontend won't start
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Can't connect to API
- Check that both servers are running
- Verify CORS settings in `api.py`
- Check browser console for errors

## Next Steps

- **Production Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **API Reference**: See [http://localhost:8000/docs](http://localhost:8000/docs)
- **Architecture**: See [ARCHITECTURE_EXPLANATION.md](ARCHITECTURE_EXPLANATION.md)

## Development Tips

### Hot Reload

Both servers support hot reload:
- **Backend**: Changes to Python files auto-reload
- **Frontend**: Changes to React files auto-update in browser

### Debugging

**Backend logs:**
```bash
# Watch API logs in terminal
uv run python api.py
```

**Frontend debugging:**
- Open browser DevTools (F12)
- Check Console tab for errors
- Check Network tab for API calls

### Testing API with curl

```bash
# Health check
curl http://localhost:8000/api/health

# Create session
curl -X POST http://localhost:8000/api/session

# Send message
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Book Oct 12 at 10am", "session_id": "your-session-id"}'
```

## Clean Restart

If something goes wrong:

```bash
# Stop both servers (Ctrl+C)

# Backend
rm -rf __pycache__ .pytest_cache
uv sync

# Frontend
cd frontend
rm -rf node_modules dist
npm install

# Restart both servers
```

## Support

- **Issues**: https://github.com/iamsohel/AI_AGENT_Ixora_Meeting_Booking/issues
- **Documentation**: See DEPLOYMENT.md for production setup

Happy booking! 🎉

# Project Structure

This project follows a standard frontend/backend separation:

```
ixora-meeting-booking/
├── backend/                    # Python FastAPI Backend
│   ├── agent/                  # LangChain agent logic
│   ├── admin/                  # Admin authentication
│   ├── database/               # Database models & logging
│   ├── rag/                    # RAG functionality
│   ├── utils/                  # Utility functions
│   ├── tests/                  # Backend tests
│   ├── api.py                  # Main API server
│   ├── admin_api.py            # Admin API endpoints
│   ├── pyproject.toml          # Python dependencies
│   ├── uv.lock                 # Lock file
│   ├── start_api.sh            # Start script
│   ├── check_system.sh         # System check script
│   ├── chroma_db/              # Vector database
│   └── ixora_chat.db           # SQLite database
│
├── frontend/                   # React Frontend
│   ├── src/                    # React components
│   ├── public/                 # Static assets
│   ├── package.json            # Node dependencies
│   ├── vite.config.js          # Vite configuration
│   └── Dockerfile              # Frontend Docker image
│
├── .env                        # Environment variables
├── .env.example                # Example environment file
├── docker-compose.yml          # Docker orchestration
├── Dockerfile                  # Backend Docker image
└── README.md                   # Project documentation
```

## Running the Application

### Development Mode

**Backend:**
```bash
cd backend
uv run python api.py
# API runs on http://localhost:8000
```

**Frontend:**
```bash
cd frontend
npm run dev
# Frontend runs on http://localhost:3000 or 3001
```

### Production Mode (Docker)

```bash
docker-compose up -d
```

## API Endpoints

- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Admin Panel**: http://localhost:8000/admin/login
- **Health Check**: http://localhost:8000/api/health

## Environment Variables

All environment variables are configured in `.env` file at the root level. See `.env.example` for reference.

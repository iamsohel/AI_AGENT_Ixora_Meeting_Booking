# AI Meeting Booking Agent

> An intelligent conversational AI agent that automates meeting bookings through Microsoft Bookings using natural language processing.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangChain](https://img.shields.io/badge/LangChain-latest-green.svg)](https://python.langchain.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-latest-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Description

This project is an AI-powered conversational agent built with **LangChain** and **LangGraph** that streamlines the meeting booking process for Ixora Solution's CEO. The agent understands natural language inputs, manages the entire booking workflow through a state machine, and interacts with Microsoft Bookings to complete reservations.

### What It Does

- **Understands natural language**: "Book a meeting next Tuesday at 2 PM"
- **Parses complex date formats**: "tomorrow", "13 oct", "next Friday"
- **Fetches available time slots** from Microsoft Bookings
- **Extracts user information** (name, email, phone) from conversation
- **Confirms booking details** before finalizing
- **Books appointments** via direct API calls to Microsoft Bookings
- **Maintains conversation context** across multiple turns

---

## 🚀 Features

- ✅ **Conversational Interface** - Natural language interaction for seamless booking
- ✅ **Smart Date Parsing** - Understands relative dates like "next Tuesday", "tomorrow", "Oct 15"
- ✅ **Automated Slot Discovery** - Scrapes available time slots from Microsoft Bookings
- ✅ **Intelligent Information Extraction** - Regex + LLM fallback for extracting user details
- ✅ **Stateful Workflow** - LangGraph state machine tracks conversation progress
- ✅ **Dual Booking Methods** - Browser automation (Playwright) + Direct API calls
- ✅ **Error Handling** - Robust validation and user-friendly error messages
- ✅ **Interactive Mode** - Real-time conversation in terminal
- ✅ **Test Mode** - Simulated conversation for testing without actual bookings

---

## 🛠️ Tech Stack

### Core Technologies

| Technology | Purpose |
|------------|---------|
| **Python 3.11+** | Programming language |
| **LangChain** | AI agent framework and tool orchestration |
| **LangGraph** | State machine for conversation workflow |
| **Google Gemini** | Large Language Model (LLM) for natural language understanding |
| **Playwright** | Browser automation for web scraping |
| **httpx** | Async HTTP client for API calls |
| **python-dotenv** | Environment variable management |

### Architecture Components

```
┌─────────────────────────────────────────────────┐
│              User Input                          │
│    "Book a meeting next Tuesday at 2 PM"        │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│          graph.py (State Machine)                │
│   Routes conversation through workflow steps     │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│          nodes.py (Workflow Steps)               │
│  1. Extract Requirements (date, time)            │
│  2. Fetch Available Slots                        │
│  3. Select Best Slot                             │
│  4. Collect User Info (name, email, phone)       │
│  5. Extract User Info (regex + LLM)              │
│  6. Confirm Booking                              │
│  7. Book Meeting (API call)                      │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│           tools.py (AI Tools)                    │
│  - parse_date: Natural language → YYYY-MM-DD    │
│  - fetch_available_slots: Scrape MS Bookings    │
│  - book_meeting: API call to book appointment   │
│  - validate_user_info: Email/phone validation   │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│          utils/ (Low-level Helpers)              │
│  - browser_automation.py: Playwright scraper     │
│  - api_booking.py: Direct HTTP API calls         │
└─────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
ixora-meeting-booking/
├── backend/                     # Python FastAPI Backend
│   ├── agent/                   # LangChain agent logic
│   │   ├── graph.py             # LangGraph state machine controller
│   │   ├── nodes.py             # Workflow step implementations
│   │   ├── tools.py             # LangChain tools (AI-callable functions)
│   │   ├── unified_agent.py     # Unified RAG + Booking agent
│   │   ├── supervisor.py        # Intent classification supervisor
│   │   └── rag_nodes.py         # RAG workflow nodes
│   ├── database/                # Database models & logging
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── database.py          # Database connection
│   │   └── chat_logger.py       # Chat session logging
│   ├── rag/                     # RAG functionality
│   │   ├── document_loader.py   # PDF document processing
│   │   ├── vector_store.py      # ChromaDB vector storage
│   │   └── rag_chain.py         # RAG query chain
│   ├── utils/                   # Utility functions
│   │   ├── api_booking.py       # Direct API booking via HTTP
│   │   ├── cache.py             # Caching utilities
│   │   └── llm_tracker.py       # LLM usage tracking
│   ├── admin/                   # Admin authentication
│   │   └── auth.py              # JWT authentication
│   ├── tests/                   # Backend tests
│   ├── api.py                   # Main FastAPI application
│   ├── admin_api.py             # Admin API endpoints
│   ├── pyproject.toml           # Python dependencies
│   └── start_api.sh             # API start script
│
├── frontend/                    # React Frontend
│   ├── src/                     # React components
│   │   ├── App.jsx              # Main application component
│   │   └── ...
│   ├── package.json             # Node dependencies
│   └── vite.config.js           # Vite configuration
│
├── docker-compose.yml           # Docker orchestration
├── Dockerfile                   # Backend Docker image
├── .env                         # Environment variables
├── README.md                    # This file
└── STRUCTURE.md                 # Detailed structure documentation
```

For more details, see [STRUCTURE.md](STRUCTURE.md).

---

## ⚙️ Setup

### Prerequisites

- **Python 3.11 or higher**
- **Google Gemini API Key** ([Get it here](https://makersuite.google.com/app/apikey))
- **Microsoft Bookings URL** (your organization's booking page)
- **Git** (for cloning the repository)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/iamsohel/AI_AGENT_Ixora_Meeting_Booking.git
   cd AI_AGENT_Ixora_Meeting_Booking
   ```

2. **Create virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**

   Using `pip`:
   ```bash
   pip install -e .
   ```

   Or using `uv` (faster):
   ```bash
   uv pip install -e .
   ```

4. **Install Playwright browsers**

   ```bash
   playwright install chromium
   ```

5. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your credentials:
   ```env
   GOOGLE_API_KEY=your_gemini_api_key_here
   IXORA_BOOKING_URL=https://outlook.office365.com/book/YourBookingPage@domain.com/
   ```

---

## 🏃 Running the Application

### Development Mode

**Backend API:**
```bash
cd backend
uv run python api.py
# API runs on http://localhost:8000
# Docs available at http://localhost:8000/docs
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
# Backend: http://localhost:8000
# Frontend: http://localhost:80
```

### Legacy Interactive Mode (Command Line Agent)

For the original command-line booking agent:

```bash
cd backend
python main.py  # If main.py exists
```

**Example conversation:**
```
Agent: Hello! I'm here to help you book a meeting with Ixora Solution's CEO.
       What date and time would work best for you?

You: book a meeting in 13 oct 10 am

Agent: Great! I found a slot at 10:00 AM. To complete the booking,
       I need your name, email, and phone number.

You: John Doe, john@example.com, +1234567890

Agent: Let me confirm the details:
       - Time: 10:00 AM
       - Name: John Doe
       - Email: john@example.com
       - Phone: +1234567890
       - Purpose: not_specified

       Should I proceed with the booking?

You: yes

Agent: Your meeting has been successfully booked!
       You'll receive a confirmation email shortly.
```

### Test Mode (Simulated)

Run a simulated conversation without actual booking:

```bash
python main.py --test
```

### Available Commands

While running the agent:

- `quit` or `exit` - End the session
- `reset` - Start a new booking conversation
- `analyze` - Analyze the booking page structure (debugging)

---

## 🧪 Testing

### Manual Testing

1. **Test date parsing**:
   - "tomorrow"
   - "next Tuesday"
   - "13 oct"
   - "October 15, 2025"

2. **Test slot selection**:
   - Specify exact time: "10 AM"
   - Let agent show options
   - Select by number: "1"

3. **Test user info extraction**:
   - Comma-separated: "John, john@email.com, +123456"
   - Natural language: "My name is John, email is john@email.com, phone +123456"

### Running Test Mode

```bash
python main.py --test
```

This simulates a complete booking flow:
1. User requests meeting
2. Agent fetches slots
3. User provides info
4. Agent confirms and books

### Debugging

For detailed logs, the agent runs with `verbose=True` by default. Check console output for:
- Tool calls
- State transitions
- Extraction results
- API responses

---

## 🔧 Configuration

### Change LLM Model

Edit `main.py`:

```python
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",  # or "gemini-pro", "gemini-1.5-flash"
    temperature=0.7,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)
```

### Adjust Browser Settings

Edit `utils/browser_automation.py`:

```python
# Run browser in visible mode for debugging
async with BookingAutomation(booking_url, headless=False) as automation:
    slots = await automation.fetch_available_slots(date)
```

### Customize Booking Timezone

Edit `utils/api_booking.py`:

```python
self.timezone = "Bangladesh Standard Time"  # Change to your timezone
```

---

## 📚 API Documentation

### Custom Tools

The agent uses 5 LangChain tools:

#### 1. `parse_date`
Converts natural language dates to YYYY-MM-DD format.

**Input**: `"next Tuesday"`, `"13 oct"`, `"tomorrow"`
**Output**: `{"parsed": "2025-10-13", "formatted": "October 13, 2025"}`

#### 2. `fetch_available_slots`
Fetches available time slots from Microsoft Bookings.

**Input**: `date: "2025-10-13"`
**Output**: `[{"time": "10:00 AM", ...}, {"time": "11:00 AM", ...}]`

#### 3. `book_meeting`
Books a meeting via API call.

**Input**: `date, time, name, email, phone, notes`
**Output**: `{"success": true, "confirmation_message": "..."}`

#### 4. `validate_user_info`
Validates email and phone formats.

**Input**: `email: "user@example.com", phone: "+1234567890"`
**Output**: `{"email_valid": true, "phone_valid": true}`

#### 5. `analyze_booking_page`
Analyzes page structure for debugging (takes screenshot).

**Input**: `headless: false`
**Output**: `{"buttons": [...], "inputs": [...], "forms": [...]}`

---

## 🐛 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `IXORA_BOOKING_URL not configured` | Create `.env` file with `IXORA_BOOKING_URL` |
| `GOOGLE_API_KEY not set` | Add your Gemini API key to `.env` |
| `No slots found` | Run `analyze` command to debug page structure |
| `Invalid email format` | Use format `user@domain.com` |
| `API request timed out` | Check internet connection and booking URL |
| `Date format error` | Use YYYY-MM-DD or natural language like "tomorrow" |

### Analyze Booking Page

If slot detection fails:

```bash
python main.py
> analyze
```

This will:
- Open browser in visible mode
- Navigate to booking page
- Take screenshot
- Print page structure
- Help identify correct selectors

### Enable Debug Logging

The agent already runs with `verbose=True`. For more details, check:
- Tool call inputs/outputs
- State transitions in graph
- Extraction regex matches
- API request/response logs

---

## 📖 Further Reading

- **Detailed Architecture**: See [ARCHITECTURE_EXPLANATION.md](ARCHITECTURE_EXPLANATION.md)
- **LangChain Documentation**: https://python.langchain.com/
- **LangGraph Guide**: https://langchain-ai.github.io/langgraph/
- **Playwright Docs**: https://playwright.dev/python/

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Authors

- **Sohel Rana** - [@iamsohel](https://github.com/iamsohel)

---

## 🙏 Acknowledgments

- Built with [LangChain](https://python.langchain.com/) and [LangGraph](https://langchain-ai.github.io/langgraph/)
- Powered by [Google Gemini](https://deepmind.google/technologies/gemini/)
- Browser automation via [Playwright](https://playwright.dev/)

---

**Need help?** Open an issue or contact the development team.

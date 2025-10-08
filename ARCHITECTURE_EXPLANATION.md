# Meeting Booking Agent - Complete Architecture Explanation

## 🏗️ Overall Architecture

Your system is a **conversational AI agent** built with **LangChain + LangGraph** that automates meeting bookings through Microsoft Bookings. It uses:

- **LangGraph**: State machine for conversation flow
- **LangChain Tools**: AI-accessible functions (parse dates, fetch slots, book meetings)
- **Playwright**: Browser automation to interact with Microsoft Bookings
- **Google Gemini**: LLM for natural language understanding

```
┌─────────────────────────────────────────────────────────────┐
│                         USER INPUT                           │
│              "book a meeting in 13 oct 10 am"                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    GRAPH.PY (Orchestrator)                   │
│        BookingAgent - State Machine Controller               │
│   - Routes user messages to appropriate nodes                │
│   - Tracks conversation state                                │
│   - Decides what to do next                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   NODES.PY (Workflow Steps)                  │
│   Each node is a conversation step:                          │
│   1. extract_requirements_node  → Parse user intent          │
│   2. fetch_slots_node           → Get available times        │
│   3. select_slot_node           → Match user's time pref     │
│   4. collect_user_info_node     → Ask for name/email/phone   │
│   5. extract_user_info_node     → Parse contact info         │
│   6. confirm_booking_node       → Show confirmation          │
│   7. book_meeting_node          → Execute booking            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              TOOLS.PY (LangChain Tools/Functions)            │
│   AI-accessible functions that agents can call:              │
│   - parse_date           → "12 oct" → "2025-10-12"          │
│   - fetch_available_slots → Gets slots from MS Bookings      │
│   - book_meeting         → Books the appointment             │
│   - validate_user_info   → Validates email/phone             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  UTILS/ (Low-level Helpers)                  │
│                                                               │
│   browser_automation.py                                      │
│   - Uses Playwright to control Chrome browser                │
│   - Clicks dates, extracts time slots, fills forms           │
│                                                               │
│   api_booking.py                                             │
│   - Direct HTTP API calls to Microsoft Bookings              │
│   - Faster than browser automation                           │
└───────────────────────────────────────────────────────────────┘

---

## 📁 Detailed Component Breakdown

### 1️⃣ **graph.py** - The Orchestrator (State Machine Controller)

**Role:** Controls the entire conversation flow

**Key Class:** `BookingAgent`

**What it does:**
1. **Maintains State** - Keeps track of:
   - Conversation history
   - User preferences (date, time, purpose)
   - Contact info (name, email, phone)
   - Available slots
   - Selected slot
   - Current step in the workflow

2. **Routes Messages** - Decides which node to execute based on `next_action`:
   ```python
   if current_action == "wait_for_user_input":
       # Run extract_requirements + fetch_slots
   elif current_action == "wait_for_slot_selection":
       # Run process_slot_selection
   elif current_action == "wait_for_user_info":
       # Run extract_user_info + collect_user_info
   elif current_action == "wait_for_confirmation":
       # Run book_meeting
   ```

3. **Creates Agent Executor** - Sets up the LangChain agent that can call tools

**Key Functions:**
- `initialize_state()` - Resets conversation state
- `process_message(user_message)` - Main entry point for user input
- `create_agent_executor(llm)` - Creates the tool-calling agent

**State Structure:**
```python
{
    "messages": [HumanMessage(...), AIMessage(...), ...],
    "date_preference": "2025-10-13",  # Parsed date
    "time_preference": "10 AM",
    "user_name": "sohel",
    "user_email": "sohel@gmail.com",
    "user_phone": "+88091993939",
    "available_slots": [{time: "10:00 AM", ...}, ...],
    "selected_slot": {time: "10:00 AM", ...},
    "next_action": "wait_for_confirmation",
    "booking_confirmed": False
}
```

---

### 2️⃣ **nodes.py** - Workflow Steps (Individual Actions)

**Role:** Each function is a **node** (step) in the conversation workflow

**Key Nodes:**

#### a) `extract_requirements_node`
- **Input:** User's initial message
- **Output:** Extracts date, time, meeting purpose
- **Uses:** LLM to parse natural language
- **Example:** "book in 13 oct 10 am" → `date_preference: "13 oct"`, `time_preference: "10 am"`

#### b) `fetch_slots_node`
- **Input:** Date preference
- **Output:** List of available time slots
- **Calls:** `parse_date` tool, then `fetch_available_slots` tool
- **Updates state:**
  - `date_preference` → "2025-10-13" (parsed format)
  - `available_slots` → [{time: "10:00 AM"}, ...]

#### c) `select_slot_node`
- **Input:** Available slots + user's time preference
- **Output:** Selects best matching slot OR shows list for user to choose
- **Logic:**
  - If user said "10 am", finds "10:00 AM" slot automatically
  - Otherwise, shows numbered list of all slots

#### d) `collect_user_info_node`
- **Input:** State with selected slot
- **Output:** Asks for missing contact info (name, email, phone)
- **Logic:** Only asks if not already provided

#### e) `extract_user_info_node`
- **Input:** User's message with contact info
- **Output:** Extracts name, email, phone using regex + LLM
- **Regex patterns:**
  - Email: `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}`
  - Phone: `[\+]?[\d][\d\s\-\(\)]{6,}`
  - Name: Text after removing email and phone

#### f) `confirm_booking_node`
- **Input:** State with all info collected
- **Output:** Shows confirmation message with all details
- **Sets:** `next_action = "wait_for_confirmation"`

#### g) `book_meeting_node`
- **Input:** Confirmed booking details
- **Output:** Books the meeting
- **Calls:** `BookMeetingTool._run()` directly (no agent executor)
- **Updates:** `booking_confirmed = True/False`

**Flow Control Functions:**
- `check_requirements_complete()` - Returns "complete" or "incomplete"
- `check_confirmation()` - Returns "confirmed" or "declined"

---

### 3️⃣ **tools.py** - LangChain Tools (AI-Callable Functions)

**Role:** Functions that the AI agent can call to perform specific tasks

**Why Tools?** The LLM cannot directly access databases or websites. Tools bridge the gap between AI and external systems.

#### Tool 1: `ParseDateTool`
**Name:** `parse_date`
**Input:** Natural language date (e.g., "tomorrow", "13 oct", "next Tuesday")
**Output:**
```json
{
  "original": "13 oct",
  "parsed": "2025-10-13",
  "formatted": "October 13, 2025"
}
```
**How it works:** Uses Python's `datetime.strptime()` with multiple format patterns

#### Tool 2: `FetchAvailableSlotsTool`
**Name:** `fetch_available_slots`
**Input:** Date in YYYY-MM-DD format (optional)
**Output:** List of available time slots
**How it works:** Calls `browser_automation.fetch_slots_sync()` to scrape Microsoft Bookings

#### Tool 3: `BookMeetingTool`
**Name:** `book_meeting`
**Input:** date, slot_time, name, email, phone, notes
**Output:** Success/failure message
**How it works:**
1. Parses date to YYYY-MM-DD if needed
2. Calls `api_booking.book_appointment_sync()`
3. Returns confirmation or error

#### Tool 4: `ValidateUserInfoTool`
**Name:** `validate_user_info`
**Input:** email, phone
**Output:** Validation results
**How it works:** Uses regex to check formats

#### Tool 5: `AnalyzeBookingPageTool`
**Name:** `analyze_booking_page`
**Input:** headless (bool)
**Output:** Page structure analysis
**Purpose:** Debugging tool to inspect the booking page

**How Agent Uses Tools:**
```python
# The LLM generates tool calls like:
{
  "tool": "parse_date",
  "input": {"date_string": "13 oct"}
}

# The agent executor runs the tool and gets the result
# Then the LLM can use this result to make decisions
```

---

### 4️⃣ **utils/browser_automation.py** - Browser Control

**Role:** Controls a real Chrome browser to interact with Microsoft Bookings website

**Key Class:** `BookingAutomation`

**Main Functions:**

#### `fetch_available_slots(date)`
**What it does:**
1. Opens Chrome browser (using Playwright)
2. Navigates to Microsoft Bookings URL
3. Waits for page to load (5 seconds)
4. If date provided, clicks on that date in the calendar
5. Waits for time slots to appear (3 seconds)
6. Scrapes all time slot buttons/text from the page
7. Returns list of slots: `[{time: "10:00 AM", selector: "..."}]`

**How it finds slots:**
- **Strategy 1:** Looks for `<button>` elements with time text
- **Strategy 2:** Uses regex to find time patterns (e.g., "10:00 AM") in page text
- **Strategy 3:** Searches entire page HTML for time formats

#### `book_meeting_sync(url, slot_info, user_details)`
**What it does:**
1. Opens booking page
2. Clicks on the selected date
3. Clicks on the selected time slot
4. Fills in the booking form:
   - Name field
   - Email field
   - Phone field
   - Notes/purpose field
5. Clicks "Book" button
6. Waits for confirmation
7. Returns success/failure

**Synchronous Wrappers:**
- `fetch_slots_sync()` - Sync version of `fetch_available_slots()`
- `book_meeting_sync()` - Sync version of `book_meeting()`

These wrappers use `asyncio.run()` to run async Playwright code in a sync context.

---

### 5️⃣ **utils/api_booking.py** - Direct API Calls

**Role:** Books meetings via direct HTTP API calls instead of browser automation

**Why?** API calls are:
- ✅ **Faster** (no browser startup time)
- ✅ **More reliable** (no UI changes breaking automation)
- ✅ **Less resource-intensive**

**Key Class:** `BookingAPI`

#### `create_booking_payload(date, time, name, email, phone, notes)`
**What it does:** Creates the JSON payload that Microsoft Bookings API expects

**Example payload:**
```json
{
  "appointment": {
    "startTime": {
      "dateTime": "2025-10-13T10:00:00",
      "timeZone": "Bangladesh Standard Time"
    },
    "endTime": {
      "dateTime": "2025-10-13T10:30:00",
      "timeZone": "Bangladesh Standard Time"
    },
    "serviceId": "bc2ea66a-7e7f-4ae4-9b20-d68a2aa1c3a0",
    "customers": [{
      "name": "sohel",
      "emailAddress": "sohel@gmail.com",
      "phone": "+88091993939",
      "notes": "Meeting with CEO"
    }]
  }
}
```

#### `book_appointment(date, time, name, email, phone, notes)`
**What it does:**
1. Creates the payload
2. Sends POST request to:
   `https://outlook.office365.com/BookingsService/api/V1/bookingBusinessesc2/SoftwareSolution@iglobe.dk/appointments`
3. Returns response

#### `book_appointment_sync()`
**What it does:** Synchronous wrapper that handles asyncio event loops correctly

---

## 🔄 Complete Execution Flow

Let me trace a complete booking from start to finish:

### **Step-by-Step Execution:**

```
USER: "book a meeting in 13 oct 10 am"
```

**1. graph.py: BookingAgent.process_message()**
   - Adds user message to state
   - `next_action` is empty, so runs full workflow
   - Calls `workflow.invoke(state)`

**2. nodes.py: extract_requirements_node()**
   - LLM analyzes: "book a meeting in 13 oct 10 am"
   - Extracts:
     - `date_preference: "13 oct"`
     - `time_preference: "10 am"`
     - `meeting_purpose: "not_specified"`

**3. nodes.py: check_requirements_complete()**
   - Returns "complete" (date and time both present)

**4. nodes.py: fetch_slots_node()**
   - Calls agent_executor with: "Fetch available meeting slots for 13 oct"
   - **Agent decides to call 2 tools:**

   **4a. Tool: parse_date("13 oct")**
   - tools.py: ParseDateTool._run()
   - Parses "13 oct" → "2025-10-13"
   - Returns: `{"parsed": "2025-10-13"}`

   **4b. Tool: fetch_available_slots("2025-10-13")**
   - tools.py: FetchAvailableSlotsTool._run()
   - Calls: browser_automation.fetch_slots_sync()
   - **Browser automation:**
     - Opens Chrome
     - Goes to MS Bookings URL
     - Clicks date "13" on calendar
     - Waits 3 seconds
     - Finds all time slots on page
     - Returns: `[{time: "10:00 AM"}, {time: "11:45 AM"}, ...]`
   - Returns: `{"slots": [...]}`

   - **Updates state:**
     - `date_preference: "2025-10-13"` (now in parsed format!)
     - `available_slots: [{time: "10:00 AM"}, ...]`

**5. nodes.py: select_slot_node()**
   - User wanted "10 am"
   - Finds "10:00 AM" in available slots
   - `selected_slot: {time: "10:00 AM", ...}`
   - `next_action: "collect_user_info"`

**6. nodes.py: collect_user_info_node()**
   - Checks: name? ❌  email? ❌  phone? ❌
   - Adds AI message: "Great! I found a slot at 10:00 AM. To complete the booking, I need your name, email, and phone number."
   - `next_action: "wait_for_user_info"`
   - **Returns control to user**

---

```
USER: "sohel, sohel0911@gmail.com, +88091993939"
```

**7. graph.py: BookingAgent.process_message()**
   - Sees `next_action == "wait_for_user_info"`
   - Calls extract_user_info_node()

**8. nodes.py: extract_user_info_node()**
   - **Regex extraction:**
     - Email regex matches: "sohel0911@gmail.com"
     - Phone regex matches: "+88091993939"
     - Name extracted: "sohel" (text after removing email/phone)
   - **Updates state:**
     - `user_name: "sohel"`
     - `user_email: "sohel0911@gmail.com"`
     - `user_phone: "+88091993939"`
   - Logs: `"After regex extraction - Name: sohel, Email: sohel0911@gmail.com, Phone: +88091993939"`

**9. nodes.py: collect_user_info_node()**
   - Checks: name? ✅  email? ✅  phone? ✅
   - All info collected!
   - `next_action: "wait_for_confirmation"`

**10. graph.py: Automatic transition**
   - Sees `next_action == "wait_for_confirmation"`
   - **Immediately calls confirm_booking_node()** (no waiting!)

**11. nodes.py: confirm_booking_node()**
   - Creates confirmation message with all details
   - Adds AI message: "Let me confirm the details: ..."
   - **Returns control to user**

---

```
USER: "yes"
```

**12. graph.py: BookingAgent.process_message()**
   - Sees `next_action == "wait_for_confirmation"`
   - Calls check_confirmation()

**13. nodes.py: check_confirmation()**
   - Checks if message contains "yes", "confirm", etc.
   - Returns "confirmed"

**14. nodes.py: book_meeting_node()**
   - **Direct tool call** (not through agent executor!):

   **14a. Tool: book_meeting()**
   - tools.py: BookMeetingTool._run()
   - Date already parsed: "2025-10-13" ✅
   - Calls: api_booking.book_appointment_sync()

   **14b. API Booking:**
   - utils/api_booking.py: book_appointment_sync()
   - Creates payload with all booking details
   - Sends POST to Microsoft Bookings API
   - **If successful:** Returns `{"success": True, "confirmation_message": "..."}`
   - **If failed:** Returns `{"success": False, "error": "..."}`

   - **Updates state:**
     - `booking_confirmed: True/False`
   - Adds AI message: "Your meeting has been successfully booked!" or error message

**15. Returns final message to user**

---

## 🎯 Key Design Patterns

### 1. **State Machine Pattern** (LangGraph)
- Each node represents a state in the conversation
- `next_action` determines which state to transition to
- Clear separation of concerns

### 2. **Tool Pattern** (LangChain)
- LLM cannot directly call functions
- Tools wrap functions in a schema the LLM understands
- Agent executor handles tool calls automatically

### 3. **Async/Sync Bridge**
- Playwright is async
- LangChain tools are sync
- Wrappers use `asyncio.run()` to bridge

### 4. **Fallback Strategy**
- Regex extraction first (fast, reliable)
- LLM extraction as fallback (flexible, handles edge cases)
- API booking preferred, browser automation as backup

### 5. **Stateful Conversation**
- State persists across turns
- No need to repeat information
- Can track complex multi-turn workflows

---

## 📊 Data Flow Diagram

```
User Input
    ↓
graph.py (Router)
    ↓
nodes.py (Workflow Step)
    ↓
tools.py (AI-Callable Function)
    ↓
utils/ (External System Access)
    ↓
Microsoft Bookings API/Website
    ↓
Response back up the chain
    ↓
User Output
```

---

## 🔧 Why This Architecture?

✅ **Modular**: Each component has a single responsibility
✅ **Testable**: Can test each node/tool independently
✅ **Maintainable**: Changes to one part don't break others
✅ **Scalable**: Easy to add new nodes or tools
✅ **Debuggable**: Clear logging at each step
✅ **Flexible**: Can handle various conversation flows

---

## 🐛 Common Issues & How They're Handled

1. **Date Format Issues**
   - Fixed: Always parse dates in fetch_slots_node
   - Store parsed format in state

2. **Duplicate Asks**
   - Fixed: Check `next_action` matches expected value
   - Auto-transition after extraction succeeds

3. **Re-scraping**
   - Fixed: Direct tool call in book_meeting_node
   - Bypass agent executor to prevent re-analysis

4. **Event Loop Conflicts**
   - Fixed: Check for existing loop, use ThreadPoolExecutor
   - Proper async/sync bridging

---

This architecture allows for a natural, human-like conversation flow while maintaining strict control over the booking process!

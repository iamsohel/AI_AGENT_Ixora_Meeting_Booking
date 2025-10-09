# Tests

This directory contains integration tests for the Ixora Meeting Booking API.

## Available Tests

### `test_integration.py`
Full integration test that validates:
- SSE streaming functionality
- Status updates during agent processing
- Response formatting (newlines, lists, bullet points)
- Complete booking conversation flow

**Usage:**
```bash
# Make sure API server is running first
python tests/test_integration.py
```

### `test_cancel_flow.py`
Tests the booking cancellation and state reset flow:
- User declines booking confirmation
- State is properly reset (clears all booking data)
- New booking requests are treated fresh
- Prevents proceeding with cancelled bookings

**Usage:**
```bash
python tests/test_cancel_flow.py
```

### `test_simple_validations.py`
Demonstration of validation features:
- Greeting detection (hi, hello, etc.)
- Slot number validation (rejects out-of-range numbers)
- Name length validation (minimum 2 characters)
- Email format validation

**Usage:**
```bash
python tests/test_simple_validations.py
```

**Requirements:**
- API server running on `http://localhost:8000`
- Valid environment variables:
  - `GOOGLE_API_KEY`
  - `IXORA_BOOKING_URL`

## Running Tests

1. Start the API server:
```bash
uv run python api.py
```

2. In another terminal, run the tests:
```bash
python tests/test_integration.py
```

## Expected Output

The test will:
1. Create a new session
2. Request a meeting booking
3. Select a time slot
4. Provide user information
5. Display the confirmation (without actually booking)

You should see:
- Status updates (e.g., "Understanding your request...", "Checking available time slots...")
- Properly formatted slot listings
- Structured confirmation details with date, time, name, email, phone

"""Custom LangChain tools for meeting booking operations."""

import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from utils.browser_automation import analyze_page_sync, fetch_slots_sync

logger = logging.getLogger(__name__)


class FetchSlotsInput(BaseModel):
    """Input for FetchAvailableSlotsTool."""
    date: Optional[str] = Field(
        default=None,
        description="Optional date in YYYY-MM-DD format to check availability. If not provided, checks current/next available dates."
    )


class FetchAvailableSlotsTool(BaseTool):
    """Tool to fetch available meeting slots from Microsoft Bookings."""

    name: str = "fetch_available_slots"
    description: str = (
        "Fetches available meeting time slots from the Microsoft Bookings page. "
        "Can optionally specify a date in YYYY-MM-DD format. "
        "Returns a list of available time slots with their details."
    )
    args_schema: type[BaseModel] = FetchSlotsInput

    def _run(self, date: Optional[str] = None) -> str:
        """Fetch available slots."""
        booking_url = os.getenv("IXORA_BOOKING_URL")
        if not booking_url:
            return json.dumps({
                "error": "IXORA_BOOKING_URL not configured in environment"
            })

        try:
            # Validate date format if provided
            if date:
                try:
                    datetime.strptime(date, "%Y-%m-%d")
                except ValueError:
                    return json.dumps({
                        "error": f"Invalid date format: {date}. Use YYYY-MM-DD"
                    })

            slots = fetch_slots_sync(booking_url, date, headless=True)

            if not slots:
                return json.dumps({
                    "message": "No available slots found for the specified date",
                    "slots": []
                })

            return json.dumps({
                "message": f"Found {len(slots)} available slots",
                "date": date or "current/upcoming dates",
                "slots": slots
            }, indent=2)

        except Exception as e:
            return json.dumps({
                "error": f"Failed to fetch slots: {str(e)}"
            })

    async def _arun(self, date: Optional[str] = None) -> str:
        """Async implementation."""
        # For now, use sync version
        return self._run(date)


class BookMeetingInput(BaseModel):
    """Input for BookMeetingTool."""
    date: str = Field(
        description="The date for the meeting (e.g., '12 october', '2025-10-12')"
    )
    slot_time: str = Field(
        description="The time slot to book (e.g., '2:00 PM', '14:00', '10:00 AM')"
    )
    name: str = Field(description="Full name of the person booking the meeting")
    email: str = Field(description="Email address of the person booking the meeting")
    phone: str = Field(description="Phone number of the person booking the meeting")
    notes: Optional[str] = Field(
        default="",
        description="Optional notes or meeting purpose"
    )


class BookMeetingTool(BaseTool):
    """Tool to book a meeting slot on Microsoft Bookings."""

    name: str = "book_meeting"
    description: str = (
        "Books a meeting slot on Microsoft Bookings with user details. "
        "Requires date, slot_time, name, email, phone, and optional notes. "
        "Returns confirmation details or error message."
    )
    args_schema: type[BaseModel] = BookMeetingInput

    def _run(
        self,
        date: str,
        slot_time: str,
        name: str,
        email: str,
        phone: str,
        notes: str = ""
    ) -> str:
        """Book a meeting slot."""
        booking_url = os.getenv("IXORA_BOOKING_URL")
        if not booking_url:
            return json.dumps({
                "error": "IXORA_BOOKING_URL not configured in environment"
            })

        try:
            # Validate email format
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                return json.dumps({
                    "error": f"Invalid email format: {email}"
                })

            # Parse date to YYYY-MM-DD format if needed
            parsed_date = date
            # If date is not in YYYY-MM-DD format, parse it
            if not re.match(r'\d{4}-\d{2}-\d{2}', date):
                # Use Python's built-in datetime parsing
                try:
                    from datetime import datetime
                    # Try common formats
                    for fmt in ["%B %d", "%b %d", "%d %B", "%d %b"]:
                        try:
                            parsed = datetime.strptime(date, fmt)
                            # Add current year (or next year if date has passed)
                            today = datetime.now()
                            parsed = parsed.replace(year=today.year)
                            if parsed < today:
                                parsed = parsed.replace(year=today.year + 1)
                            parsed_date = parsed.strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                except:
                    # If all parsing fails, use as-is
                    pass

            # Create slot info
            slot_info = {
                "time": slot_time,
                "date": parsed_date,  # Include date in slot info
                "selector": f'div:has-text("{slot_time}")',
                "aria_label": slot_time
            }

            # Use improved browser automation with all fixes
            from utils.api_booking import book_appointment_sync
            from utils.browser_automation import book_meeting_sync

            logger.info(f"Booking via browser: {parsed_date} at {slot_time}")

            # Prepare user details dictionary
            user_details = {
                "name": name,
                "email": email,
                "phone": phone,
                "notes": notes
            }

            # result = book_meeting_sync(
            #     booking_url,
            #     slot_info,
            #     user_details,
            #     headless=True
            # )

            result = book_appointment_sync(parsed_date, slot_time, name, email, phone, notes)

            logger.info(f"Browser booking result: {result.get('success')}")
            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({
                "error": f"Failed to book meeting: {str(e)}"
            })

    async def _arun(
        self,
        date: str,
        slot_time: str,
        name: str,
        email: str,
        phone: str,
        notes: str = ""
    ) -> str:
        """Async implementation."""
        return self._run(date, slot_time, name, email, phone, notes)


class ValidateUserInfoInput(BaseModel):
    """Input for ValidateUserInfoTool."""
    email: str = Field(description="Email address to validate")
    phone: Optional[str] = Field(default=None, description="Phone number to validate")


class ValidateUserInfoTool(BaseTool):
    """Tool to validate user information."""

    name: str = "validate_user_info"
    description: str = (
        "Validates user information like email and phone number format. "
        "Returns validation results."
    )
    args_schema: type[BaseModel] = ValidateUserInfoInput

    def _run(self, email: str, phone: Optional[str] = None) -> str:
        """Validate user information."""
        results = {
            "email_valid": False,
            "phone_valid": None,
            "errors": []
        }

        # Validate email
        if re.match(r"[^@]+@[^@]+\.[^@]+", email):
            results["email_valid"] = True
        else:
            results["errors"].append(f"Invalid email format: {email}")

        # Validate phone if provided
        if phone:
            # Basic phone validation (digits, spaces, dashes, parentheses, plus sign)
            if re.match(r"^[\d\s\-\(\)\+]+$", phone) and len(re.sub(r"\D", "", phone)) >= 10:
                results["phone_valid"] = True
            else:
                results["phone_valid"] = False
                results["errors"].append(f"Invalid phone format: {phone}")

        return json.dumps(results, indent=2)

    async def _arun(self, email: str, phone: Optional[str] = None) -> str:
        """Async implementation."""
        return self._run(email, phone)


class AnalyzeBookingPageInput(BaseModel):
    """Input for AnalyzeBookingPageTool."""
    headless: bool = Field(
        default=False,
        description="Whether to run browser in headless mode"
    )


class AnalyzeBookingPageTool(BaseTool):
    """Tool to analyze the booking page structure."""

    name: str = "analyze_booking_page"
    description: str = (
        "Analyzes the Microsoft Bookings page structure to identify form fields, "
        "buttons, and other elements. Useful for debugging. Takes screenshot."
    )
    args_schema: type[BaseModel] = AnalyzeBookingPageInput

    def _run(self, headless: bool = False) -> str:
        """Analyze booking page structure."""
        booking_url = os.getenv("IXORA_BOOKING_URL")
        if not booking_url:
            return json.dumps({
                "error": "IXORA_BOOKING_URL not configured in environment"
            })

        try:
            structure = analyze_page_sync(booking_url, headless)
            return json.dumps(structure, indent=2)
        except Exception as e:
            return json.dumps({
                "error": f"Failed to analyze page: {str(e)}"
            })

    async def _arun(self, headless: bool = False) -> str:
        """Async implementation."""
        return self._run(headless)


class ParseDateInput(BaseModel):
    """Input for ParseDateTool."""
    date_string: str = Field(
        description="Natural language date string to parse (e.g., 'next Tuesday', 'October 15')"
    )


class ParseDateTool(BaseTool):
    """Tool to parse natural language dates into YYYY-MM-DD format."""

    name: str = "parse_date"
    description: str = (
        "Parses natural language date strings into YYYY-MM-DD format. "
        "Handles relative dates like 'tomorrow', 'next Tuesday', specific dates like 'October 15', etc."
    )
    args_schema: type[BaseModel] = ParseDateInput

    def _run(self, date_string: str) -> str:
        """Parse date string."""
        try:
            today = datetime.now()
            date_string_lower = date_string.lower().strip()

            # Handle relative dates
            if date_string_lower == "today":
                target_date = today
            elif date_string_lower == "tomorrow":
                target_date = today + timedelta(days=1)
            elif "next week" in date_string_lower:
                target_date = today + timedelta(weeks=1)
            elif date_string_lower.startswith("next "):
                # Handle "next Monday", "next Tuesday", etc.
                day_name = date_string_lower.replace("next ", "").strip()
                weekdays = {
                    "monday": 0, "tuesday": 1, "wednesday": 2,
                    "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
                }

                if day_name in weekdays:
                    target_weekday = weekdays[day_name]
                    current_weekday = today.weekday()
                    days_ahead = target_weekday - current_weekday
                    if days_ahead <= 0:  # Target day already happened this week
                        days_ahead += 7
                    target_date = today + timedelta(days=days_ahead)
                else:
                    return json.dumps({
                        "error": f"Unknown day name: {day_name}"
                    })
            else:
                # Try to parse as specific date
                # Try common formats
                formats = [
                    "%Y-%m-%d",
                    "%B %d",  # October 15
                    "%b %d",  # Oct 15
                    "%d %B",  # 15 October
                    "%d %b",  # 15 Oct
                    "%B %d, %Y",  # October 15, 2024
                    "%b %d, %Y",  # Oct 15, 2024
                    "%d %B %Y",  # 15 October 2024
                    "%d %b %Y",  # 15 Oct 2024
                    "%m/%d/%Y",
                    "%m/%d",
                    "%d/%m/%Y",
                    "%d/%m",
                ]

                target_date = None
                for fmt in formats:
                    try:
                        target_date = datetime.strptime(date_string, fmt)
                        # If year not specified, use current year
                        if target_date.year == 1900:
                            target_date = target_date.replace(year=today.year)
                        # If the parsed date is in the past, assume next year
                        if target_date < today and target_date.year == today.year:
                            target_date = target_date.replace(year=today.year + 1)
                        break
                    except ValueError:
                        continue

                if not target_date:
                    return json.dumps({
                        "error": f"Could not parse date: {date_string}"
                    })

            return json.dumps({
                "original": date_string,
                "parsed": target_date.strftime("%Y-%m-%d"),
                "formatted": target_date.strftime("%B %d, %Y")
            }, indent=2)

        except Exception as e:
            return json.dumps({
                "error": f"Failed to parse date: {str(e)}"
            })

    async def _arun(self, date_string: str) -> str:
        """Async implementation."""
        return self._run(date_string)


# Export all tools
def get_all_tools() -> List[BaseTool]:
    """Get all available booking tools."""
    return [
        FetchAvailableSlotsTool(),
        BookMeetingTool(),
        ValidateUserInfoTool(),
        AnalyzeBookingPageTool(),
        ParseDateTool(),
    ]

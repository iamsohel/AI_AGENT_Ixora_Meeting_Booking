"""Custom LangChain tools for meeting booking operations."""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import List

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BookMeetingInput(BaseModel):
    """Input for BookMeetingTool."""
    date: str = Field(
        description="The date for the meeting (e.g., '12 october', '2025-10-12')"
    )
    slot_time: str = Field(
        description="The time slot to book (e.g., '2:00 PM', '14:00', '10:00 AM')"
    )
    name: str = Field(
        description="Full name of the person booking the meeting")
    email: str = Field(
        description="Email address of the person booking the meeting")
    phone: str = Field(
        description="Phone number of the person booking the meeting")
    notes: str = Field(
        default="",
        description="Optional notes or meeting purpose"
    )


class BookMeetingTool(BaseTool):
    """Tool to book a meeting slot using the Microsoft Bookings API."""

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
        try:
            # Validate email format
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                return json.dumps({
                    "error": f"Invalid email format: {email}"
                })

            # Parse date to YYYY-MM-DD format if needed
            parsed_date = date
            if not re.match(r'\d{4}-\d{2}-\d{2}', date):
                # Try common formats
                try:
                    for fmt in ["%B %d", "%b %d", "%d %B", "%d %b"]:
                        try:
                            parsed = datetime.strptime(date, fmt)
                            today = datetime.now()
                            parsed = parsed.replace(year=today.year)
                            if parsed < today:
                                parsed = parsed.replace(year=today.year + 1)
                            parsed_date = parsed.strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass

            # Use API booking
            from utils.api_booking import book_appointment_sync

            logger.info(f"Booking via API: {parsed_date} at {slot_time}")
            result = book_appointment_sync(
                parsed_date, slot_time, name, email, phone, notes)

            logger.info(f"Booking result: {result.get('success')}")
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
    phone: str = Field(
        default="",
        description="Phone number to validate")


class ValidateUserInfoTool(BaseTool):
    """Tool to validate user information."""

    name: str = "validate_user_info"
    description: str = (
        "Validates user information like email and phone number format. "
        "Returns validation results."
    )
    args_schema: type[BaseModel] = ValidateUserInfoInput

    def _run(self, email: str, phone: str = "") -> str:
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
            # Basic phone validation
            if re.match(r"^[\d\s\-\(\)\+]+$", phone) and len(re.sub(r"\D", "", phone)) >= 10:
                results["phone_valid"] = True
            else:
                results["phone_valid"] = False
                results["errors"].append(f"Invalid phone format: {phone}")

        return json.dumps(results, indent=2)

    async def _arun(self, email: str, phone: str = "") -> str:
        """Async implementation."""
        return self._run(email, phone)


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

            # Remove ordinal suffixes (1st, 2nd, 3rd, 4th, etc.)
            date_string = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_string)
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
                    if days_ahead <= 0:
                        days_ahead += 7
                    target_date = today + timedelta(days=days_ahead)
                else:
                    return json.dumps({
                        "error": f"Unknown day name: {day_name}"
                    })
            else:
                # Try to parse as specific date
                formats = [
                    "%Y-%m-%d",
                    "%B %d", "%b %d", "%d %B", "%d %b",
                    "%B %d, %Y", "%b %d, %Y",
                    "%d %B, %Y", "%d %b, %Y",
                    "%d %B %Y", "%d %b %Y",
                    "%m/%d/%Y", "%m/%d",
                    "%d/%m/%Y", "%d/%m",
                ]

                target_date = None
                for fmt in formats:
                    try:
                        target_date = datetime.strptime(date_string, fmt)
                        if target_date.year == 1900:
                            target_date = target_date.replace(year=today.year)
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


def get_all_tools() -> List[BaseTool]:
    """Get all available booking tools."""
    return [
        ParseDateTool(),
        ValidateUserInfoTool(),
        BookMeetingTool(),
    ]

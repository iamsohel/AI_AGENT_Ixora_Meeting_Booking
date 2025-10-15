"""Direct API booking for Microsoft Bookings."""
import logging
from datetime import datetime
from typing import Dict

import httpx

from utils.cache import get_cache

logger = logging.getLogger(__name__)

# Global HTTP client with connection pooling
_http_client = None


class BookingAPI:
    """Direct API client for Microsoft Bookings."""

    def __init__(self, business_email: str = "SoftwareSolution@iglobe.dk"):
        """Initialize the booking API client."""
        self.business_email = business_email
        self.base_url = f"https://outlook.office365.com/BookingsService/api/V1/bookingBusinessesc2/{business_email}"

        # Fixed IDs from the booking page
        self.service_id = "bc2ea66a-7e7f-4ae4-9b20-d68a2aa1c3a0"
        self.staff_ids = [
            "622acedc-716a-4287-9198-08f340ffecf3",
            "29272458-d06e-4125-b710-5914403055d9"
        ]
        self.timezone = "Bangladesh Standard Time"

    async def get_available_slots(
        self,
        start_date: str,  # "2025-10-12" format
        end_date: str = None  # Optional, defaults to same day for optimal performance
    ) -> Dict:
        """Get available time slots using GetStaffAvailability API.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (optional, defaults to same day for faster response)

        Returns:
            Dict with success status and list of available slots
        """
        try:
            import time
            from datetime import datetime, timedelta

            # Check cache first
            cache = get_cache()
            cache_key = f"slots_{start_date}_{end_date or start_date}"
            cached_result = cache.get(cache_key)

            if cached_result:
                logger.info(f"⚡ Cache HIT for {start_date} - returning cached slots (instant!)")
                return cached_result

            logger.info(f"Cache MISS for {start_date} - fetching from API")

            # Parse start date
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")

            # If no end date, default to same day (single day query for faster response)
            if not end_date:
                end_dt = start_dt  # Query only the requested date
            else:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            # Format dates for API
            start_datetime_str = start_dt.strftime("%Y-%m-%dT00:00:00")
            end_datetime_str = end_dt.strftime("%Y-%m-%dT23:59:59")

            # Build payload
            payload = {
                "serviceId": self.service_id,
                "staffIds": self.staff_ids,
                "startDateTime": {
                    "dateTime": start_datetime_str,
                    "timeZone": self.timezone
                },
                "endDateTime": {
                    "dateTime": end_datetime_str,
                    "timeZone": self.timezone
                }
            }

            date_range = f"{start_date}" if start_dt == end_dt else f"{start_date} to {end_dt.strftime('%Y-%m-%d')}"
            logger.info(f"Fetching available slots for: {date_range}")
            logger.debug(f"Payload: {payload}")

            # Make API request
            endpoint = f"{self.base_url}/GetStaffAvailability"

            # Start timing
            start_time = time.time()
            logger.info(f"Starting API call to GetStaffAvailability at {time.strftime('%H:%M:%S')}")

            # Use HTTP client with connection pooling for better performance
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            async with httpx.AsyncClient(
                timeout=120.0,
                limits=limits
            ) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip, deflate"  # Enable compression
                    }
                )

                # Calculate elapsed time
                elapsed_time = time.time() - start_time
                logger.info(f"API Response Status: {response.status_code}")
                logger.info(f"⏱️  API call completed in {elapsed_time:.2f} seconds")

                if response.status_code == 200:
                    response_data = response.json()
                    logger.debug(f"Raw API response: {response_data}")  # Changed to debug level

                    # Parse available slots
                    available_slots = []

                    staff_availability = response_data.get("staffAvailabilityResponse", [])

                    for staff in staff_availability:
                        staff_id = staff.get("staffId", "")
                        availability_items = staff.get("availabilityItems", [])

                        for item in availability_items:
                            status = item.get("status", "")

                            # Only include AVAILABLE slots
                            if status == "BOOKINGSAVAILABILITYSTATUS_AVAILABLE":
                                start_time_info = item.get("startDateTime", {})
                                start_time_str = start_time_info.get("dateTime", "")

                                if start_time_str:
                                    # Parse and format the time
                                    try:
                                        slot_dt = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S")
                                        time_formatted = slot_dt.strftime("%I:%M %p")  # e.g., "10:00 AM"
                                        date_formatted = slot_dt.strftime("%Y-%m-%d")

                                        # Only include slots for the requested date
                                        if date_formatted == start_date:
                                            available_slots.append({
                                                "time": time_formatted,
                                                "datetime": start_time_str,
                                                "date": date_formatted,
                                                "staff_id": staff_id
                                            })
                                    except Exception as e:
                                        logger.warning(f"Error parsing slot time: {e}")
                                        continue

                    # Sort slots by time
                    available_slots.sort(key=lambda x: x["datetime"])

                    logger.info(f"Found {len(available_slots)} available slots")

                    result = {
                        "success": True,
                        "slots": available_slots,
                        "date": start_date
                    }

                    # Cache the result for 10 minutes (600 seconds)
                    cache.set(cache_key, result, ttl=600)
                    logger.info(f"✓ Cached result for {start_date} (TTL: 10 minutes)")

                    return result
                else:
                    # Error
                    logger.error(f"API request failed with status {response.status_code}")
                    logger.error(f"Response: {response.text[:500]}")

                    return {
                        "success": False,
                        "error": f"API returned status {response.status_code}",
                        "details": response.text[:500]
                    }

        except httpx.TimeoutException:
            elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
            logger.error(f"❌ GetStaffAvailability API request timed out after {elapsed_time:.2f} seconds")
            return {
                "success": False,
                "error": f"API request timed out after {elapsed_time:.2f} seconds (max: 120s)"
            }
        except ValueError as e:
            logger.error(f"Invalid date format: {e}")
            return {
                "success": False,
                "error": f"Invalid date format: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error fetching available slots: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }

    def create_booking_payload(
        self,
        date: str,  # "2025-10-12"
        time: str,  # "10:00 AM"
        name: str,
        email: str,
        phone: str = "",
        notes: str = ""
    ) -> Dict:
        """Create the booking payload in Microsoft Bookings format.

        Args:
            date: Date in YYYY-MM-DD format
            time: Time in "HH:MM AM/PM" format
            name: Customer name
            email: Customer email
            phone: Customer phone
            notes: Booking notes

        Returns:
            Dict payload ready for API submission
        """
        # Parse date and time
        date_obj = datetime.strptime(date, "%Y-%m-%d")

        # Parse time (e.g., "10:00 AM")
        time_obj = datetime.strptime(time, "%I:%M %p")

        # Combine date and time
        start_datetime = datetime(
            date_obj.year,
            date_obj.month,
            date_obj.day,
            time_obj.hour,
            time_obj.minute
        )

        # End time is 30 minutes after start (default meeting duration)
        from datetime import timedelta
        end_datetime = start_datetime + timedelta(minutes=30)

        # Format as ISO string without timezone
        start_str = start_datetime.strftime("%Y-%m-%dT%H:%M:%S")
        end_str = end_datetime.strftime("%Y-%m-%dT%H:%M:%S")

        # Build the payload
        payload = {
            "appointment": {
                "startTime": {
                    "dateTime": start_str,
                    "timeZone": self.timezone
                },
                "endTime": {
                    "dateTime": end_str,
                    "timeZone": self.timezone
                },
                "serviceId": self.service_id,
                # Use first staff member
                "staffMemberIds": [self.staff_ids[0]],
                "customers": [
                    {
                        "name": name,
                        "emailAddress": email,
                        "phone": phone,
                        "notes": notes,
                        "timeZone": self.timezone,
                        "answeredCustomQuestions": [],
                        "location": {
                            "displayName": "",
                            "address": {
                                "street": "",
                                "type": "Other"
                            }
                        },
                        "smsNotificationsEnabled": False,
                        "instanceId": "",
                        "price": 0,
                        "priceType": "SERVICEDEFAULTPRICETYPES_NOT_SET"
                    }
                ],
                "isLocationOnline": True,
                "smsNotificationsEnabled": False,
                "verificationCode": "",
                "customerTimeZone": self.timezone,
                "trackingDataId": "",
                "bookingFormInfoList": [],
                "price": 0,
                "priceType": "SERVICEDEFAULTPRICETYPES_NOT_SET",
                "isAllDay": False,
                "additionalRecipients": []
            },
            "preferences": {
                "staffCandidates": self.staff_ids
            }
        }

        return payload

    async def book_appointment(
        self,
        date: str,
        time: str,
        name: str,
        email: str,
        phone: str = "",
        notes: str = ""
    ) -> Dict:
        """Book an appointment via direct API call.

        Args:
            date: Date in YYYY-MM-DD format
            time: Time in "HH:MM AM/PM" format
            name: Customer name
            email: Customer email
            phone: Customer phone
            notes: Booking notes

        Returns:
            Dict with success status and response details
        """
        try:
            import time as time_module
            from datetime import datetime as dt

            # Create payload
            payload = self.create_booking_payload(
                date, time, name, email, phone, notes)

            logger.info(f"Booking appointment for {name} on {date} at {time}")
            logger.info(f"Payload: {payload}")

            # Make API request
            endpoint = f"{self.base_url}/appointments"

            # Start timing
            start_time = time_module.time()
            logger.info(f"Starting API call to book appointment at {dt.now().strftime('%H:%M:%S')}")

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                )

                # Calculate elapsed time
                elapsed_time = time_module.time() - start_time

                print("RES:::, ", response.status_code, response.json())

                logger.info(f"API Response Status: {response.status_code}")
                logger.info(f"⏱️  Booking API call completed in {elapsed_time:.2f} seconds")

                if response.status_code in [200, 201]:
                    # Success
                    try:
                        response_data = response.json()
                        logger.info("Booking successful!")
                        return {
                            "success": True,
                            "confirmation_message": "Meeting booked successfully via API",
                            "booking_id": response_data.get("id", "N/A"),
                            "response": response_data
                        }
                    except:
                        return {
                            "success": True,
                            "confirmation_message": "Meeting booked successfully via API",
                            "response_text": response.text[:500]
                        }
                else:
                    # Error
                    logger.error(
                        f"Booking failed with status {response.status_code}")
                    logger.error(f"Response: {response.text[:500]}")

                    return {
                        "success": False,
                        "error": f"API returned status {response.status_code}",
                        "details": response.text[:500]
                    }

        except httpx.TimeoutException:
            elapsed_time = time_module.time() - start_time if 'start_time' in locals() else 0
            logger.error(f"❌ Booking API request timed out after {elapsed_time:.2f} seconds")
            return {
                "success": False,
                "error": f"API request timed out after {elapsed_time:.2f} seconds (max: 300s)"
            }
        except ValueError as e:
            # Date/time format errors
            logger.error(f"Invalid date/time format: {e}")
            return {
                "success": False,
                "error": f"Invalid date/time format: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }


def get_available_slots_sync(
    start_date: str,
    end_date: str = None
) -> Dict:
    """Synchronous wrapper for getting available slots.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (optional)

    Returns:
        Dict with success status and list of available slots
    """
    import asyncio

    api = BookingAPI()

    async def _get_slots():
        return await api.get_available_slots(start_date, end_date)

    # Check if there's an existing event loop
    try:
        asyncio.get_running_loop()
        # If we're in a running loop, run in a thread to avoid conflicts
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _get_slots())
            return future.result()
    except RuntimeError:
        # No running loop, safe to use asyncio.run directly
        return asyncio.run(_get_slots())


def book_appointment_sync(
    date: str,
    time: str,
    name: str,
    email: str,
    phone: str = "",
    notes: str = ""
) -> Dict:
    """Synchronous wrapper for booking appointment.

    Args:
        date: Date in YYYY-MM-DD format
        time: Time in "HH:MM AM/PM" format
        name: Customer name
        email: Customer email
        phone: Customer phone
        notes: Booking notes

    Returns:
        Dict with success status and response details
    """
    import asyncio

    api = BookingAPI()

    async def _book():
        return await api.book_appointment(date, time, name, email, phone, notes)

    # Check if there's an existing event loop
    try:
        asyncio.get_running_loop()
        # If we're in a running loop, run in a thread to avoid conflicts
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _book())
            return future.result()
    except RuntimeError:
        # No running loop, safe to use asyncio.run directly
        return asyncio.run(_book())

"""Direct API booking for Microsoft Bookings."""
import logging
from datetime import datetime
from typing import Dict
import httpx

logger = logging.getLogger(__name__)


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
                "staffMemberIds": [self.staff_ids[0]],  # Use first staff member
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
            # Create payload
            payload = self.create_booking_payload(date, time, name, email, phone, notes)

            logger.info(f"Booking appointment for {name} on {date} at {time}")
            logger.debug(f"Payload: {payload}")

            # Make API request
            endpoint = f"{self.base_url}/appointments"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                )

                logger.info(f"API Response Status: {response.status_code}")

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
                    logger.error(f"Booking failed with status {response.status_code}")
                    logger.error(f"Response: {response.text[:500]}")

                    return {
                        "success": False,
                        "error": f"API returned status {response.status_code}",
                        "details": response.text[:500]
                    }

        except httpx.TimeoutException:
            logger.error("API request timed out")
            return {
                "success": False,
                "error": "API request timed out after 30 seconds"
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

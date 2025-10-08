"""API booking with browser session for authentication."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict
import httpx
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


async def book_with_browser_session(
    booking_url: str,
    date: str,
    time: str,
    name: str,
    email: str,
    phone: str = "",
    notes: str = ""
) -> Dict:
    """Book appointment using API with browser session cookies.

    This hybrid approach:
    1. Opens browser and navigates to booking page
    2. Extracts session cookies
    3. Uses cookies to make authenticated API call

    Args:
        booking_url: The Microsoft Bookings page URL
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
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Navigate to booking page to establish session
            logger.info("Navigating to booking page to establish session...")
            await page.goto(booking_url, wait_until="networkidle")
            await page.wait_for_timeout(2000)

            # Extract cookies
            cookies = await context.cookies()
            logger.info(f"Extracted {len(cookies)} cookies from browser session")

            # Close browser
            await browser.close()

            # Build cookie dictionary for httpx
            cookie_dict = {cookie["name"]: cookie["value"] for cookie in cookies}

            # Now make API call with cookies
            business_email = "SoftwareSolution@iglobe.dk"
            api_url = f"https://outlook.office365.com/BookingsService/api/V1/bookingBusinessesc2/{business_email}/appointments"

            # Parse date and time
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            time_obj = datetime.strptime(time, "%I:%M %p")

            start_datetime = datetime(
                date_obj.year,
                date_obj.month,
                date_obj.day,
                time_obj.hour,
                time_obj.minute
            )
            end_datetime = start_datetime + timedelta(minutes=30)

            # Create payload
            payload = {
                "appointment": {
                    "startTime": {
                        "dateTime": start_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
                        "timeZone": "Bangladesh Standard Time"
                    },
                    "endTime": {
                        "dateTime": end_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
                        "timeZone": "Bangladesh Standard Time"
                    },
                    "serviceId": "bc2ea66a-7e7f-4ae4-9b20-d68a2aa1c3a0",
                    "staffMemberIds": ["622acedc-716a-4287-9198-08f340ffecf3"],
                    "customers": [
                        {
                            "name": name,
                            "emailAddress": email,
                            "phone": phone,
                            "notes": notes,
                            "timeZone": "Bangladesh Standard Time",
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
                    "customerTimeZone": "Bangladesh Standard Time",
                    "trackingDataId": "",
                    "bookingFormInfoList": [],
                    "price": 0,
                    "priceType": "SERVICEDEFAULTPRICETYPES_NOT_SET",
                    "isAllDay": False,
                    "additionalRecipients": []
                },
                "preferences": {
                    "staffCandidates": [
                        "622acedc-716a-4287-9198-08f340ffecf3",
                        "29272458-d06e-4125-b710-5914403055d9"
                    ]
                }
            }

            logger.info(f"Making API call to: {api_url}")
            logger.info(f"With {len(cookie_dict)} cookies")

            # Make API request with cookies
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    api_url,
                    json=payload,
                    cookies=cookie_dict,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                        "Referer": booking_url,
                        "Origin": "https://outlook.office365.com"
                    }
                )

                logger.info(f"API Response Status: {response.status_code}")
                logger.debug(f"Response Text: {response.text[:500]}")

                if response.status_code in [200, 201]:
                    try:
                        response_data = response.json()
                        return {
                            "success": True,
                            "confirmation_message": "Meeting booked successfully via API",
                            "booking_id": response_data.get("id", "N/A"),
                            "response": response_data
                        }
                    except:
                        return {
                            "success": True,
                            "confirmation_message": "Meeting booked successfully",
                            "response_text": response.text[:500]
                        }
                else:
                    return {
                        "success": False,
                        "error": f"API returned status {response.status_code}",
                        "details": response.text[:500]
                    }

    except Exception as e:
        logger.error(f"Error in book_with_browser_session: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }


def book_with_session_sync(
    booking_url: str,
    date: str,
    time: str,
    name: str,
    email: str,
    phone: str = "",
    notes: str = ""
) -> Dict:
    """Synchronous wrapper for book_with_browser_session."""
    return asyncio.run(
        book_with_browser_session(booking_url, date, time, name, email, phone, notes)
    )

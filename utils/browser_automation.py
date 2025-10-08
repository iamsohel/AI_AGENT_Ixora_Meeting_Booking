"""Browser automation utilities using Playwright for Microsoft Bookings."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Page, Browser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BookingAutomation:
    """Handles browser automation for Microsoft Bookings."""

    def __init__(self, booking_url: str, headless: bool = True):
        self.booking_url = booking_url
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def navigate_to_booking_page(self) -> bool:
        """Navigate to the Microsoft Bookings page."""
        try:
            logger.info(f"Navigating to booking page: {self.booking_url}")
            await self.page.goto(self.booking_url, wait_until="networkidle", timeout=60000)

            # Wait for the page to be fully loaded
            await self.page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(5)  # Additional wait for dynamic content to load

            logger.info("Successfully navigated to booking page")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to booking page: {e}")
            return False

    async def fetch_available_slots(self, date: Optional[str] = None) -> List[Dict]:
        """
        Fetch available time slots from the booking page.
        Microsoft Bookings shows slots on the right side after selecting a date.

        Args:
            date: Optional date string in format 'YYYY-MM-DD'

        Returns:
            List of available slots with datetime and slot info
        """
        try:
            await self.navigate_to_booking_page()

            # Wait for calendar to be visible
            await self.page.wait_for_timeout(2000)

            # If specific date provided, select it from the calendar
            if date:
                date_selected = await self._select_date(date)
                if not date_selected:
                    logger.error(f"Failed to select date {date} - date may not be available for booking")
                    return []
            else:
                # If no date specified, click on today or the first available date
                logger.info("No date specified, looking for first available date")
                # The current date is usually pre-selected or highlighted
                # Just wait a bit for time slots to appear
                await self.page.wait_for_timeout(2000)

            # Wait for time slots to load after date selection
            await self.page.wait_for_timeout(3000)

            # Microsoft Bookings shows time slots as buttons with time text (e.g., "12:15 PM")
            # They appear in the TIME section on the right side
            logger.info("Looking for time slot buttons...")

            slots = []

            # Strategy 1: Find all visible buttons and clickable elements
            # Include divs that might be acting as buttons
            all_elements = await self.page.query_selector_all('button, div[role="button"], [role="button"]')
            logger.info(f"Found {len(all_elements)} total clickable elements on page")

            import re
            for element in all_elements:
                try:
                    is_visible = await element.is_visible()
                    if not is_visible:
                        continue

                    text = await element.inner_text()
                    if not text:
                        continue

                    text_clean = text.strip()
                    aria_label = await element.get_attribute("aria-label")

                    # Check if text looks like a time
                    # Pattern: "12:15 PM" or "1:15 PM" (with or without space before AM/PM)
                    time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM))', text_clean, re.IGNORECASE)

                    if time_match:
                        time_text = time_match.group(1)
                        slot_info = {
                            "time": time_text,
                            "aria_label": aria_label,
                            "selector": "element",
                            # Don't store element - not JSON serializable
                        }
                        slots.append(slot_info)
                        logger.info(f"Found time slot: {time_text}")

                except Exception as e:
                    logger.debug(f"Error checking element: {e}")

            # If still no slots found, try alternative approach
            if not slots:
                logger.warning("No slots found with element strategy, trying comprehensive text search...")

                # Get all text content and search for time patterns
                body_text = await self.page.inner_text('body')
                import re
                time_patterns = re.findall(r'\d{1,2}:\d{2}\s*(?:AM|PM)', body_text, re.IGNORECASE)

                if time_patterns:
                    unique_times = sorted(set(time_patterns))
                    logger.info(f"Found {len(unique_times)} unique time patterns in page text: {unique_times}")

                    # Try multiple selector strategies for each time
                    for time_text in unique_times:
                        try:
                            # Try different selectors
                            selectors_to_try = [
                                f'button:has-text("{time_text}")',
                                f'div:has-text("{time_text}")',
                                f'[role="button"]:has-text("{time_text}")',
                            ]

                            for selector in selectors_to_try:
                                try:
                                    element = await self.page.query_selector(selector)
                                    if element:
                                        is_visible = await element.is_visible()
                                        if is_visible:
                                            # Check if this element is actually clickable
                                            aria_label = await element.get_attribute("aria-label")
                                            slot_info = {
                                                "time": time_text,
                                                "aria_label": aria_label,
                                                "selector": selector,
                                                # Don't include element - it's not JSON serializable
                                            }
                                            slots.append(slot_info)
                                            logger.info(f"Found time slot via text search: {time_text}")
                                            break  # Found it, no need to try other selectors
                                except:
                                    continue
                        except Exception as e:
                            logger.debug(f"Error in text search for {time_text}: {e}")

            # If still no slots found, take a screenshot for debugging
            if not slots:
                screenshot_path = "no_slots_debug.png"
                await self.page.screenshot(path=screenshot_path, full_page=True)
                logger.warning(f"No slots found. Screenshot saved to {screenshot_path}")

                # Log what we see on the page
                body_text = await self.page.inner_text('body')
                logger.debug(f"Page text (first 1000 chars): {body_text[:1000]}")

            logger.info(f"Found {len(slots)} available slots")
            return slots

        except Exception as e:
            logger.error(f"Error fetching available slots: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def _select_date(self, date: str) -> bool:
        """Select a specific date on the booking calendar.
        Microsoft Bookings shows a calendar grid with date numbers as buttons.

        Returns:
            True if date was selected successfully, False otherwise
        """
        try:
            # Parse the target date
            target_date = datetime.strptime(date, "%Y-%m-%d")
            logger.info(f"Selecting date: {date} (day: {target_date.day}, month: {target_date.strftime('%B')})")

            # Wait for calendar to be visible
            await self.page.wait_for_timeout(2000)

            # First, make sure we're in the correct month
            # Look for month navigation (next/previous buttons)
            current_month_year = target_date.strftime("%B %Y")

            # Try to find the month/year display
            month_display = await self.page.inner_text('body')
            if current_month_year not in month_display:
                logger.info(f"Need to navigate to {current_month_year}")

                # Find next/previous month buttons and click as needed
                # This is simplified - you may need to click multiple times
                next_button = await self.page.query_selector('button[aria-label*="next" i], button[aria-label*="forward" i]')
                if next_button:
                    logger.info("Clicking next month button")
                    await next_button.click()
                    await self.page.wait_for_timeout(1000)

            # Now find the date button in the calendar
            # Microsoft Bookings calendar uses buttons/divs with just the day number
            logger.info(f"Looking for day {target_date.day} in calendar")

            # Find all clickable elements (buttons, divs with role=button, etc.)
            all_elements = await self.page.query_selector_all('button, div[role="button"], div[role="gridcell"], [role="gridcell"] button')

            potential_date_elements = []
            for element in all_elements:
                try:
                    is_visible = await element.is_visible()
                    if not is_visible:
                        continue

                    text = await element.inner_text()
                    text_stripped = text.strip()

                    # Check if it's a day number (1-31)
                    if text_stripped.isdigit() and 1 <= int(text_stripped) <= 31:
                        if int(text_stripped) == target_date.day:
                            potential_date_elements.append(element)
                            logger.info(f"Found potential date element: {text_stripped}")

                except:
                    pass

            # Try to click the date element
            if potential_date_elements:
                logger.info(f"Found {len(potential_date_elements)} elements for day {target_date.day}")
                # Click the first one (there might be multiple if showing multiple months)
                await potential_date_elements[0].click()
                await self.page.wait_for_timeout(3000)  # Wait for time slots to load
                logger.info(f"Successfully clicked date {target_date.day}")
                return True

            logger.warning(f"Could not find clickable element for date {target_date.day}")
            return False

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error selecting date: {error_msg}")

            # Check if date is not available (disabled)
            if "element is not enabled" in error_msg.lower():
                logger.warning(f"Date {date} is not available for booking (element disabled)")

            import traceback
            logger.error(traceback.format_exc())
            return False

    async def book_slot(
        self,
        slot_info: Dict,
        user_details: Dict[str, str]
    ) -> Dict:
        """
        Book a specific time slot with user details.

        Args:
            slot_info: Slot information from fetch_available_slots (includes 'element' reference)
            user_details: Dict with 'name', 'email', 'phone', 'notes'

        Returns:
            Dict with booking status and confirmation details
        """
        try:
            time = slot_info.get("time")
            date = slot_info.get("date")  # Get date from slot_info
            logger.info(f"Attempting to book slot at {time} on {date}")

            # Navigate to booking page
            logger.info("Navigating to booking page...")
            await self.navigate_to_booking_page()

            # Select the date if provided
            if date:
                logger.info(f"Selecting date: {date}")
                date_selected = await self._select_date(date)
                if not date_selected:
                    return {
                        "success": False,
                        "error": f"Could not select date {date} - date may not be available for booking"
                    }

            # Wait for slots to appear after date selection
            await self.page.wait_for_timeout(3000)

            # Check if we have the element reference from fetch_available_slots
            slot_element = slot_info.get("element")

            if slot_element:
                # We have direct reference to the element - use it
                logger.info("Using stored element reference to click slot")
                try:
                    await slot_element.click()
                    logger.info(f"Clicked slot button for {time}")
                except Exception as e:
                    logger.warning(f"Stored element click failed: {e}, trying to find it again")
                    slot_element = None

            # If no element reference or click failed, find it again
            if not slot_element:
                logger.info(f"Finding slot button for {time}")

                # Try to find the button with the time text
                selector = slot_info.get("selector", "")
                aria_label = slot_info.get("aria_label")

                # Try multiple strategies
                selectors_to_try = [
                    f'button:has-text("{time}")',
                    f'div:has-text("{time}")',
                    f'[role="button"]:has-text("{time}")',
                ]

                if aria_label:
                    selectors_to_try.insert(0, f'[aria-label="{aria_label}"]')

                slot_button = None
                for sel in selectors_to_try:
                    try:
                        slot_button = await self.page.query_selector(sel)
                        if slot_button:
                            is_visible = await slot_button.is_visible()
                            if is_visible:
                                logger.info(f"Found slot button with selector: {sel}")
                                break
                    except:
                        continue

                if not slot_button:
                    return {
                        "success": False,
                        "error": f"Could not find clickable slot button for {time}"
                    }

                await slot_button.click()
                logger.info(f"Clicked slot button for {time}")

            # Wait for form to appear and radio button to be selected
            await self.page.wait_for_timeout(2000)

            # CRITICAL: Verify that a time slot radio button is actually selected
            # Microsoft Bookings uses radio buttons named "selectedTimeSlot"
            logger.info("Verifying time slot radio button selection...")
            selected_radio = await self.page.query_selector('input[name="selectedTimeSlot"]:checked')

            if not selected_radio:
                logger.warning("No time slot radio button is selected! Attempting to select manually...")
                # Try to find and click the first enabled time slot radio button
                # NOTE: Radio buttons are typically hidden, so don't check visibility
                radio_buttons = await self.page.query_selector_all('input[name="selectedTimeSlot"]')
                logger.info(f"Found {len(radio_buttons)} radio buttons")

                for i, radio in enumerate(radio_buttons):
                    try:
                        is_enabled = await radio.is_enabled()
                        if is_enabled:
                            await radio.click()
                            logger.info(f"Clicked radio button {i}")

                            # Verify it's now checked
                            await self.page.wait_for_timeout(500)
                            is_checked = await radio.is_checked()
                            logger.info(f"Radio button checked: {is_checked}")

                            if is_checked:
                                break
                    except Exception as e:
                        logger.debug(f"Error with radio {i}: {e}")
                        continue

                await self.page.wait_for_timeout(1000)

            # Fill in the booking form
            logger.info("Filling booking form...")
            await self._fill_booking_form(user_details)

            # Submit the booking
            logger.info("Submitting booking...")
            result = await self._submit_booking()

            return result

        except Exception as e:
            logger.error(f"Error booking slot: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }

    async def _fill_booking_form(self, user_details: Dict[str, str]):
        """Fill in the booking form with user details.
        Based on Microsoft Bookings form structure."""
        try:
            logger.info("Waiting for form to be visible...")
            await self.page.wait_for_timeout(1000)

            # Name field - labeled "First and last name"
            name_selectors = [
                'input[placeholder*="First and last name"]',
                'input[placeholder*="name"]',
                'input[aria-label*="name" i]',
                'input[name="name"]',
                'input[type="text"]',  # Often the first text input
            ]
            filled_name = await self._fill_field(name_selectors, user_details.get("name", ""))
            if filled_name:
                logger.info(f"✓ Filled name: {user_details.get('name', '')}")

            # Email field
            email_selectors = [
                'input[type="email"]',
                'input[placeholder*="Email" i]',
                'input[aria-label*="email" i]',
                'input[name="email"]',
            ]
            filled_email = await self._fill_field(email_selectors, user_details.get("email", ""))
            if filled_email:
                logger.info(f"✓ Filled email: {user_details.get('email', '')}")

            # Phone field
            phone_selectors = [
                'input[placeholder*="phone" i]',
                'input[type="tel"]',
                'input[aria-label*="phone" i]',
                'input[name="phone"]',
            ]
            filled_phone = await self._fill_field(phone_selectors, user_details.get("phone", ""))
            if filled_phone:
                logger.info(f"✓ Filled phone: {user_details.get('phone', '')}")

            # Notes/Special requests field (optional)
            if user_details.get("notes"):
                notes_selectors = [
                    'textarea[placeholder*="special requests" i]',
                    'textarea[placeholder*="Add any" i]',
                    'textarea[aria-label*="notes" i]',
                    'textarea[aria-label*="requests" i]',
                    'textarea[name="notes"]',
                ]
                filled_notes = await self._fill_field(notes_selectors, user_details.get("notes", ""))
                if filled_notes:
                    logger.info(f"✓ Filled notes: {user_details.get('notes', '')}")

            logger.info("Successfully filled booking form")

        except Exception as e:
            logger.error(f"Error filling booking form: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    async def _fill_field(self, selectors: List[str], value: str) -> bool:
        """Try multiple selectors to fill a form field.
        Returns True if field was filled successfully."""
        if not value:
            return False

        for selector in selectors:
            try:
                field = await self.page.query_selector(selector)
                if field:
                    is_visible = await field.is_visible()
                    if is_visible:
                        await field.fill(value)
                        logger.debug(f"Filled field {selector}")
                        return True
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue

        logger.warning(f"Could not find visible field with any selector")
        return False

    async def _submit_booking(self) -> Dict:
        """Submit the booking form and capture confirmation."""
        try:
            # Look for submit/book button
            submit_selectors = [
                'button[type="submit"]',
                'button:has-text("Book")',
                'button:has-text("Schedule")',
                'button:has-text("Confirm")',
                'button[aria-label*="book" i]',
                'button[aria-label*="submit" i]'
            ]

            submit_button = None
            for selector in submit_selectors:
                submit_button = await self.page.query_selector(selector)
                if submit_button:
                    break

            if not submit_button:
                return {
                    "success": False,
                    "error": "Could not find submit button"
                }

            # Click submit and wait for response
            await submit_button.click()

            # Wait for confirmation page/message
            await self.page.wait_for_timeout(3000)

            # Look for confirmation indicators
            confirmation_selectors = [
                '[role="alert"]:has-text("confirmed" i)',
                '[role="alert"]:has-text("booked" i)',
                '.confirmation-message',
                '[data-testid*="confirmation"]'
            ]

            for selector in confirmation_selectors:
                confirmation = await self.page.query_selector(selector)
                if confirmation:
                    message = await confirmation.inner_text()
                    return {
                        "success": True,
                        "confirmation_message": message.strip()
                    }

            # If no explicit confirmation found, check URL change or page title
            current_url = self.page.url
            if "confirmation" in current_url.lower() or "success" in current_url.lower():
                return {
                    "success": True,
                    "confirmation_message": "Booking confirmed (URL indicates success)"
                }

            # Take screenshot for debugging
            await self.page.screenshot(path="booking_result.png")

            return {
                "success": True,
                "confirmation_message": "Booking submitted (confirmation not explicitly detected)",
                "note": "Screenshot saved as booking_result.png for verification"
            }

        except Exception as e:
            logger.error(f"Error submitting booking: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def analyze_page_structure(self) -> Dict:
        """
        Analyze the booking page structure to identify selectors.
        Useful for debugging and initial setup.
        """
        try:
            await self.navigate_to_booking_page()

            # Extract all interactive elements
            buttons = await self.page.query_selector_all("button")
            inputs = await self.page.query_selector_all("input")
            textareas = await self.page.query_selector_all("textarea")

            structure = {
                "url": self.page.url,
                "title": await self.page.title(),
                "buttons": [],
                "inputs": [],
                "textareas": []
            }

            for btn in buttons:
                text = await btn.inner_text()
                aria_label = await btn.get_attribute("aria-label")
                data_testid = await btn.get_attribute("data-testid")
                structure["buttons"].append({
                    "text": text.strip()[:50] if text else "",
                    "aria_label": aria_label,
                    "data_testid": data_testid
                })

            for inp in inputs:
                name = await inp.get_attribute("name")
                input_type = await inp.get_attribute("type")
                aria_label = await inp.get_attribute("aria-label")
                placeholder = await inp.get_attribute("placeholder")
                structure["inputs"].append({
                    "name": name,
                    "type": input_type,
                    "aria_label": aria_label,
                    "placeholder": placeholder
                })

            for ta in textareas:
                name = await ta.get_attribute("name")
                aria_label = await ta.get_attribute("aria-label")
                placeholder = await ta.get_attribute("placeholder")
                structure["textareas"].append({
                    "name": name,
                    "aria_label": aria_label,
                    "placeholder": placeholder
                })

            # Take screenshot
            await self.page.screenshot(path="page_structure.png")
            structure["screenshot"] = "page_structure.png"

            return structure

        except Exception as e:
            logger.error(f"Error analyzing page structure: {e}")
            return {"error": str(e)}


# Synchronous wrapper functions for easier integration
def fetch_slots_sync(booking_url: str, date: Optional[str] = None, headless: bool = True) -> List[Dict]:
    """Synchronous wrapper for fetching available slots."""
    async def _fetch():
        async with BookingAutomation(booking_url, headless) as automation:
            return await automation.fetch_available_slots(date)

    return asyncio.run(_fetch())


def book_meeting_sync(
    booking_url: str,
    slot_info: Dict,
    user_details: Dict[str, str],
    headless: bool = True
) -> Dict:
    """Synchronous wrapper for booking a meeting."""
    async def _book():
        async with BookingAutomation(booking_url, headless) as automation:
            return await automation.book_slot(slot_info, user_details)

    return asyncio.run(_book())


def analyze_page_sync(booking_url: str, headless: bool = False) -> Dict:
    """Synchronous wrapper for analyzing page structure."""
    async def _analyze():
        async with BookingAutomation(booking_url, headless) as automation:
            return await automation.analyze_page_structure()

    return asyncio.run(_analyze())

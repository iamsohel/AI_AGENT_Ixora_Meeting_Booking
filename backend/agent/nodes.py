"""Agent nodes for meeting booking workflow."""

import json
from typing import Annotated, Literal, TypedDict

from langchain.agents import AgentExecutor
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


class AgentState(TypedDict):
    """State for the booking agent."""
    messages: Annotated[list, "The conversation messages"]
    user_intent: str  # What the user wants to do
    date_preference: str  # Preferred date
    time_preference: str  # Preferred time
    meeting_purpose: str  # Purpose/notes for the meeting
    user_name: str  # User's full name
    user_email: str  # User's email
    user_phone: str  # User's phone number
    available_slots: list  # Fetched available slots
    selected_slot: dict  # Selected slot for booking
    booking_confirmed: bool  # Whether booking is confirmed
    next_action: str  # Next step to take


def extract_requirements_node(state: AgentState, llm) -> AgentState:
    """Extract meeting requirements from conversation."""
    messages = state["messages"]

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at extracting meeting requirements from conversation.
        Analyze the conversation and extract:
        - date_preference: The preferred date (if mentioned). Extract ONLY the date, not the time.
        - meeting_purpose: The purpose or notes for the meeting (if mentioned)

        If any information is missing, indicate it as 'not_specified'.

        Return your response as JSON with keys: date_preference, meeting_purpose"""),
        MessagesPlaceholder(variable_name="messages"),
        ("user", "Extract the meeting requirements from the conversation above.")
    ])

    # Track LLM call
    from utils.llm_tracker import track_llm_call
    track_llm_call(
        call_type="chat",
        location="nodes.py:extract_requirements_node",
        model=getattr(llm, 'model_name', 'unknown'),
        purpose="Extract date/purpose from conversation"
    )

    chain = prompt | llm
    response = chain.invoke({"messages": messages})

    # Parse the response
    try:
        # Try to extract JSON from response
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        requirements = json.loads(content)

        state["date_preference"] = requirements.get(
            "date_preference", "not_specified")
        state["meeting_purpose"] = requirements.get(
            "meeting_purpose", "not_specified")

        # Set time_preference to "not_specified" since we no longer extract it
        state["time_preference"] = "not_specified"

    except Exception as e:
        # If parsing fails, keep as not_specified
        state["date_preference"] = state.get(
            "date_preference", "not_specified")
        state["meeting_purpose"] = state.get(
            "meeting_purpose", "not_specified")
        state["time_preference"] = "not_specified"

    return state


def check_requirements_complete(state: AgentState) -> Literal["complete", "incomplete"]:
    """Check if all requirements are gathered."""
    # Only date is required now; time will be selected from available slots
    if state.get("date_preference", "not_specified") == "not_specified":
        return "incomplete"

    return "complete"


def ask_for_missing_info_node(state: AgentState, llm) -> AgentState:
    """Ask user for missing information."""
    date_missing = state.get("date_preference", "not_specified") == "not_specified"

    if date_missing:
        prompt = "What date would you like to schedule the meeting? (e.g., 'tomorrow', 'next Monday', 'October 15')"
    else:
        # This shouldn't happen since we only require date, but handle it gracefully
        prompt = "What date would you like to schedule the meeting?"

    state["next_action"] = "wait_for_user_input"
    state["messages"].append(AIMessage(content=prompt))

    return state


def fetch_slots_node(state: AgentState, agent_executor: AgentExecutor) -> AgentState:
    """Fetch available slots using the API."""
    import logging

    logger = logging.getLogger(__name__)
    date_pref = state.get("date_preference", "")

    if not date_pref or date_pref == "not_specified":
        logger.error("No date preference specified")
        state["available_slots"] = []
        return state

    # Use agent to parse date if needed
    query = f"Parse the date: {date_pref}"
    response = agent_executor.invoke({
        "input": query
    })

    # Extract parsed date from the intermediate steps (tool calls)
    parsed_date = None
    try:
        # Check intermediate_steps for tool calls
        intermediate_steps = response.get("intermediate_steps", [])
        for step in intermediate_steps:
            # Each step is (AgentAction, tool_output)
            if len(step) >= 2:
                action, tool_output = step[0], step[1]

                # Extract parsed date from parse_date tool call
                if hasattr(action, 'tool') and action.tool == "parse_date":
                    if isinstance(tool_output, str):
                        try:
                            date_data = json.loads(tool_output)
                            parsed_date = date_data.get("parsed")
                            if parsed_date:
                                # Update state with parsed date in YYYY-MM-DD format
                                state["date_preference"] = parsed_date
                                logger.info(f"Parsed date: {parsed_date}")
                        except Exception as e:
                            logger.error(f"Error parsing date: {e}")
                            pass
    except Exception as e:
        logger.error(f"Error extracting parsed date: {e}")
        pass

    # If date parsing failed, try to use the date as-is if it's already in YYYY-MM-DD format
    if not parsed_date:
        import re
        if re.match(r'\d{4}-\d{2}-\d{2}', date_pref):
            parsed_date = date_pref
            state["date_preference"] = parsed_date
        else:
            logger.error(f"Could not parse date: {date_pref}")
            state["available_slots"] = []
            return state

    # Now fetch available slots using the API
    try:
        from utils.api_booking import get_available_slots_sync

        logger.info(f"Fetching available slots for {parsed_date}")
        result = get_available_slots_sync(parsed_date)

        if result.get("success"):
            slots = result.get("slots", [])
            state["available_slots"] = slots
            logger.info(f"Found {len(slots)} available slots")
        else:
            error = result.get("error", "Unknown error")
            logger.error(f"Failed to fetch slots: {error}")
            state["available_slots"] = []

    except Exception as e:
        logger.error(f"Error fetching slots: {e}")
        import traceback
        logger.error(traceback.format_exc())
        state["available_slots"] = []

    return state


def select_slot_node(state: AgentState, llm) -> AgentState:
    """Show available time slots for user to select."""
    available_slots = state.get("available_slots", [])

    if not available_slots:
        state["messages"].append(
            AIMessage(
                content="No available slots found for your preferred date. Would you like to try a different date?")
        )
        state["next_action"] = "wait_for_new_date"
        return state

    # Check if user has already selected a slot
    if state.get("selected_slot"):
        # Slot already selected, move on
        return state

    # Show numbered list of all available slots for user to choose
    slot_list = []
    for i, slot in enumerate(available_slots, 1):
        time = slot.get("time", "Unknown time")
        slot_list.append(f"  {i}. {time}")

    # Format the date nicely
    date_preference = state.get("date_preference", "")
    date_display = date_preference
    if date_preference and date_preference != "not_specified":
        try:
            from datetime import datetime
            parsed_date = datetime.strptime(date_preference, "%Y-%m-%d")
            date_display = parsed_date.strftime("%B %d, %Y")  # e.g., "October 14, 2025"
        except:
            date_display = date_preference

    slots_message = f"""Great! I found {len(available_slots)} available time slot(s) for {date_display}:

{chr(10).join(slot_list)}

Please select a time slot by number (e.g., "1" for the first slot)."""

    state["messages"].append(AIMessage(content=slots_message))
    state["next_action"] = "wait_for_slot_selection"

    return state


def process_slot_selection_node(state: AgentState, llm) -> AgentState:
    """Process user's slot selection."""
    available_slots = state.get("available_slots", [])
    last_message = state["messages"][-1] if state["messages"] else None

    if not last_message:
        state["next_action"] = "wait_for_slot_selection"
        return state

    user_input = last_message.content.strip()

    # Try to parse as slot number
    try:
        slot_number = int(user_input)

        # Validate slot number is within range
        if slot_number < 1 or slot_number > len(available_slots):
            state["messages"].append(
                AIMessage(
                    content=f"Sorry, slot number {slot_number} is not valid. Please choose a number between 1 and {len(available_slots)}.")
            )
            state["next_action"] = "wait_for_slot_selection"
            return state

        # Valid slot number
        state["selected_slot"] = available_slots[slot_number - 1]
        state["messages"].append(
            AIMessage(
                content=f"Perfect! You've selected the {available_slots[slot_number - 1].get('time')} slot.")
        )
        state["next_action"] = "collect_user_info"
        return state
    except ValueError:
        pass

    # Use LLM to match user's preference with available slots
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are matching a user's time preference with available slots.
        Given the user's input and available slots, select the best matching slot.
        Return only the slot information as JSON."""),
        ("user", """Available slots: {slots}
        User's preference: {user_input}

        Select the best matching slot and return it as JSON.""")
    ])

    # Track LLM call
    from utils.llm_tracker import track_llm_call
    track_llm_call(
        call_type="chat",
        location="nodes.py:process_slot_selection_node",
        model=getattr(llm, 'model_name', 'unknown'),
        purpose="Match user preference to available slots"
    )

    chain = prompt | llm
    response = chain.invoke({
        "slots": json.dumps(available_slots, indent=2),
        "user_input": user_input
    })

    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        selected = json.loads(content)
        state["selected_slot"] = selected
        state["messages"].append(
            AIMessage(
                content=f"Great! You've selected the {selected.get('time')} slot.")
        )
        state["next_action"] = "collect_user_info"
    except:
        # If parsing fails, ask again
        state["messages"].append(
            AIMessage(
                content="I couldn't understand your selection. Please choose a slot number (e.g., '1', '2') or try again.")
        )
        state["next_action"] = "wait_for_slot_selection"

    return state


def collect_user_info_node(state: AgentState, llm) -> AgentState:
    """Collect user information for booking."""
    missing_info = []

    if not state.get("user_name") or state.get("user_name", "").strip() == "":
        missing_info.append("name")
    if not state.get("user_email") or state.get("user_email", "").strip() == "":
        missing_info.append("email")
    if not state.get("user_phone") or state.get("user_phone", "").strip() == "":
        missing_info.append("phone number")

    if missing_info:
        # Only ask if we haven't asked before in this round
        # Check if the last AI message already asked for this info
        last_ai_message = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage):
                last_ai_message = msg.content
                break

        # Don't ask again if we just asked for the same info
        asking_for_same_info = False
        if last_ai_message:
            if all(field in last_ai_message.lower() for field in ["name", "email", "phone"]):
                asking_for_same_info = True

        if not asking_for_same_info:
            if len(missing_info) == 3:
                # First time asking
                message = "To complete the booking, I need your name, email, and phone number."
            else:
                # Asking for specific missing fields
                message = f"I still need your {', '.join(missing_info)}. Please provide the missing information."

            state["messages"].append(AIMessage(content=message))

        state["next_action"] = "wait_for_user_info"
    else:
        # All info collected! Set correct next_action for confirmation
        state["next_action"] = "wait_for_confirmation"

    return state


def extract_user_info_node(state: AgentState, llm) -> AgentState:
    """Extract user information from messages."""
    import logging
    import re

    logger = logging.getLogger(__name__)
    messages = state["messages"]

    # First try regex-based extraction from the last user message
    if messages:
        last_user_msg = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_user_msg = msg.content
                break

        if last_user_msg:
            logger.info(f"Extracting user info from: '{last_user_msg}'")
            # Extract email using regex
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_match = re.search(email_pattern, last_user_msg)
            if email_match and not state.get("user_email"):
                state["user_email"] = email_match.group(0)
                logger.info(f"Extracted email: {state['user_email']}")

            # Extract phone using regex (supports various formats)
            # Matches: +1234567890, 1234567890, (123) 456-7890, +88 909 808, +8989809, +987777, etc.
            # Minimum 6 digits total (including country code)
            phone_pattern = r'[\+]?[\d][\d\s\-\(\)]{4,}'
            phone_match = re.search(phone_pattern, last_user_msg)
            if phone_match and not state.get("user_phone"):
                state["user_phone"] = phone_match.group(0).strip()
                logger.info(f"Extracted phone: {state['user_phone']}")

            # Extract name - try to get text that's not email or phone
            # Remove email and phone from the message
            text_without_email_phone = last_user_msg
            if email_match:
                text_without_email_phone = text_without_email_phone.replace(
                    email_match.group(0), '')
            if phone_match:
                text_without_email_phone = text_without_email_phone.replace(
                    phone_match.group(0), '')

            # Clean up and extract name
            # Remove common separators and extra whitespace
            name_text = re.sub(r'[,;]+', ' ', text_without_email_phone)
            name_text = re.sub(r'\s+', ' ', name_text).strip()

            if name_text and len(name_text) > 1 and not state.get("user_name"):
                state["user_name"] = name_text
                logger.info(f"Extracted name: {state['user_name']}")

            logger.info(
                f"After regex extraction - Name: {state.get('user_name')}, Email: {state.get('user_email')}, Phone: {state.get('user_phone')}")

    # If regex extraction didn't get everything, try LLM extraction
    if not all([state.get("user_name"), state.get("user_email"), state.get("user_phone")]):
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Extract user contact information from the conversation.
            Look for: name, email, phone number.
            The user may provide them in various formats like comma-separated or in natural language.
            Return ONLY a JSON object with keys: name, email, phone.
            If any field is not found, set it to null.

            Example input: "sohel@gmail.com, sohel rana, +8989809"
            Example output: {{"name": "sohel rana", "email": "sohel@gmail.com", "phone": "+8989809"}}
            """),
            MessagesPlaceholder(variable_name="messages"),
            ("user", "Extract the user's contact information and return ONLY the JSON object.")
        ])

        # Track LLM call
        from utils.llm_tracker import track_llm_call
        track_llm_call(
            call_type="chat",
            location="nodes.py:extract_user_info_node",
            model=getattr(llm, 'model_name', 'unknown'),
            purpose="Extract user name/email/phone"
        )

        chain = prompt | llm
        # Only use last 3 messages for context
        response = chain.invoke({"messages": messages[-3:]})

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            user_info = json.loads(content)

            if user_info.get("name") and not state.get("user_name"):
                state["user_name"] = user_info["name"]
            if user_info.get("email") and not state.get("user_email"):
                state["user_email"] = user_info["email"]
            if user_info.get("phone") and not state.get("user_phone"):
                state["user_phone"] = user_info["phone"]

        except:
            pass

    # Validate extracted information
    validation_errors = []

    # Validate name (at least 2 characters)
    if state.get("user_name"):
        name = state["user_name"].strip()
        if len(name) < 2:
            validation_errors.append("name should be at least 2 characters")
            state["user_name"] = ""  # Clear invalid name

    # Validate email format
    if state.get("user_email"):
        email = state["user_email"].strip()
        # More comprehensive email validation
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            validation_errors.append("email format is invalid")
            state["user_email"] = ""  # Clear invalid email

    # If there are validation errors, add a message
    if validation_errors:
        error_message = "I found some issues with the information provided:\n"
        for error in validation_errors:
            error_message += f"• {error}\n"
        error_message += "\nPlease provide the correct information."

        state["messages"].append(AIMessage(content=error_message))
        # Keep waiting for correct user info
        state["next_action"] = "wait_for_user_info"

    return state


def confirm_booking_node(state: AgentState, llm) -> AgentState:
    """Ask for final confirmation before booking."""
    selected_slot = state.get("selected_slot", {})
    slot_time = selected_slot.get("time", "the selected time")
    date_preference = state.get("date_preference", "")

    # Format the date nicely if available
    date_display = date_preference
    if date_preference and date_preference != "not_specified":
        try:
            from datetime import datetime
            # Try to parse and format the date
            parsed_date = datetime.strptime(date_preference, "%Y-%m-%d")
            date_display = parsed_date.strftime("%B %d, %Y")  # e.g., "October 14, 2025"
        except:
            # If parsing fails, use as-is
            date_display = date_preference

    confirmation_msg = f"""Let me confirm the details:
- Date: {date_display}
- Time: {slot_time}
- Name: {state.get('user_name', 'N/A')}
- Email: {state.get('user_email', 'N/A')}
- Phone: {state.get('user_phone', 'N/A')}

Should I proceed with the booking?"""

    state["messages"].append(AIMessage(content=confirmation_msg))
    state["next_action"] = "wait_for_confirmation"

    return state


def book_meeting_node(state: AgentState, agent_executor) -> AgentState:
    """Book the meeting using the API."""
    import logging

    logger = logging.getLogger(__name__)

    # Extract booking details from state
    selected_slot = state.get("selected_slot", {})
    date_preference = state.get("date_preference", "")
    slot_time = selected_slot.get("time", "")
    user_name = state.get("user_name", "")
    user_email = state.get("user_email", "")
    user_phone = state.get("user_phone", "")
    meeting_purpose = state.get("meeting_purpose", "")

    # Validate required fields
    if not all([date_preference, slot_time, user_name, user_email]):
        error_msg = "Missing required booking information. Please try again."
        state["messages"].append(AIMessage(content=error_msg))
        state["next_action"] = "wait_for_user_input"
        return state

    try:
        from utils.api_booking import book_appointment_sync

        logger.info(f"Booking meeting for {user_name} on {date_preference} at {slot_time}")

        # Call the booking API
        result = book_appointment_sync(
            date=date_preference,
            time=slot_time,
            name=user_name,
            email=user_email,
            phone=user_phone,
            notes=meeting_purpose if meeting_purpose != "not_specified" else ""
        )

        if result.get("success"):
            # Booking successful
            logger.info("Booking successful!")

            # Format the date nicely for the message
            date_display = date_preference
            try:
                from datetime import datetime
                parsed_date = datetime.strptime(date_preference, "%Y-%m-%d")
                date_display = parsed_date.strftime("%B %d, %Y")
            except:
                date_display = date_preference

            success_msg = f"""Great news! Your meeting has been successfully booked!

Confirmation details:
- Date: {date_display}
- Time: {slot_time}
- Name: {user_name}
- Email: {user_email}

You will receive a confirmation email shortly. Looking forward to meeting with you!"""

            state["messages"].append(AIMessage(content=success_msg))
            state["booking_confirmed"] = True
            state["next_action"] = "booking_complete"
        else:
            # Booking failed
            error = result.get("error", "Unknown error")
            logger.error(f"Booking failed: {error}")

            error_msg = f"""I apologize, but there was an issue booking your meeting: {error}

Would you like to try a different time slot?"""

            state["messages"].append(AIMessage(content=error_msg))
            state["next_action"] = "wait_for_new_date"

    except Exception as e:
        logger.error(f"Error booking meeting: {e}")
        import traceback
        logger.error(traceback.format_exc())

        error_msg = "I apologize, but there was a technical issue while booking your meeting. Please try again."
        state["messages"].append(AIMessage(content=error_msg))
        state["next_action"] = "wait_for_new_date"

    return state



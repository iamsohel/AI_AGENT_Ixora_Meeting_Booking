"""LangGraph agent nodes for meeting booking workflow."""

import json
from typing import Annotated, Literal, TypedDict

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import END, StateGraph

from agent.tools import get_all_tools


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
        - date_preference: The preferred date (if mentioned)
        - time_preference: The preferred time (if mentioned)
        - meeting_purpose: The purpose or notes for the meeting (if mentioned)

        If any information is missing, indicate it as 'not_specified'.

        Return your response as JSON with keys: date_preference, time_preference, meeting_purpose"""),
        MessagesPlaceholder(variable_name="messages"),
        ("user", "Extract the meeting requirements from the conversation above.")
    ])

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
        state["time_preference"] = requirements.get(
            "time_preference", "not_specified")
        state["meeting_purpose"] = requirements.get(
            "meeting_purpose", "not_specified")

    except Exception as e:
        # If parsing fails, keep as not_specified
        state["date_preference"] = state.get(
            "date_preference", "not_specified")
        state["time_preference"] = state.get(
            "time_preference", "not_specified")
        state["meeting_purpose"] = state.get(
            "meeting_purpose", "not_specified")

    return state


def check_requirements_complete(state: AgentState) -> Literal["complete", "incomplete"]:
    """Check if all requirements are gathered."""
    required = ["date_preference", "time_preference"]

    for field in required:
        if state.get(field, "not_specified") == "not_specified":
            return "incomplete"

    return "complete"


def ask_for_missing_info_node(state: AgentState, llm) -> AgentState:
    """Ask user for missing information."""
    missing_fields = []

    date_missing = state.get("date_preference", "not_specified") == "not_specified"
    time_missing = state.get("time_preference", "not_specified") == "not_specified"

    if date_missing:
        missing_fields.append("date")
    if time_missing:
        missing_fields.append("time")

    # If date is provided but time is missing, ask specifically for time only
    if not date_missing and time_missing:
        prompt = "What time would you prefer for the meeting?"
        state["next_action"] = "wait_for_time_only"
    elif date_missing and not time_missing:
        # Time provided but date missing - ask for date
        prompt = "What date would you like to schedule the meeting?"
        state["next_action"] = "wait_for_user_input"
    else:
        # Both missing or first time asking
        prompt = f"What {' and '.join(missing_fields)} would work best for you?"
        state["next_action"] = "wait_for_user_input"

    state["messages"].append(AIMessage(content=prompt))

    return state


def fetch_slots_node(state: AgentState, agent_executor: AgentExecutor) -> AgentState:
    """Fetch available slots using the agent."""
    date_pref = state.get("date_preference", "")

    # Use agent to parse date if needed and fetch slots
    query = f"Fetch available meeting slots"
    if date_pref and date_pref != "not_specified":
        query += f" for {date_pref}"

    response = agent_executor.invoke({
        "input": query
    })

    # Extract slots and parsed date from the intermediate steps (tool calls)
    state["available_slots"] = []
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
                        except:
                            pass

                # Check if this was a fetch_available_slots tool call
                if hasattr(action, 'tool') and action.tool == "fetch_available_slots":
                    # Parse the tool output JSON
                    if isinstance(tool_output, str):
                        try:
                            slots_data = json.loads(tool_output)
                            state["available_slots"] = slots_data.get(
                                "slots", [])
                        except:
                            pass
    except Exception as e:
        # If extraction fails, try fallback parsing
        try:
            output = response.get("output", "")
            if "slots" in output.lower():
                # Try to find JSON in the output
                import re
                json_match = re.search(r'\{[\s\S]*"slots"[\s\S]*\}', output)
                if json_match:
                    slots_data = json.loads(json_match.group(0))
                    state["available_slots"] = slots_data.get("slots", [])
        except:
            pass

    return state


def select_slot_node(state: AgentState, llm) -> AgentState:
    """Select appropriate slot based on user preferences."""
    available_slots = state.get("available_slots", [])

    if not available_slots:
        state["messages"].append(
            AIMessage(
                content="No available slots found for your preferred date. Would you like to try a different date ?")
        )
        state["next_action"] = "wait_for_new_date"
        return state

    # Check if user has already selected a slot
    if state.get("selected_slot"):
        # Slot already selected, move on
        return state

    # Check if user's time preference exactly matches an available slot
    time_pref = state.get("time_preference", "")
    if time_pref and time_pref != "not_specified":
        # Normalize time preference for comparison (e.g., "10:30 am" -> "10:30 AM")
        time_pref_normalized = time_pref.strip().upper().replace(" ", "")

        for slot in available_slots:
            slot_time = slot.get("time", "")
            slot_time_normalized = slot_time.strip().upper().replace(" ", "")

            # Check for exact match
            if time_pref_normalized == slot_time_normalized:
                # Auto-select this slot
                state["selected_slot"] = slot
                state["messages"].append(
                    AIMessage(
                        content=f"Great! I found a slot at {slot_time} on your preferred date.")
                )
                state["next_action"] = "collect_user_info"
                return state

    # No exact match found - show numbered list for user to choose
    slot_list = []
    for i, slot in enumerate(available_slots, 1):
        time = slot.get("time", "Unknown time")
        slot_list.append(f"  {i}. {time}")

    slots_message = f"""Great! I found {len(available_slots)} available slot(s) for your preferred date:

{chr(10).join(slot_list)}

Please choose a slot by number (e.g., "1")."""

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
            selected_slot = state.get("selected_slot", {})
            slot_time = selected_slot.get("time", "your preferred time")

            if len(missing_info) == 3:
                # First time asking
                message = f"Great! I found a slot at {slot_time}. To complete the booking, I need your name, email, and phone number."
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
            from langchain_core.messages import HumanMessage
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


def check_confirmation(state: AgentState, llm) -> Literal["confirmed", "declined"]:
    """Check if user confirmed the booking."""
    last_message = state["messages"][-1]

    if isinstance(last_message, HumanMessage):
        content_lower = last_message.content.lower()
        if any(word in content_lower for word in ["yes", "confirm", "proceed", "book it", "sure", "ok", "okay"]):
            return "confirmed"

    return "declined"


def book_meeting_node(state: AgentState, agent_executor: AgentExecutor) -> AgentState:
    """Execute the booking."""
    import json

    from agent.tools import BookMeetingTool

    selected_slot = state.get("selected_slot", {})
    slot_time = selected_slot.get("time", "")
    date_preference = state.get("date_preference", "")

    # Directly call the BookMeetingTool instead of using agent_executor
    # This prevents re-scraping and re-parsing
    booking_tool = BookMeetingTool()

    result_json = booking_tool._run(
        date=date_preference,
        slot_time=slot_time,
        name=state.get('user_name', ''),
        email=state.get('user_email', ''),
        phone=state.get('user_phone', ''),
        notes=state.get('meeting_purpose', 'Meeting with Ixora CEO')
    )

    # Parse the result
    try:
        result = json.loads(result_json)
        if result.get("success"):
            state["booking_confirmed"] = True
            state["messages"].append(
                AIMessage(
                    content="Your meeting has been successfully booked! You'll receive a confirmation email shortly.")
            )
            # Clear next_action after successful booking to prevent misinterpretation of follow-up messages
            state["next_action"] = "booking_complete"
        else:
            state["booking_confirmed"] = False
            error_msg = result.get("error", "Unknown error")

            # Make error message more user-friendly
            user_friendly_msg = _get_user_friendly_error_message(error_msg)

            state["messages"].append(
                AIMessage(
                    content=f"There was an issue booking the meeting: {user_friendly_msg}. Please try again.")
            )
    except Exception as e:
        state["booking_confirmed"] = False
        user_friendly_msg = _get_user_friendly_error_message(str(e))
        state["messages"].append(
            AIMessage(
                content=f"There was an issue booking the meeting: {user_friendly_msg}. Please try again.")
        )

    return state


def _get_user_friendly_error_message(error_msg: str) -> str:
    """Convert technical error messages to user-friendly messages."""
    error_lower = error_msg.lower()

    # Map technical errors to user-friendly messages
    if "status 400" in error_lower or "bad request" in error_lower:
        return "The booking information couldn't be processed. Please check your details and try again"
    elif "status 401" in error_lower or "unauthorized" in error_lower:
        return "Unable to authenticate with the booking system"
    elif "status 403" in error_lower or "forbidden" in error_lower:
        return "Access to the booking system was denied"
    elif "status 404" in error_lower or "not found" in error_lower:
        return "The booking service or time slot was not found"
    elif "status 409" in error_lower or "conflict" in error_lower:
        return "This time slot may no longer be available. Please choose a different time"
    elif "status 500" in error_lower or "status 502" in error_lower or "status 503" in error_lower:
        return "The booking system is temporarily unavailable. Please try again in a few moments"
    elif "timeout" in error_lower or "timed out" in error_lower:
        return "The booking request took too long. Please try again"
    elif "network" in error_lower or "connection" in error_lower:
        return "Unable to connect to the booking system. Please check your internet connection"
    else:
        # For unknown errors, return a generic friendly message
        return "An unexpected error occurred. Please try again or contact support if the issue persists"


def create_booking_graph(llm, agent_executor: AgentExecutor):
    """Create the LangGraph workflow for meeting booking."""

    workflow = StateGraph(AgentState)

    # Add nodes with llm/agent_executor bound
    workflow.add_node("extract_requirements",
                      lambda s: extract_requirements_node(s, llm))
    workflow.add_node("ask_missing_info",
                      lambda s: ask_for_missing_info_node(s, llm))
    workflow.add_node(
        "fetch_slots", lambda s: fetch_slots_node(s, agent_executor))
    workflow.add_node("select_slot", lambda s: select_slot_node(s, llm))
    workflow.add_node("collect_user_info",
                      lambda s: collect_user_info_node(s, llm))
    workflow.add_node("extract_user_info",
                      lambda s: extract_user_info_node(s, llm))
    workflow.add_node("confirm_booking",
                      lambda s: confirm_booking_node(s, llm))
    workflow.add_node(
        "book_meeting", lambda s: book_meeting_node(s, agent_executor))

    # Define edges
    workflow.set_entry_point("extract_requirements")

    workflow.add_conditional_edges(
        "extract_requirements",
        check_requirements_complete,
        {
            "complete": "fetch_slots",
            "incomplete": "ask_missing_info"
        }
    )

    workflow.add_edge("ask_missing_info", END)
    workflow.add_edge("fetch_slots", "select_slot")
    workflow.add_edge("select_slot", "collect_user_info")

    workflow.add_conditional_edges(
        "collect_user_info",
        lambda s: "extract" if s.get(
            "next_action") == "wait_for_user_info" else "confirm",
        {
            "extract": END,  # Wait for user to provide info
            "confirm": "confirm_booking"
        }
    )

    workflow.add_edge("extract_user_info", "collect_user_info")
    workflow.add_edge("confirm_booking", END)

    workflow.add_conditional_edges(
        "book_meeting",
        lambda s: "end" if s.get("booking_confirmed") else "end",
        {
            "end": END
        }
    )

    return workflow.compile()

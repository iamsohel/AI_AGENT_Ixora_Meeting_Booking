"""Unified agent combining RAG (company info) and Booking capabilities."""

import logging
from typing import Dict, List

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from agent.graph import create_agent_executor
from agent.llm_helpers import check_new_booking_intent, check_user_confirmation
from agent.nodes import AgentState
from agent.rag_nodes import rag_query_node
from agent.supervisor import classify_intent_node, route_to_agent

logger = logging.getLogger(__name__)


class UnifiedAgent:
    """
    Unified AI agent for Ixora Solution.

    Combines two capabilities:
    1. RAG - Answer questions about company using vector store
    2. Booking - Schedule meetings with the CEO/CTO
    """

    def __init__(self, llm):
        self.llm = llm
        self.agent_executor = create_agent_executor(llm)
        self.state = None

    def initialize_state(self):
        """Initialize a new conversation state."""
        self.state = {
            # Common fields
            "messages": [],
            "agent_mode": "rag",  # Default to RAG mode
            "previous_agent_mode": "",
            "intent_classification": {},
            # Booking-specific fields
            "user_intent": "",
            "date_preference": "not_specified",
            "time_preference": "not_specified",
            "meeting_purpose": "not_specified",
            "user_name": "",
            "user_email": "",
            "user_phone": "",
            "available_slots": [],
            "selected_slot": {},
            "booking_confirmed": False,
            "next_action": "",
            # RAG-specific fields
            "rag_sources": [],
        }

    def process_message(self, user_message: str):
        """
        Process a user message through the unified agent.

        Args:
            user_message: User's input message

        Returns:
            AI response string
        """
        # Reset LLM call tracker for this request
        from utils.llm_tracker import get_llm_call_summary, reset_llm_tracker

        reset_llm_tracker()
        logger.info(f"📨 NEW REQUEST: '{user_message[:50]}...'")

        if self.state is None:
            self.initialize_state()

        # Add user message to state
        self.state["messages"].append(HumanMessage(content=user_message))

        # Get current workflow state
        current_action = self.state.get("next_action", "")

        # Classify user intent (RAG or Booking)
        # LLM will naturally handle greetings and route to appropriate response
        self.state = classify_intent_node(self.state, self.llm)
        # agent_mode = route_to_agent(self.state)
        agent_mode = self.state["agent_mode"]

        logger.info(f"Routed to agent: {agent_mode} (current_action: {current_action})")
        logger.info(
            f"Routed to agent2: {self.state['agent_mode']} (current_action: {current_action})"
        )

        # Define booking-specific actions (don't route to booking for RAG actions)
        booking_actions = [
            "wait_for_user_input",
            "wait_for_slot_selection",
            "wait_for_new_date",
            "wait_for_user_info",
            "wait_for_confirmation",
            "wait_for_new_booking",
            "booking_complete",
        ]

        # Route to appropriate agent
        # Only route to booking if agent_mode is "booking" OR we're in a booking workflow
        if agent_mode == "booking" or (current_action in booking_actions):
            # Use the existing booking agent logic
            return self._handle_booking(user_message, current_action)
        else:
            # Use RAG to answer questions (including when current_action is "rag_complete" or empty)
            return self._handle_rag()

    def _handle_rag(self):
        """Handle RAG (company information) queries."""
        try:
            self.state = rag_query_node(self.state, self.llm)

            # Clear next_action for RAG queries (don't interfere with routing)
            # RAG sets next_action to "rag_complete", but we want to allow fresh routing next time
            print("state3 ", self.state)
            if self.state.get("next_action") in ["rag_complete", "suggest_booking"]:
                self.state["next_action"] = ""

            # Log LLM call summary
            from utils.llm_tracker import get_llm_call_summary

            summary = get_llm_call_summary()
            logger.info(
                f"✅ REQUEST COMPLETE: {summary['total_calls']} LLM calls in {summary.get('elapsed_seconds', 0):.2f}s"
            )

            # Return the last AI message
            for msg in reversed(self.state["messages"]):
                if isinstance(msg, AIMessage):
                    return msg.content

            return "How can I help you learn about Ixora Solution?"
        except Exception as e:
            logger.error(f"Error in RAG handler: {e}")

            # Log rate limit info if it's a 429 error
            if "429" in str(e) or "quota" in str(e).lower():
                from utils.llm_tracker import log_rate_limit_info

                log_rate_limit_info()

            # Log summary even on error
            from utils.llm_tracker import get_llm_call_summary

            summary = get_llm_call_summary()
            logger.info(
                f"✅ REQUEST COMPLETE (with error): {summary['total_calls']} LLM calls in {summary.get('elapsed_seconds', 0):.2f}s"
            )

            # Provide a fallback response
            self.state["messages"].append(
                AIMessage(
                    content="I apologize for the inconvenience. Our knowledge base is temporarily unavailable. "
                    "However, I can still help you book a meeting with our team.\n\n"
                    "Ixora Solution is a full-cycle offshore software development company based in Bangladesh, "
                    "specializing in custom software solutions, web and mobile development, and IT consulting services.\n\n"
                    "Would you like to schedule a meeting to learn more?"
                )
            )
            return self.state["messages"][-1].content

    def _handle_booking(self, user_message: str, current_action: str):
        """
        Handle booking workflow.

        This reuses the existing booking agent logic from graph.py
        """
        from agent.nodes import (
            ask_for_missing_info_node,
            book_meeting_node,
            check_requirements_complete,
            collect_user_info_node,
            confirm_booking_node,
            extract_requirements_node,
            extract_user_info_node,
            fetch_slots_node,
            process_slot_selection_node,
            select_slot_node,
        )

        # Use LLM to detect cancellation intent (except during confirmation)
        # We exclude confirmation because we have specific confirmation handling
        if current_action != "wait_for_confirmation" and current_action != "booking_complete":
            from agent.llm_helpers import check_cancellation_intent

            wants_to_cancel = check_cancellation_intent(user_message, current_action, self.llm)

            if wants_to_cancel:
                # User wants to exit booking and talk about company/services
                logger.info(f"🚫 BOOKING CANCELLED: User said '{user_message}'")

                # Reset booking state but keep message history
                old_messages = self.state["messages"].copy()
                self.initialize_state()
                self.state["messages"] = old_messages

                # Add natural transition message
                self.state["messages"].append(
                    AIMessage(
                        content="No problem! I'd be happy to tell you more about Ixora Solution. What would you like to know?"
                    )
                )
                self.state["next_action"] = ""
                self.state["agent_mode"] = "rag"

                # Log LLM call summary
                from utils.llm_tracker import get_llm_call_summary
                summary = get_llm_call_summary()
                logger.info(
                    f"✅ REQUEST COMPLETE (booking cancelled): {summary['total_calls']} LLM calls in {summary.get('elapsed_seconds', 0):.2f}s"
                )

                return self.state["messages"][-1].content

        # Existing booking logic from BookingAgent.process_message
        if current_action == "wait_for_user_input":
            self.state = extract_requirements_node(self.state, self.llm)
            if check_requirements_complete(self.state) == "complete":
                self.state = fetch_slots_node(self.state, self.agent_executor)
                self.state = select_slot_node(self.state, self.llm)

        elif current_action == "wait_for_new_date":
            # Reset booking state for new date
            self.state["date_preference"] = "not_specified"
            self.state["time_preference"] = "not_specified"
            self.state["available_slots"] = []
            self.state["selected_slot"] = {}

            # Use LLM to understand user intent
            intent = check_new_booking_intent(user_message, self.llm)

            if intent == "yes":
                # User wants to try again
                self.state = ask_for_missing_info_node(self.state, self.llm)
            elif intent == "no":
                # User doesn't want to book
                self.state["messages"].append(
                    AIMessage(
                        content="No problem! Feel free to reach out when you'd like to book a meeting. Have a great day!"
                    )
                )
                self.state["next_action"] = ""
            else:  # new_request
                # User provided a specific date/time
                self.state = extract_requirements_node(self.state, self.llm)
                if check_requirements_complete(self.state) == "complete":
                    self.state = fetch_slots_node(self.state, self.agent_executor)
                    self.state = select_slot_node(self.state, self.llm)
                else:
                    self.state = ask_for_missing_info_node(self.state, self.llm)

        elif current_action == "wait_for_slot_selection":
            self.state = process_slot_selection_node(self.state, self.llm)
            if self.state.get("next_action") == "collect_user_info":
                self.state = collect_user_info_node(self.state, self.llm)

        elif current_action == "wait_for_user_info":
            # Use LLM to check if user is starting a new booking or providing info
            from agent.llm_helpers import check_user_intent_in_context

            intent = check_user_intent_in_context(
                user_message,
                "We asked for your contact information (name, email, phone). Did the user provide this information or are they trying to start a new booking?",
                self.llm,
            )

            if intent == "new_booking":
                # User wants to start a new booking
                self.initialize_state()
                self.state["messages"].append(HumanMessage(content=user_message))
                self.state = extract_requirements_node(self.state, self.llm)
                if check_requirements_complete(self.state) == "complete":
                    self.state = fetch_slots_node(self.state, self.agent_executor)
                    self.state = select_slot_node(self.state, self.llm)
            else:
                # Extract user info from message (LLM handles all formats)
                self.state = extract_user_info_node(self.state, self.llm)
                self.state = collect_user_info_node(self.state, self.llm)
                if self.state.get("next_action") == "wait_for_confirmation":
                    self.state = confirm_booking_node(self.state, self.llm)

        elif current_action == "wait_for_confirmation":
            # Use LLM to check confirmation (flexible understanding)
            confirmation_result = check_user_confirmation(
                user_message, "We asked: Is this booking information correct?", self.llm
            )

            if confirmation_result == "confirmed":
                # User confirmed - proceed with booking
                self.state = book_meeting_node(self.state, self.agent_executor)
            elif confirmation_result == "cancelled":
                # User cancelled
                old_messages = self.state["messages"].copy()
                self.initialize_state()
                self.state["messages"] = old_messages
                self.state["messages"].append(
                    AIMessage(
                        content="Booking cancelled. No problem!\n\nWould you like to book a meeting for a different date?"
                    )
                )
                self.state["next_action"] = "wait_for_new_booking"
            else:  # unclear
                # Ask for clarification
                self.state["messages"].append(
                    AIMessage(
                        content="I didn't quite catch that. Please confirm if the booking details are correct by saying 'yes' to proceed or 'no' to cancel."
                    )
                )
                self.state["next_action"] = "wait_for_confirmation"

        elif current_action == "booking_complete":
            # After booking is complete, use LLM to check if user wants to book again
            intent = check_new_booking_intent(user_message, self.llm)

            if intent == "new_request":
                # User wants to book another meeting
                self.initialize_state()
                self.state["messages"].append(HumanMessage(content=user_message))
                self.state = extract_requirements_node(self.state, self.llm)
                if check_requirements_complete(self.state) == "complete":
                    self.state = fetch_slots_node(self.state, self.agent_executor)
                    self.state = select_slot_node(self.state, self.llm)
            else:
                # Let LLM generate natural response to whatever user said
                # (could be thanks, goodbye, or a question)
                # Route through supervisor for natural handling
                self.state["next_action"] = ""  # Clear action to allow new flow
                return self._handle_rag()  # Let RAG/LLM handle naturally

        elif current_action == "wait_for_new_booking":
            # Use LLM to understand user intent
            intent = check_new_booking_intent(user_message, self.llm)

            if intent == "yes":
                # User wants to book
                self.state["messages"].append(
                    AIMessage(content="Great! What date would work best for you?")
                )
                self.state["next_action"] = "wait_for_user_input"
            elif intent == "no":
                # User doesn't want to book
                self.state["messages"].append(
                    AIMessage(
                        content="No problem! Feel free to reach out when you'd like to book a meeting. Have a great day!"
                    )
                )
                self.state["next_action"] = ""
            else:  # new_request
                # User provided specific date/time
                self.state = extract_requirements_node(self.state, self.llm)
                if check_requirements_complete(self.state) == "complete":
                    self.state = fetch_slots_node(self.state, self.agent_executor)
                    self.state = select_slot_node(self.state, self.llm)
                else:
                    self.state["messages"].append(
                        AIMessage(
                            content="I didn't catch that. What date would you like to schedule the meeting?"
                        )
                    )
                    self.state["next_action"] = "wait_for_user_input"

        else:
            # Initial booking request
            self.state = extract_requirements_node(self.state, self.llm)
            if check_requirements_complete(self.state) == "complete":
                self.state = fetch_slots_node(self.state, self.agent_executor)
                self.state = select_slot_node(self.state, self.llm)
            else:
                self.state = ask_for_missing_info_node(self.state, self.llm)

        # Log LLM call summary before returning
        from utils.llm_tracker import get_llm_call_summary

        summary = get_llm_call_summary()
        logger.info(
            f"✅ REQUEST COMPLETE: {summary['total_calls']} LLM calls in {summary.get('elapsed_seconds', 0):.2f}s"
        )

        # Return the last AI message
        for msg in reversed(self.state["messages"]):
            if isinstance(msg, AIMessage):
                return msg.content

        return "I'm here to help you book a meeting. What date works for you?"

    def get_conversation_history(self):
        """Get the full conversation history."""
        return self.state["messages"] if self.state else []

    def reset(self):
        """Reset the agent state."""
        self.state = None

    async def process_message_stream(self, user_message: str):
        """
        Process a user message and stream the response with status updates.

        Args:
            user_message: The user's input message

        Yields:
            dict: Status updates and response chunks
        """
        import asyncio
        import re

        # Initialize state if needed
        if self.state is None:
            self.initialize_state()

        # Determine current action and send appropriate status
        current_action = self.state.get("next_action", "") if self.state else ""

        # Send status based on what the agent is doing
        if current_action == "wait_for_slot_selection":
            yield {"type": "status", "message": "Processing your selection..."}
        elif current_action == "wait_for_user_info":
            yield {"type": "status", "message": "Extracting your information..."}
        elif current_action == "wait_for_confirmation":
            yield {"type": "status", "message": "Processing confirmation..."}
        elif current_action in ["wait_for_new_date", "wait_for_user_input"]:
            yield {"type": "status", "message": "Fetching available time slots..."}
        else:
            # Check agent mode - different status for RAG vs Booking
            if self.state and self.state.get("agent_mode") == "rag":
                yield {"type": "status", "message": "Thinking..."}
            else:
                yield {"type": "status", "message": "Processing your request..."}

        # Get the full response (blocking - status stays visible during this)
        try:
            response = self.process_message(user_message)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            yield {"type": "status", "message": ""}
            yield {
                "type": "chunk",
                "data": "I apologize, but I encountered an error. Please try again or rephrase your question.",
            }
            return

        # Clear status and start streaming response
        yield {"type": "status", "message": ""}

        # Stream the response word by word while preserving newlines
        parts = re.split(r"(\s+)", response)

        for part in parts:
            if part:
                yield {"type": "chunk", "data": part}
                if not part.isspace():
                    await asyncio.sleep(0.03)

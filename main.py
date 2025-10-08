"""Main entry point for the Ixora Meeting Booking Agent."""

import argparse
import os
import sys

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.graph import BookingAgent

# Load environment variables
load_dotenv()

# 
# https://outlook.office365.com/BookingsService/api/V1/bookingBusinessesc2/SoftwareSolution@iglobe.dk/appointments

# {"appointment":{"startTime":{"dateTime":"2025-10-12T17:00:00","timeZone":"Bangladesh Standard Time"},"endTime":{"dateTime":"2025-10-12T17:30:00","timeZone":"Bangladesh Standard Time"},"serviceId":"bc2ea66a-7e7f-4ae4-9b20-d68a2aa1c3a0","staffMemberIds":["622acedc-716a-4287-9198-08f340ffecf3"],"customers":[{"name":"Mr. Adam","emailAddress":"adm.lord@gmail.com","phone":"","notes":"","timeZone":"Bangladesh Standard Time","answeredCustomQuestions":[],"location":{"displayName":"","address":{"street":"","type":"Other"}},"smsNotificationsEnabled":false,"instanceId":"","price":0,"priceType":"SERVICEDEFAULTPRICETYPES_NOT_SET"}],"isLocationOnline":true,"smsNotificationsEnabled":false,"verificationCode":"","customerTimeZone":"Bangladesh Standard Time","trackingDataId":"","bookingFormInfoList":[],"price":0,"priceType":"SERVICEDEFAULTPRICETYPES_NOT_SET","isAllDay":false,"additionalRecipients":[]},"preferences":{"staffCandidates":["622acedc-716a-4287-9198-08f340ffecf3","29272458-d06e-4125-b710-5914403055d9"]}}

def print_banner():
    """Print welcome banner."""
    print("\n" + "="*60)
    print(" Ixora Meeting Booking Agent")
    print("="*60)
    print("Welcome! I can help you book a meeting with Ixora Solution's CEO.")
    print("\nCommands:")
    print("  - Type your message to interact with the agent")
    print("  - 'quit' or 'exit' to end the session")
    print("  - 'reset' to start a new booking conversation")
    print("  - 'analyze' to analyze the booking page structure")
    print("="*60 + "\n")


def validate_env():
    """Validate required environment variables."""
    google_api_key = os.getenv("GOOGLE_API_KEY")
    booking_url = os.getenv("IXORA_BOOKING_URL")

    errors = []
    if not google_api_key:
        errors.append("GOOGLE_API_KEY not set in .env file")
    if not booking_url:
        errors.append("IXORA_BOOKING_URL not set in .env file")

    if errors:
        print("\n❌ Environment Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease create a .env file with the required variables.")
        print("See .env.example for reference.\n")
        return False

    return True


def run_test_mode(agent: BookingAgent):
    """Run a simulated test conversation."""
    print("\n🧪 Running in TEST MODE (simulated conversation)\n")

    test_messages = [
        "I want to book a meeting with the CEO",
        "Next Tuesday at 2 PM",
        "John Doe, john.doe@example.com, +1234567890",
        "yes"
    ]

    for i, message in enumerate(test_messages, 1):
        print(f"\n[Step {i}] User: {message}")
        response = agent.process_message(message)
        print(f"\n[Step {i}] Agent: {response}")
        print("-" * 60)

    print("\n✅ Test conversation completed!\n")


def run_interactive_mode(agent: BookingAgent):
    """Run interactive conversation mode."""
    print_banner()

    # Initial greeting
    print("Agent: Hello! I'm here to help you book a meeting with Ixora Solution's CEO.")
    print("       What date and time would work best for you?\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Handle special commands
            if user_input.lower() in ['quit', 'exit']:
                print("\nAgent: Thank you for using the Ixora Booking Agent. Goodbye!\n")
                break

            elif user_input.lower() == 'reset':
                agent.reset()
                print("\nAgent: Conversation reset. Let's start fresh!")
                print("       What date and time would work best for you?\n")
                continue

            elif user_input.lower() == 'analyze':
                print("\nAgent: Analyzing booking page structure...")
                print("       This will open a browser window and take a screenshot.\n")
                from agent.tools import AnalyzeBookingPageTool
                tool = AnalyzeBookingPageTool()
                result = tool._run(headless=False)
                print(f"\nAnalysis Result:\n{result}\n")
                continue

            # Process message through agent
            response = agent.process_message(user_input)
            print(f"\nAgent: {response}\n")

        except KeyboardInterrupt:
            print("\n\nAgent: Conversation interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please try again or type 'reset' to start over.\n")


def main():
    """Main function to run the booking agent."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Ixora Meeting Booking Agent - AI-powered meeting scheduler"
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode with simulated conversation'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='gemini-2.5-flash',
        help='Gemini model to use (default: gemini-2.5-flash)'
    )
    parser.add_argument(
        '--temperature',
        type=float,
        default=0.7,
        help='LLM temperature (default: 0.7)'
    )

    args = parser.parse_args()

    # Validate environment
    if not validate_env():
        sys.exit(1)

    try:
        # Initialize the LLM
        print(f"\n🚀 Initializing {args.model}...")
        llm = ChatGoogleGenerativeAI(
            model=args.model,
            temperature=args.temperature,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )

        # Create the booking agent
        print("🤖 Creating booking agent with LangGraph workflow...")
        agent = BookingAgent(llm)
        agent.initialize_state()

        print("✅ Agent ready!\n")

        # Run in appropriate mode
        if args.test:
            run_test_mode(agent)
        else:
            run_interactive_mode(agent)

    except Exception as e:
        print(f"\n❌ Failed to initialize agent: {str(e)}")
        print("\nPlease check your configuration and try again.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

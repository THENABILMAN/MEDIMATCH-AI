"""Interactive Terminal Chat CLI for MediMatch AI Symptom Assistant.

Allows testing the LangGraph conversational workflow, rule-based safety escalation,
follow-up questions, and doctor search criteria generation directly in the terminal.

Usage:
    python backend/scripts/chat_cli.py
"""

import os
import sys
import uuid
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.supabase import get_supabase_admin_client, get_supabase_client
from app.services.chat_service import (
    DISCLAIMER_MESSAGE,
    create_conversation,
    send_patient_message,
)


def run_cli():
    print("=" * 70)
    print(" 🩺  MediMatch AI — Interactive Symptom Assistant CLI  🤖")
    print("=" * 70)
    print("Type 'exit' or 'quit' at any prompt to end the session.\n")

    # Use seeded demo patient ID
    patient_id = "a0000000-0000-0000-0000-000000000002"
    patient_email = "patient@medimatch.test"

    print(f"[Connecting as Demo Patient: {patient_email}]")

    try:
        conv = create_conversation(patient_id=patient_id, title="CLI Consultation Session")
        conversation_id = conv["id"]
        print(f"[Session Initialized: {conversation_id}]\n")
    except Exception as e:
        print(f"[ERROR] Could not initialize conversation session: {e}")
        # Fallback to local session ID if DB connection fails
        conversation_id = str(uuid.uuid4())
        print(f"[Using Local Fallback Session: {conversation_id}]\n")

    print("🤖 Assistant:")
    print("-" * 50)
    print(DISCLAIMER_MESSAGE)
    print("-" * 50 + "\n")

    while True:
        try:
            user_input = input("👤 You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "q"]:
            print("\nThank you for using MediMatch AI. Goodbye!")
            break

        print("\nThinking...")
        try:
            result = send_patient_message(
                conversation_id=conversation_id,
                patient_id=patient_id,
                message_content=user_input,
            )

            assistant_reply = result["assistant_reply"]
            current_step = result["current_step"]
            search_criteria = result.get("search_criteria")

            print("\n🤖 Assistant:")
            print("-" * 50)
            print(assistant_reply)
            print("-" * 50)

            if search_criteria:
                print("\n📋 [Search Criteria Generated]")
                print(f"  • Candidate Specialties : {', '.join(search_criteria.get('candidate_specialties', []))}")
                print(f"  • Target City           : {search_criteria.get('city', 'Dhaka')}")
                if search_criteria.get('max_fee'):
                    print(f"  • Max Fee Filter        : {search_criteria.get('max_fee')} BDT")
                print(f"  • Extracted Keywords    : {', '.join(search_criteria.get('keywords', []))}")
                print("-" * 50)

            print(f"Status: {current_step}\n")

        except Exception as e:
            print(f"[Error processing message]: {e}\n")


if __name__ == "__main__":
    run_cli()


"""
Day 3 - Email Auto-Responder
Step 7: Main script - run this to process your unread inbox.

What it does each run:
  1. Fetch unread emails not yet labeled "AI-Processed"
  2. For each: extract content, classify + draft with Claude
  3. If the email warrants a reply: create a Gmail DRAFT (never sends)
  4. Label the email "AI-Processed" either way, so it's not re-processed next run

Usage:
  python email_autoresponder.py
  python email_autoresponder.py --max 20    (process up to 20 emails instead of default 10)

Requires:
  - token.json (from authenticate.py)
  - ANTHROPIC_API_KEY environment variable set
"""

import argparse
import os
import re

from dotenv import load_dotenv

from gmail_helper import (
    create_draft_reply,
    extract_email_content,
    fetch_unread_emails,
    get_gmail_service,
    label_as_processed,
)
from llm_classifier import classify_and_draft

load_dotenv()  # loads ANTHROPIC_API_KEY from a .env file if present


def _parse_sender_address(sender_header):
    """'From' header looks like 'Jane Doe <jane@example.com>' - we need just the address."""
    match = re.search(r"<(.+?)>", sender_header)
    return match.group(1) if match else sender_header


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=10, help="Max emails to process this run")
    args = parser.parse_args()

    if "ANTHROPIC_API_KEY" not in os.environ:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set. Put it in a .env file or export it in your shell."
        )

    service = get_gmail_service()
    messages, processed_label_id = fetch_unread_emails(service, max_results=args.max)

    if not messages:
        print("[INFO] No new unread emails to process.")
        return

    print(f"[INFO] Found {len(messages)} unread email(s) to process.")

    drafted_count = 0

    for msg_ref in messages:
        email = extract_email_content(service, msg_ref["id"])
        print(f"\n[PROCESSING] From: {email['sender']} | Subject: {email['subject']}")

        try:
            result = classify_and_draft(email)
        except Exception as e:
            print(f"  [ERROR] LLM classification failed: {e}")
            continue  # don't label as processed - we'll retry it next run

        print(f"  Category: {result['category']}  |  Draft reply: {result['should_draft_reply']}")
        print(f"  Reasoning: {result['reasoning']}")

        if result["should_draft_reply"]:
            to_address = _parse_sender_address(email["sender"])
            create_draft_reply(
                service,
                thread_id=email["thread_id"],
                to_address=to_address,
                subject=email["subject"],
                reply_body=result["reply_body"],
            )
            drafted_count += 1
            print(f"  [DRAFTED] Reply saved to Gmail Drafts for your review.")

        # Label as processed regardless of whether we drafted a reply -
        # a classified "no reply needed" is still a completed decision.
        label_as_processed(service, msg_ref["id"], processed_label_id)

    print(f"\n[DONE] Processed {len(messages)} email(s), drafted {drafted_count} repl(ies).")
    print("[REMINDER] Nothing was sent. Review drafts in Gmail before sending.")


if __name__ == "__main__":
    main()

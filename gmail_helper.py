"""
Day 3 - Email Auto-Responder
Step 5: Gmail helper functions.

These wrap the Gmail API's slightly awkward raw format into simple functions:
- get_gmail_service(): authenticate using the saved token
- fetch_unread_emails(): list unread messages not yet processed by us
- extract_email_content(): pull sender/subject/plain-text body out of raw MIME
- create_draft_reply(): save a reply as a DRAFT (never sends)
- label_as_processed(): mark an email so we don't draft a reply to it twice
"""

import base64
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
PROCESSED_LABEL = "AI-Processed"  # emails with this label are skipped next run


def get_gmail_service():
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def _get_or_create_label(service, label_name):
    """Gmail labels are how we track 'already handled this one' state."""
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"] == label_name:
            return label["id"]

    new_label = service.users().labels().create(
        userId="me",
        body={"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"},
    ).execute()
    return new_label["id"]


def fetch_unread_emails(service, max_results=10):
    """
    Only fetch emails that are UNREAD and do NOT already have our processed
    label. This is what makes the script safe to re-run repeatedly (e.g. via
    a scheduled task every 15 minutes) without drafting duplicate replies.
    """
    processed_label_id = _get_or_create_label(service, PROCESSED_LABEL)

    query = f"is:unread -label:{PROCESSED_LABEL}"
    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    return results.get("messages", []), processed_label_id


def extract_email_content(service, message_id):
    """Pulls sender, subject, and plain-text body from Gmail's raw format."""
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()

    headers = msg["payload"]["headers"]
    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(no subject)")
    sender = next((h["value"] for h in headers if h["name"] == "From"), "(unknown sender)")
    thread_id = msg["threadId"]

    body = _extract_plain_text(msg["payload"])

    return {
        "message_id": message_id,
        "thread_id": thread_id,
        "sender": sender,
        "subject": subject,
        "body": body,
    }


def _extract_plain_text(payload):
    """
    Emails can be multipart (HTML + plain text versions) or single-part.
    We specifically look for the plain-text part - trying to parse HTML
    directly would drag in tags and formatting noise that pollutes the
    LLM's input for no benefit.
    """
    if payload.get("mimeType") == "text/plain":
        data = payload["body"].get("data", "")
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain":
            data = part["body"].get("data", "")
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        # Recurse into nested multipart structures
        if part.get("parts"):
            result = _extract_plain_text(part)
            if result:
                return result

    return "(could not extract plain text body)"


def create_draft_reply(service, thread_id, to_address, subject, reply_body):
    """
    Creates a DRAFT reply in the same thread. This never sends anything -
    it shows up in the user's Gmail Drafts folder for manual review and send.
    """
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    message = MIMEText(reply_body)
    message["to"] = to_address
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    draft = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw, "threadId": thread_id}},
    ).execute()

    return draft


def label_as_processed(service, message_id, processed_label_id):
    """Tags an email so future runs skip it - prevents duplicate drafts."""
    service.users().messages().modify(
        userId="me", id=message_id, body={"addLabelIds": [processed_label_id]}
    ).execute()

"""
Day 3 - Email Auto-Responder
Step 6: LLM classification + reply drafting.

Given an email's sender/subject/body, ask Claude to:
1. Classify what kind of email this is
2. Decide whether it even warrants an auto-drafted reply
3. If yes, write a draft reply in a specific style

We request STRUCTURED JSON output specifically so the rest of the script
doesn't have to guess-parse free-form text.
"""

import json
import os

import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are an email triage assistant. Given an email, classify it and \
decide if it deserves an automatically drafted reply.

Categories: "meeting_request", "support_question", "sales_inquiry", "personal", \
"newsletter_or_promo", "spam_or_irrelevant", "other"

Only set should_draft_reply to true for: meeting_request, support_question, \
sales_inquiry, or personal emails that clearly expect a response from the recipient. \
Never draft replies for newsletters, promotions, automated notifications, or spam.

If should_draft_reply is true, write a brief, professional, friendly reply in the \
recipient's voice. Do NOT invent specific facts, dates, prices, or commitments you \
don't have information for - instead, acknowledge the request and say you'll follow \
up with specifics, or ask a clarifying question.

Respond ONLY with valid JSON, no other text, in this exact shape:
{
  "category": "...",
  "should_draft_reply": true/false,
  "reasoning": "one short sentence on why",
  "reply_body": "..." (empty string if should_draft_reply is false)
}"""


def classify_and_draft(email):
    user_message = f"""From: {email['sender']}
Subject: {email['subject']}

Body:
{email['body'][:3000]}"""
    # truncate very long bodies - classification doesn't need the whole email,
    # and it keeps token usage (and cost) predictable per email

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text.strip()

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        # LLMs occasionally wrap JSON in markdown fences despite instructions -
        # this is a pragmatic fallback, not a silent failure
        cleaned = raw_text.replace("```json", "").replace("```", "").strip()
        result = json.loads(cleaned)

    return result

# Day 3 — LLM-Powered Email Auto-Responder

## What this project does
Scans your unread Gmail inbox, classifies each email (meeting request, support
question, sales inquiry, personal, newsletter, spam, etc.), and — only for emails
that genuinely warrant a response — drafts a reply using Claude and saves it to
your **Gmail Drafts folder for you to review and send manually.**

**It never sends anything automatically.** This is a deliberate design choice, not
a limitation: fully autonomous email sending is exactly the kind of automation
that goes wrong in hard-to-undo ways. A human-approval step is standard practice
here.

## Setup

### 1. Enable Gmail API access (one-time, console only)
1. [console.cloud.google.com](https://console.cloud.google.com) → new project
2. APIs & Services → Library → search "Gmail API" → **Enable**
3. APIs & Services → OAuth consent screen → **External** → add your Gmail as a test user
4. APIs & Services → Credentials → **Create Credentials → OAuth client ID** → Application type: **Desktop app**
5. Download the JSON, rename it `credentials.json`, place it in this folder

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your Anthropic API key
Create a `.env` file in this folder:
```
ANTHROPIC_API_KEY=your_key_here
```
(Get a key from [console.anthropic.com](https://console.anthropic.com))

### 4. Authenticate with Gmail (one-time)
```bash
python authenticate.py
```
This opens your browser once for login/consent, then saves `token.json` for future runs.

### 5. Run it
```bash
python email_autoresponder.py
```
Optional: `--max 20` to process more than the default 10 emails per run.

Check your Gmail **Drafts** folder afterward — every drafted reply is waiting there for your review.

## How it avoids duplicate work
Every processed email gets an `AI-Processed` Gmail label. Each run only looks at
emails that are unread **and** don't already have that label — so you can safely
re-run this on a schedule (cron, Task Scheduler, etc.) without it drafting the
same reply twice.

## Architecture
```
authenticate.py        - one-time OAuth login, saves token.json
gmail_helper.py         - Gmail API wrappers (fetch, parse MIME, create draft, label)
llm_classifier.py       - Claude API call: classify email + draft reply as structured JSON
email_autoresponder.py  - main script that ties it all together
```

## Design decisions worth mentioning in your post
- **Structured JSON output from the LLM**, not free-form text — makes the rest of
  the pipeline reliable instead of guess-parsing prose.
- **A `should_draft_reply` flag decided by the LLM itself** — not every unread
  email deserves a drafted reply (newsletters, notifications, spam shouldn't get one).
- **Draft, never send** — the actual safety boundary is in the code (it never
  calls Gmail's send endpoint), not just the OAuth scope, which is worth being
  precise about rather than overclaiming.
- **Gmail labels as a dedup mechanism** — a small but real distributed-systems-style
  problem (idempotency) that's easy to overlook in a first draft of this kind of script.

## Suggested LinkedIn post draft
```
🚀 Day 3/30 of my AI Build Challenge

Built: An email auto-responder that reads unread Gmail, classifies intent, and
drafts context-aware replies — using Claude.

Problem it solves: cuts the "read email, figure out what it needs, write a reply"
loop down to "read + approve."

Stack: Gmail API (OAuth), Claude API, Python

Hardest part: making sure the LLM doesn't try to draft a reply to *everything* —
had to explicitly ask it to decide first whether an email even deserves one, and
skip newsletters/spam/notifications.

Design choice I'm sticking to: it only ever creates DRAFTS, never sends. Full
autonomy here felt like the wrong call — a human should always be the one hitting
send on their own inbox.

Demo: [screen recording of a draft appearing in Gmail]
Code: [GitHub link]

#Day3of30 #AIAutomation #LLM #Python #BuildInPublic
```

## Known limitations (worth being upfront about)
- Only extracts plain-text email bodies — image-only or unusually formatted
  emails may not parse cleanly.
- Classification quality depends on the LLM prompt; edge cases (e.g. an email
  that's both a newsletter AND asks a direct question) may be misclassified.
- No handling for emails in languages other than what the model naturally supports.

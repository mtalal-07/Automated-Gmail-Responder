"""
Day 3 - Email Auto-Responder
Step 4: One-time authentication.

Run this ONCE. It opens your browser, asks you to log in and approve access,
then saves a token.json file so future runs don't need to re-authenticate.

Usage:
  python authenticate.py
"""

from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes define what this token is ALLOWED to do at the API level.
# gmail.modify covers read + create drafts + apply labels (and, technically,
# sending too - Google doesn't offer a scope that permits drafts but
# categorically forbids sending). The real safety guarantee in this project
# isn't the scope - it's that our code (email_autoresponder.py) simply never
# calls the send endpoint, and every reply sits as a draft for YOU to review
# and send manually in Gmail. Be honest with yourself about this distinction:
# a scope is a permission ceiling, not a behavioral promise.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def main():
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)

    with open("token.json", "w") as f:
        f.write(creds.to_json())

    print("[INFO] Authentication successful. Saved token.json")
    print("[INFO] You can now run email_autoresponder.py")


if __name__ == "__main__":
    main()

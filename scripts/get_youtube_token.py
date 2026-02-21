"""
One-time helper: obtain a YouTube (Google OAuth) refresh token.

Run this script once locally to authorize the app against your Google account.
It opens a browser, you log in, and the script prints the refresh token to copy
into your .env file (or GitHub Secrets).

Usage:
    python scripts/get_youtube_token.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv(Path(__file__).parent.parent / ".env")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> None:
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("ERROR: YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET must be set in .env")
        raise SystemExit(1)

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)

    print("Opening browser for Google / YouTube authorization…")
    credentials = flow.run_local_server(port=0)

    refresh_token = credentials.refresh_token
    if not refresh_token:
        print("ERROR: No refresh token returned.")
        raise SystemExit(1)

    print("\n" + "=" * 60)
    print("SUCCESS — copy this value into your .env / GitHub Secrets:")
    print(f"\nYOUTUBE_REFRESH_TOKEN={refresh_token}\n")
    print("=" * 60)


if __name__ == "__main__":
    main()

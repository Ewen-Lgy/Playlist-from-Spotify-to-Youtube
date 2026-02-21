# -*- coding: utf-8 -*-
"""
One-time helper: obtain a Spotify refresh token.

Run this script once locally to authorize the app against your Spotify account.
It opens a browser, you log in, and the script prints the refresh token to copy
into your .env file (or GitHub Secrets).

Usage:
    python scripts/get_spotify_token.py
"""

import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv(Path(__file__).parent.parent / ".env")

SCOPES = " ".join([
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-private",
    "playlist-modify-public",
])


def main() -> None:
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/callback")

    if not client_id or not client_secret:
        print("ERROR: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env")
        raise SystemExit(1)

    print(f"  Client ID    : {client_id[:8]}...")
    print(f"  Redirect URI : {redirect_uri}")
    print()
    print("Make sure this EXACT URI is saved in your Spotify Dashboard:")
    print(f"  https://developer.spotify.com/dashboard -> Edit Settings -> Redirect URIs")
    print()

    # open_browser=True: spotipy starts a local HTTP server on the port from
    # redirect_uri (8000), opens the browser, and captures the code automatically.
    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPES,
        open_browser=True,
        cache_path=None,
    )

    print("Opening browser for Spotify authorization...")
    token_info = auth_manager.get_access_token(as_dict=True)

    refresh_token = token_info.get("refresh_token")
    if not refresh_token:
        print("ERROR: No refresh token returned.")
        raise SystemExit(1)

    print()
    print("=" * 60)
    print("SUCCESS - copy this into your .env / GitHub Secrets:")
    print()
    print(f"SPOTIFY_REFRESH_TOKEN={refresh_token}")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()

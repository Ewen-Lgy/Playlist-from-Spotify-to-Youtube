"""
Spotify API client.

Handles authentication (refresh-token flow, safe for CI) and
exposes the playlist operations needed by the pipeline:
  - list all user playlists
  - filter those tagged [YOUTUBE]
  - fetch track details
  - rename a playlist (e.g. [YOUTUBE] → [DONE])
"""

import os
import logging
from dataclasses import dataclass

import spotipy
from spotipy.oauth2 import SpotifyOAuth

logger = logging.getLogger(__name__)

YOUTUBE_TAG = "[YOUTUBE]"
DONE_TAG = "[DONE]"

REQUIRED_SCOPES = " ".join([
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-private",
    "playlist-modify-public",
])


@dataclass
class Track:
    title: str
    artist: str
    duration_ms: int


@dataclass
class Playlist:
    id: str
    name: str
    tracks: list[Track]
    cover_url: str = ""


def _build_spotify_client() -> spotipy.Spotify:
    """
    Build an authenticated Spotify client using the refresh token stored in
    the environment.  No browser / interactive flow — safe for headless CI.
    """
    client_id = os.environ["SPOTIFY_CLIENT_ID"]
    client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]
    redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
    refresh_token = os.environ["SPOTIFY_REFRESH_TOKEN"]

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=REQUIRED_SCOPES,
    )
    # Inject the stored refresh token so no browser prompt is needed.
    token_info = auth_manager.refresh_access_token(refresh_token)
    return spotipy.Spotify(auth=token_info["access_token"], requests_timeout=10, retries=0)


def get_tagged_playlists() -> list[Playlist]:
    """
    Return all playlists whose name contains [YOUTUBE], including their tracks.
    """
    sp = _build_spotify_client()

    tagged: list[Playlist] = []
    offset = 0
    limit = 50

    logger.info("Scanning Spotify playlists for tag '%s'…", YOUTUBE_TAG)

    while True:
        logger.info("  Fetching playlists at offset %d…", offset)
        user = sp.current_user()
        logger.info("  Current user: %s", user['display_name'])
        response = sp.current_user_playlists(limit=limit, offset=offset)
        items = response.get("items", [])
        if not items:
            break

        logger.info("  Scanning playlists %d–%d…", offset + 1, offset + len(items))

        for item in items:
            name: str = item["name"]
            if YOUTUBE_TAG in name:
                playlist_id: str = item["id"]
                logger.info("  Found tagged playlist: %s (id=%s)", name, playlist_id)
                tracks = _fetch_tracks(sp, playlist_id)
                images = item.get("images", [])
                cover_url = images[0]["url"] if images else ""
                tagged.append(Playlist(id=playlist_id, name=name, tracks=tracks, cover_url=cover_url))

        if response["next"] is None:
            break
        offset += limit

    logger.info("Found %d tagged playlist(s).", len(tagged))
    return tagged


def _fetch_tracks(sp: spotipy.Spotify, playlist_id: str) -> list[Track]:
    """Fetch all tracks for a given playlist id."""
    tracks: list[Track] = []
    offset = 0
    limit = 100

    while True:
        response = sp._get(
            f"playlists/{playlist_id}/items",
            limit=limit,
            offset=offset,
            additional_types="track",
        )
        items = response.get("items", [])
        if not items:
            break

        for item in items:
            track_data = item.get("item")
            if not track_data or track_data.get("type") != "track" or not track_data.get("name"):
                continue
            artist = ", ".join(a["name"] for a in track_data.get("artists", []))
            tracks.append(Track(
                title=track_data["name"],
                artist=artist,
                duration_ms=track_data.get("duration_ms", 0),
            ))

        if response.get("next") is None:
            break
        offset += limit

    return tracks


def mark_playlist_done(playlist_id: str, current_name: str) -> None:
    """
    Replace [YOUTUBE] with [DONE] in the playlist name so the pipeline
    won't process it again on the next run.
    """
    sp = _build_spotify_client()
    new_name = current_name.replace(YOUTUBE_TAG, DONE_TAG)
    sp.playlist_change_details(playlist_id, name=new_name)
    logger.info("Renamed playlist '%s' → '%s'", current_name, new_name)

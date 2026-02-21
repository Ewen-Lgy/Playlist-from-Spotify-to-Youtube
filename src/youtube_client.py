"""
YouTube Data API v3 client.

Handles OAuth (refresh-token flow, safe for CI) and video upload.

The upload uses a resumable upload so large files are handled reliably.
Progress is logged every 10 %.
"""

import logging
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from .spotify_client import Playlist

logger = logging.getLogger(__name__)

YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB


def _build_youtube_client():
    """Return an authenticated YouTube service object."""
    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=[YOUTUBE_UPLOAD_SCOPE],
    )
    # Refresh immediately to obtain a valid access token.
    credentials.refresh(Request())
    return build("youtube", "v3", credentials=credentials)


def upload_video(video_path: Path, playlist: Playlist) -> str:
    """
    Upload *video_path* to YouTube with metadata derived from *playlist*.
    Returns the YouTube video ID.
    """
    privacy = os.environ.get("YOUTUBE_PRIVACY_STATUS", "unlisted")

    clean_name = (
        playlist.name
        .replace("[YOUTUBE]", "")
        .replace("[DONE]", "")
        .strip()
    )
    track_lines = "\n".join(
        f"{i + 1}. {t.artist} – {t.title}"
        for i, t in enumerate(playlist.tracks)
    )
    description = (
        f"Playlist: {clean_name}\n\n"
        f"Tracklist:\n{track_lines}\n\n"
        f"Auto-generated from Spotify playlist."
    )

    body = {
        "snippet": {
            "title": clean_name,
            "description": description,
            "tags": ["playlist", "music", clean_name],
            "categoryId": "10",  # Music
        },
        "status": {
            "privacyStatus": privacy,
        },
    }

    youtube = _build_youtube_client()
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        chunksize=CHUNK_SIZE,
        resumable=True,
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    logger.info("Uploading '%s' to YouTube (%s)…", clean_name, privacy)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            if pct % 10 == 0:
                logger.info("  Upload progress: %d %%", pct)

    video_id = response["id"]
    logger.info("Upload complete. Video ID: %s", video_id)
    return video_id

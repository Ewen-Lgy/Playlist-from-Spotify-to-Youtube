"""
Audio downloader.

Uses yt-dlp to search YouTube Music for each track and download it as
an MP3 into the given work directory.

Returns a list of (track, local_audio_path) pairs, skipping any track
that could not be downloaded.
"""

import logging
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import yt_dlp

from .spotify_client import Track

logger = logging.getLogger(__name__)


@dataclass
class DownloadedTrack:
    track: Track
    audio_path: Path


def download_tracks(tracks: list[Track], work_dir: Path) -> list[DownloadedTrack]:
    """
    Download audio for every track in *tracks*.
    Skips (with a warning) any track that fails to download.
    Returns only successfully downloaded tracks, in order.
    """
    results: list[DownloadedTrack] = []

    for track in tracks:
        try:
            path = _download_single(track, work_dir)
            results.append(DownloadedTrack(track=track, audio_path=path))
        except Exception as exc:
            logger.warning(
                "Could not download '%s – %s': %s", track.artist, track.title, exc
            )

    return results


def _download_single(track: Track, work_dir: Path) -> Path:
    query = f"{track.artist} - {track.title}"
    safe = _safe_filename(query)
    output_path = work_dir / f"{safe}.mp3"

    if output_path.exists():
        logger.info("  Audio already downloaded, reusing: %s", output_path.name)
        return output_path

    logger.info("  Downloading: %s", query)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(work_dir / f"{safe}.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "default_search": "ytmsearch1",  # YouTube Music natif
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "android"],
                "skip": ["dash", "hls"],  # évite certaines erreurs de format
            }
        },
        "retries": 3,
        "fragment_retries": 3,
        "ignoreerrors": True,
    }

    cookies_file = os.environ.get("YOUTUBE_COOKIES_FILE")
    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"ytsearch1:{query}"])

    if not output_path.exists():
        raise FileNotFoundError(f"Expected output file not found: {output_path}")

    return output_path


def _safe_filename(name: str) -> str:
    """Strip characters that are unsafe in file names."""
    return re.sub(r'[\\/*?:"<>|\'`]', "_", name)[:180]

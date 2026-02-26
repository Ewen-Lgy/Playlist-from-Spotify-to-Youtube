"""
Main pipeline orchestrator.

For each Spotify playlist tagged [YOUTUBE]:
  1. Generate a background image (DALL·E or Unsplash fallback).
  2. Download audio for each track via yt-dlp.
  3. Assemble image + audio into an .mp4 with FFmpeg.
  4. Upload the .mp4 to YouTube.
  5. Rename the Spotify playlist [YOUTUBE] → [DONE].
"""

import logging
import os
import shutil
from pathlib import Path

from .spotify_client import Playlist, get_tagged_playlists, mark_playlist_done
from .image_generator import generate_thumbnail
from .audio_downloader import download_tracks
from .video_assembler import assemble_video
from .youtube_client import upload_video

logger = logging.getLogger(__name__)


def run() -> None:
    """Entry point for the full pipeline."""
    work_base = Path(os.environ.get("WORK_DIR", "./tmp"))
    output_dir = Path(os.environ.get("OUTPUT_DIR", "./output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    playlists = get_tagged_playlists()

    if not playlists:
        logger.info("No playlists with '%s' tag found. Nothing to do.", "[YOUTUBE]")
        return

    for playlist in playlists:
        _process_playlist(playlist, work_base, output_dir)


def _process_playlist(playlist: Playlist, work_base: Path, output_dir: Path) -> None:
    safe_name = "".join(
        c if c.isalnum() or c in " _-" else "_" for c in playlist.name
    ).strip()
    work_dir = work_base / safe_name
    work_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("Processing playlist: %s (%d tracks)", playlist.name, len(playlist.tracks))

    try:
        # Step 1 — thumbnail
        thumbnail_path = generate_thumbnail(playlist.name, work_dir, playlist.cover_url)

        # Step 2 — audio download
        downloaded = download_tracks(playlist.tracks, work_dir)
        if not downloaded:
            logger.error(
                "No tracks could be downloaded for '%s'. Skipping.", playlist.name
            )
            return

        logger.info(
            "Downloaded %d / %d tracks.", len(downloaded), len(playlist.tracks)
        )

        # Step 3 — video assembly
        video_path = output_dir / f"{safe_name}.mp4"
        print(video_path)
        assemble_video(downloaded, thumbnail_path, video_path)

        # Step 4 — YouTube upload
        video_id = upload_video(video_path, playlist)
        logger.info("YouTube video published: https://youtu.be/%s", video_id)

        # Step 5 — mark playlist as done
        mark_playlist_done(playlist.id, playlist.name)

    except Exception as exc:
        logger.exception(
            "Pipeline failed for playlist '%s': %s", playlist.name, exc
        )
        # Do NOT mark as done — will be retried on the next run.
        return
    finally:
        # Clean up per-playlist working files to save disk space.
        shutil.rmtree(work_dir, ignore_errors=True)

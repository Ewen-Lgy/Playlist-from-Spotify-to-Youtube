"""
Thumbnail downloader.

Downloads the Spotify playlist cover image.
Falls back to a local default image if the cover is unavailable.
"""

import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

FALLBACK_IMAGE = Path(__file__).parent.parent / "assets" / "default_thumbnail.jpg"


def generate_thumbnail(playlist_name: str, work_dir: Path, cover_url: str = "") -> Path:
    """
    Download the Spotify cover image for *playlist_name* and save it under *work_dir*.
    Falls back to assets/default_thumbnail.jpg if unavailable.
    Returns the path to the saved image file.
    """
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in playlist_name)
    output_path = work_dir / f"thumbnail_{safe_name}.jpg"

    if output_path.exists():
        logger.info("Thumbnail already exists, reusing: %s", output_path)
        return output_path

    if cover_url:
        try:
            resp = requests.get(cover_url, timeout=30)
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
            logger.info("Spotify cover downloaded: %s", output_path)
            return output_path
        except Exception as exc:
            logger.warning("Could not download Spotify cover (%s), using fallback.", exc)

    logger.info("Using fallback thumbnail: %s", FALLBACK_IMAGE)
    return FALLBACK_IMAGE

"""
Thumbnail / background image generator.

Strategy:
  1. Try DALL·E 3 (OpenAI) — generates a custom image for the playlist name.
  2. Fallback to Unsplash — searches for a relevant photo.
  3. Last resort — create a plain dark gradient with Pillow.

Returns the local path of the saved image.
"""

import os
import logging
from pathlib import Path

import requests
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


def generate_thumbnail(playlist_name: str, work_dir: Path) -> Path:
    """
    Generate a thumbnail image for *playlist_name* and save it under *work_dir*.
    Returns the path to the saved image file.
    """
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in playlist_name)
    output_path = work_dir / f"thumbnail_{safe_name}.png"

    if output_path.exists():
        logger.info("Thumbnail already exists, reusing: %s", output_path)
        return output_path

    # 1. DALL·E
    try:
        return _generate_dalle(playlist_name, output_path)
    except Exception as exc:
        logger.warning("DALL·E generation failed (%s), trying Unsplash…", exc)

    # 2. Unsplash
    try:
        return _fetch_unsplash(playlist_name, output_path)
    except Exception as exc:
        logger.warning("Unsplash fetch failed (%s), using fallback image.", exc)

    # 3. Pillow fallback
    return "./assets/default_thumbnail.jpg"


# ---------------------------------------------------------------------------
# DALL·E
# ---------------------------------------------------------------------------

def _generate_dalle(playlist_name: str, output_path: Path) -> Path:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    prompt = (
        f"A visually stunning, cinematic music playlist cover art for a playlist called "
        f'"{playlist_name}". Abstract, vibrant colors, no text, suitable as a YouTube '
        f"video background. High quality, 16:9 aspect ratio feel."
    )
    logger.info("Generating DALL·E image for playlist '%s'…", playlist_name)

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1792x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url
    _download_image(image_url, output_path)
    logger.info("DALL·E image saved to %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# Unsplash
# ---------------------------------------------------------------------------

def _fetch_unsplash(playlist_name: str, output_path: Path) -> Path:
    access_key = os.environ["UNSPLASH_ACCESS_KEY"]
    query = playlist_name.replace("[YOUTUBE]", "").replace("[DONE]", "").strip()

    logger.info("Fetching Unsplash image for query '%s'…", query)
    resp = requests.get(
        "https://api.unsplash.com/photos/random",
        params={"query": query, "orientation": "landscape"},
        headers={"Authorization": f"Client-ID {access_key}"},
        timeout=15,
    )
    resp.raise_for_status()
    image_url = resp.json()["urls"]["full"]
    _download_image(image_url, output_path)
    logger.info("Unsplash image saved to %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# Pillow fallback
# ---------------------------------------------------------------------------

def _generate_fallback(playlist_name: str, output_path: Path) -> Path:
    width, height = 1920, 1080
    logger.info("Generating fallback gradient image for '%s'…", playlist_name)

    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # Simple top-to-bottom gradient: dark blue → dark purple
    for y in range(height):
        ratio = y / height
        r = int(10 + ratio * 30)
        g = int(10 + ratio * 5)
        b = int(60 + ratio * 40)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Overlay playlist name
    try:
        font = ImageFont.truetype("arial.ttf", size=72)
    except IOError:
        font = ImageFont.load_default()

    clean_name = playlist_name.replace("[YOUTUBE]", "").replace("[DONE]", "").strip()
    bbox = draw.textbbox((0, 0), clean_name, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(
        ((width - text_w) // 2, (height - text_h) // 2),
        clean_name,
        fill=(255, 255, 255),
        font=font,
    )

    img.save(output_path, "PNG")
    logger.info("Fallback image saved to %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _download_image(url: str, dest: Path) -> None:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)

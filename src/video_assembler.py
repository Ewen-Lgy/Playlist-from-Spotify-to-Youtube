"""
Video assembler.

Combines a static background image with audio tracks (one per song) into a
single .mp4 file using FFmpeg.

The video layout:
  - Fixed background image for the entire duration.
  - Audio = all downloaded tracks concatenated in playlist order.
  - Resolution: VIDEO_WIDTH x VIDEO_HEIGHT (env vars, default 1920x1080).
"""

import logging
import os
import subprocess
import tempfile
from pathlib import Path

from .audio_downloader import DownloadedTrack

logger = logging.getLogger(__name__)


def assemble_video(
    downloaded_tracks: list[DownloadedTrack],
    thumbnail_path: Path,
    output_path: Path,
) -> Path:
    """
    Build a .mp4 at *output_path* from a list of audio files and a background image.
    Returns *output_path* on success.
    """
    if not downloaded_tracks:
        raise ValueError("No downloaded tracks to assemble.")

    width = int(os.environ.get("VIDEO_WIDTH", 1920))
    height = int(os.environ.get("VIDEO_HEIGHT", 1080))

    audio_paths = [dt.audio_path for dt in downloaded_tracks]
    print(audio_paths)

    # Write a concat list file for FFmpeg
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        print(f.name)
        concat_file = Path(f.name)
        for p in audio_paths:
            # FFmpeg concat demuxer requires absolute, escaped paths
            escaped = str(Path(p).resolve()).replace("\\", "/").replace("'", "\\'")
            f.write(f"file '{escaped}'\n")

    try:
        _run_ffmpeg(thumbnail_path, concat_file, output_path, width, height)
    finally:
        concat_file.unlink(missing_ok=True)

    logger.info("Video assembled: %s", output_path)
    return output_path


def _run_ffmpeg(
    image_path: Path,
    concat_file: Path,
    output_path: Path,
    width: int,
    height: int,
) -> None:
    """
    Invoke FFmpeg to produce the final video.

    FFmpeg command breakdown:
      -loop 1 -i <image>          → loop the still image
      -f concat -i <concat_file>  → concatenated audio stream
      -vf scale=W:H               → scale image to target resolution
      -c:v libx264 -tune stillimage → encode with H.264 optimised for stills
      -c:a aac -b:a 192k          → encode audio as AAC
      -shortest                   → stop when the audio ends
      -movflags +faststart        → optimise for streaming
    """
    cmd = [
        "ffmpeg",
        "-y",                          # overwrite output without asking
        "-loop", "1",
        "-i", str(image_path),
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-vf", f"scale={width}:{height}",
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]

    logger.debug("FFmpeg command: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed (exit {result.returncode}):\n{result.stderr}"
        )

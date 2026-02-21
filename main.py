"""
Entry point — Spotify → YouTube pipeline.

Usage:
    python main.py

All configuration is read from environment variables (see .env.example).
For local development, copy .env.example to .env and fill in the values.
"""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env file when running locally (no-op in CI where secrets are env vars).
load_dotenv(Path(__file__).parent / ".env")

from src.pipeline import run  # noqa: E402 — import after dotenv load


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


if __name__ == "__main__":
    _configure_logging()
    run()

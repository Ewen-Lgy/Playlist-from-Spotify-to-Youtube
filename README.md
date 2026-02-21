# Playlist from Spotify to YouTube

Automatically converts your Spotify playlists into YouTube videos.

Tag any playlist with `[YOUTUBE]` in its name → the pipeline generates a
background image, downloads the audio, assembles an MP4, uploads it to your
YouTube channel, and renames the playlist to `[DONE]`.

Runs daily via GitHub Actions (or manually on demand).

---

## How it works

```
[YOUTUBE] playlist detected
        │
        ▼
  Generate thumbnail (DALL·E 3 → Unsplash → Pillow fallback)
        │
        ▼
  Download audio tracks (yt-dlp → YouTube Music)
        │
        ▼
  Assemble video (FFmpeg: still image + concatenated audio)
        │
        ▼
  Upload to YouTube (Data API v3, resumable upload)
        │
        ▼
  Rename Spotify playlist [YOUTUBE] → [DONE]
```

---

## Prerequisites

- Python 3.12+
- [FFmpeg](https://ffmpeg.org/download.html) installed and on your `PATH`
- Accounts / apps for: Spotify, Google (YouTube), OpenAI, Unsplash

---

## Local setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/<you>/Playlist-from-Spotify-to-Youtube.git
cd Playlist-from-Spotify-to-Youtube
pip install -r requirements.txt
```

### 2. Copy the environment template

```bash
cp .env.example .env
```

Then open `.env` and fill in each value as described below.

---

## Getting credentials

### Spotify

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and create an app.
2. Add `http://localhost:8888/callback` as a **Redirect URI** in the app settings.
3. Copy **Client ID** and **Client Secret** into `.env`.
4. Run the one-time authorization helper to get your refresh token:

```bash
python scripts/get_spotify_token.py
```

A browser window opens, you log in, and the script prints your
`SPOTIFY_REFRESH_TOKEN`. Copy it into `.env`.

### YouTube (Google OAuth)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project, then enable the **YouTube Data API v3**.
3. Create **OAuth 2.0 credentials** (type: Desktop app).
4. Download the JSON — copy `client_id` and `client_secret` into `.env`.
5. Run the one-time authorization helper:

```bash
python scripts/get_youtube_token.py
```

A browser window opens, you authorize access, and the script prints your
`YOUTUBE_REFRESH_TOKEN`. Copy it into `.env`.

### OpenAI

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
2. Create a key and paste it as `OPENAI_API_KEY` in `.env`.

> The pipeline uses DALL·E 3 for thumbnail generation. If this key is absent
> or the quota is exceeded, it falls back to Unsplash automatically.

### Unsplash

1. Go to [unsplash.com/developers](https://unsplash.com/developers) and create an app.
2. Copy the **Access Key** as `UNSPLASH_ACCESS_KEY` in `.env`.

---

## Running locally

```bash
python main.py
```

The script will:
- Scan all your Spotify playlists for `[YOUTUBE]`
- Process each one through the full pipeline
- Write temporary files to `./tmp/` and finished videos to `./output/`
  (both are gitignored)

---

## GitHub Actions — automated daily run

### 1. Push the repository to GitHub

### 2. Add secrets

Go to **Settings → Secrets and variables → Actions** and add one secret per
variable listed in `.env.example`:

| Secret | Where to find it |
|---|---|
| `SPOTIFY_CLIENT_ID` | Spotify Dashboard |
| `SPOTIFY_CLIENT_SECRET` | Spotify Dashboard |
| `SPOTIFY_REDIRECT_URI` | `http://localhost:8888/callback` |
| `SPOTIFY_REFRESH_TOKEN` | Output of `scripts/get_spotify_token.py` |
| `YOUTUBE_CLIENT_ID` | Google Cloud Console |
| `YOUTUBE_CLIENT_SECRET` | Google Cloud Console |
| `YOUTUBE_REFRESH_TOKEN` | Output of `scripts/get_youtube_token.py` |
| `OPENAI_API_KEY` | platform.openai.com |
| `UNSPLASH_ACCESS_KEY` | unsplash.com/developers |

### 3. The workflow runs automatically

The workflow (`.github/workflows/daily_sync.yml`) triggers every day at
**07:00 UTC**. You can also trigger it manually from the **Actions** tab →
**Spotify → YouTube daily sync** → **Run workflow**.

---

## Project structure

```
.
├── .env.example                   # All required env vars (no values)
├── .github/
│   └── workflows/
│       └── daily_sync.yml         # GitHub Actions cron job
├── main.py                        # Entry point
├── requirements.txt
├── scripts/
│   ├── get_spotify_token.py       # One-time Spotify OAuth helper
│   └── get_youtube_token.py       # One-time YouTube OAuth helper
└── src/
    ├── audio_downloader.py        # yt-dlp audio download
    ├── image_generator.py         # DALL·E / Unsplash / Pillow thumbnail
    ├── pipeline.py                # Orchestrates all steps
    ├── spotify_client.py          # Spotify API (playlist detection & rename)
    ├── video_assembler.py         # FFmpeg video assembly
    └── youtube_client.py          # YouTube Data API v3 upload
```

---

## Security

- **No credentials are ever committed.** All secrets live in `.env` locally
  and in GitHub Secrets for CI.
- `.env` is listed in `.gitignore`.
- The `token.json` OAuth cache (if ever written) is also gitignored.

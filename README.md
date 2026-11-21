# Smart Reflection

Smart Reflection is a desktop smart-mirror dashboard built with Python and PySide6. It combines time, calendar, weather, news, stocks, music, voice control, Gemini AI, and camera-based makeup suggestions in a modern glass-style interface.

## Features

- Live clock and calendar
- Local music playback and voice controls
- Gemini conversational assistant
- OpenWeather weather updates
- News headlines and market quotes
- Face analysis and makeup suggestions
- Text-to-speech feedback
- Optional Spotify integration

## Requirements

- Windows 10/11 (primary target)
- Python 3.10 or newer
- A webcam and microphone
- API keys for the integrations you enable

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python main.py
```

Add your keys to `.env`:

```dotenv
GEMINI_API_KEY=...
OPENWEATHER_API_KEY=...
ALPHA_VANTAGE_API_KEY=...
NEWS_API_KEY=...
```

Never commit `.env` or real API credentials. The application requires these values only when their corresponding widgets are enabled.

## Spotify (optional)

Spotify Premium may be required for playback control. Add the optional values to `.env` and instantiate `SpotifyWidget` in `main.py` with `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, and `SPOTIFY_REDIRECT_URI`.

Register `http://127.0.0.1:8888/callback` as a redirect URI in the Spotify developer dashboard.

## DevOps

### Continuous Integration

GitHub Actions validates every push and pull request with:

- Python 3.11 setup
- Dependency installation
- `compileall` source validation
- Unittest discovery

The workflow is located at [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

### Containerization

A Linux container definition is included for reproducible dependency setup:

```bash
docker compose build
docker compose up
```

The desktop GUI requires a running X11 display server. On Linux:

```bash
xhost +local:
docker compose up
```

Native Windows execution is recommended because the application uses a webcam, microphone, Windows-friendly audio playback, and Qt desktop widgets.

### Local validation

```powershell
python -m compileall -q .
python -m unittest discover -s . -p "test*.py" -v
docker compose build
```

# Kitten-TTS API

Lightweight, stateless API for KittenTTS text-to-speech synthesis with immediate file download.

**Original project:** https://github.com/KittenML/KittenTTS

## Features

- **Instant Downloads** – Synthesize and download audio in a single request
- **Lightweight** – Tiny lightweight models that runs on CPU without GPU
- **8 Built-in Voices** – Bella, Jasper, Luna, Bruno, Rosie, Hugo, Kiki, Leo
- **Speed Control** – Adjustable playback speed (0.5x–2.0x)
- **Structured Logging** – Consistent format with request tracing
- **Simple & Stateless** – No database, no request tracking

## Prerequisites

- Docker or Podman installed
- Git

## Quickstart — Using the Helper Script

> [!IMPORTANT]
> By default the script will use Docker, then Podman

**Force Docker:**
```sh
cat setup | python3 --use docker
```

**Force Podman** (adds SELinux `:Z` volume label):
```sh
cat setup | python3 --use podman
```

The script:
- Builds an image named `myapp` from an embedded Dockerfile
- Mounts `./` and `.cache` into the container
- Exposes port 8000 and starts uvicorn

## API Endpoints

**Base URL:** `http://HOST:PORT`

### POST /generate
**Synthesize text to speech and download audio immediately.**

**Request:**
```json
{
  "text": "Hello world",
  "voice": "Jasper"
}
```

**Parameters:**
- `text` (string, required): Input text (1–1500 characters)
- `voice` (string, optional): Voice name. Default: `"Jasper"`
  - Available: `Bella`, `Jasper`, `Luna`, `Bruno`, `Rosie`, `Hugo`, `Kiki`, `Leo`

**Response:**
- HTTP 200 – WAV file streamed as download (`audio_<request_id>.wav`)
- HTTP 500 – Synthesis failed (check logs for details)

### DELETE /cleanup
**Delete all generated audio files from the output folder.**

**Response:**
```json
{
  "message": "Cleaned up 5 files",
  "count": 5
}
```

### GET /health
**Health check endpoint.**

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

## Examples

### Synthesize and Save
```sh
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world","voice":"Jasper"}' \
  -o output.wav
```

### Python Client
```python
import requests

response = requests.post(
    "http://localhost:8000/generate",
    json={
        "text": "This is a test of Kitten TTS",
        "voice": "Luna"
    }
)

with open("output.wav", "wb") as f:
    f.write(response.content)
```

### Cleanup
```sh
curl -X DELETE http://localhost:8000/cleanup
```

## Configuration

Edit `api.py` to customize:

- **Output folder:** Change `OUTPUT_FOLDER` path (default: `/tmp/kitten_tts_output`)
- **Model:** Change model ID in `KittenTTS()` initialization (default: `KittenML/kitten-tts-mini-0.8`)
  - Available models: `kitten-tts-nano-0.8`, `kitten-tts-micro-0.8`, `kitten-tts-mini-0.8`
- **Port/Host:** Modify uvicorn config in `if __name__ == "__main__"` block


## Architecture

- **No Database** – Stateless API (no SQLite or request tracking)
- **Immediate Processing** – Synthesis happens synchronously, returns file directly
- **Auto-cleanup** – Use `DELETE /cleanup` to free disk space
- **Automatic Model Download** – First run downloads model from Hugging Face (~80MB)

## Notes

- `.cache` maps to `/root/.cache` (model cache); podman uses `:Z` SELinux label
- Files saved to `/tmp/kitten_tts_output` by default (configurable)
- Ensure sufficient disk space for output files
- Each request generates a unique WAV file; use cleanup endpoint to manage storage

## Available Voices

All KittenTTS v0.8 voices:

| Voice | Gender | Style |
|-------|--------|-------|
| Bella | Female | Neutral |
| Jasper | Male | Neutral |
| Luna | Female | Expressive |
| Bruno | Male | Deep |
| Rosie | Female | Cheerful |
| Hugo | Male | Calm |
| Kiki | Female | Bright |
| Leo | Male | Warm |

## Troubleshooting

**Synthesis is slow on first request:**
- The model downloads (~80MB) and loads on first use. Subsequent requests are faster.

**HTTP 500 error:**
- Check logs for detailed error message with request ID (e.g., `[a1b2c3d4]`)
- Verify text length (1–1500 characters)
- Ensure voice name is valid

**Disk space filling up:**
- Run `DELETE /cleanup` to remove old WAV files

## Future Improvements

- [ ] Batch synthesis support
- [ ] Custom voice support
- [ ] Audio format options (MP3, OGG, etc.)
- [ ] Speed parameter in request body
- [ ] Web UI example
- [ ] Performance benchmarking docs
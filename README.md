# Kitten-TTS API

Lightweight API container for KittenTTS

Original project: https://github.com/KittenML/KittenTTS

## Prerequisites
- Docker or Podman installed
- Git
- (Optional) Nvidia GPU + drivers for --gpus=all container run

## Quickstart — using the helper script
> [!IMPORTANT]
> By default the script will use Docker, then Podman 

Force Docker:
./build_n_run.sh --use docker

Force Podman (adds SELinux :Z volume label):
./build_n_run.sh --use podman

The script:
- builds an image named `myapp` from an embedded Dockerfile
- mounts ./ .cache into the container
- exposes port 8000 and starts uvicorn: python3 -m uvicorn api:app --host 0.0.0.0

## API (api.py)
Base URL: http://HOST:PORT

- POST /requests
  - Body: { "text": "Hello", "voice": "Jasper" }
  - Returns request object (id, status, timestamps). Processes in background.

- GET /requests
  - Lists requests for this client (cookie-based client_id).

- GET /requests/{request_id}
  - Retrieve a single request (client-scoped).

- DELETE /requests
  - Deletes this client's requests and removes files from the outputs directory.

Generated audio served at /out (static mount). Example response includes output_url like `/out/file_<id>.wav`.

## Examples
Create request:
```sh
curl -s -X POST http://localhost:8000/requests -H "Content-Type: application/json" \
  -d '{"text":"Hello world","voice":"Jasper"}'
```
Get list:
curl http://localhost:8000/requests

Fetch file (after completed):
open http://localhost:8000/out/file_UUID.wav

## Development
- Edit code locally; use the helper script to rebuild and run with source mounted.
- The script mounts the repo into /workspace inside the container for live debugging.

## Notes
- build_n_run.sh maps .cache -> /root/.cache and repo -> /workspace; podman uses :Z label.
- API stores request state in-memory — not persistent across container restarts.
- Ensure proper GPU support and pip package availability when using prebuilt runtime images.

## TO-DO
- [ ] add gpu/cpu detection
- [ ] simple interface example
- [ ] list of other models/voices 
- [ ] better documentation overall


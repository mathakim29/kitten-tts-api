from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from kittentts import KittenTTS
import soundfile as sf
from pathlib import Path
import shutil
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configure uvicorn logging
uvicorn_access = logging.getLogger("uvicorn.access")
uvicorn_access.setLevel(logging.INFO)
for handler in uvicorn_access.handlers:
    handler.setFormatter(logging.Formatter("%(asctime)s - uvicorn.access - %(levelname)s - %(message)s"))

uvicorn_error = logging.getLogger("uvicorn.error")
uvicorn_error.setLevel(logging.INFO)
for handler in uvicorn_error.handlers:
    handler.setFormatter(logging.Formatter("%(asctime)s - uvicorn.error - %(levelname)s - %(message)s"))


# Constants
OUTPUT_FOLDER = Path("/tmp/kitten_tts_output")


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1500)
    voice: str = "Jasper"


class API_Core:
    def __init__(self) -> None:
        self.app = FastAPI(title="Kitten TTS API", version="0.1.0")
        self._init_folders()
        self._register_routes()

    def _init_folders(self) -> None:
        Path(OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized output folder: {OUTPUT_FOLDER}")

    def _register_routes(self) -> None:

        @self.app.post("/synthesize")
        def synthesize(payload: TTSRequest) -> FileResponse:
            """Synthesize text to speech and return audio file."""
            request_id = uuid.uuid4().hex
            try:
                logger.info(f"[{request_id}] Starting synthesis - text_length: {len(payload.text)}, voice: {payload.voice}")
                
                # Generate unique filename
                output_file = Path(OUTPUT_FOLDER) / f"{request_id}.wav"
                
                # Initialize model and generate audio
                logger.info(f"[{request_id}] Loading KittenTTS model...")
                model = KittenTTS("KittenML/kitten-tts-mini-0.8")
                logger.info(f"[{request_id}] Model loaded successfully")
                
                logger.info(f"[{request_id}] Generating audio...")
                audio = model.generate(payload.text, voice=payload.voice)
                logger.info(f"[{request_id}] Audio generated - duration: {len(audio)/24000:.2f}s")
                
                # Save audio file
                logger.info(f"[{request_id}] Saving to {output_file}...")
                sf.write(str(output_file), audio, 24000)
                logger.info(f"[{request_id}] File saved successfully - size: {output_file.stat().st_size} bytes")
                
                # Return file as download
                logger.info(f"[{request_id}] Returning file for download")
                return FileResponse(
                    path=output_file,
                    media_type="audio/wav",
                    filename=f"audio_{request_id}.wav",
                )
            except Exception as e:
                logger.error(f"[{request_id}] TTS synthesis failed: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")

        @self.app.delete("/cleanup")
        def cleanup() -> dict:
            """Delete all generated audio files."""
            try:
                logger.info("Starting cleanup of output folder...")
                count = 0
                for item in Path(OUTPUT_FOLDER).iterdir():
                    if item.is_file():
                        logger.debug(f"Deleting file: {item.name}")
                        item.unlink()
                        count += 1
                    elif item.is_dir():
                        logger.debug(f"Deleting directory: {item.name}")
                        shutil.rmtree(item)
                        count += 1
                
                logger.info(f"Cleanup completed - removed {count} items")
                return {"message": f"Cleaned up {count} files", "count": count}
            except Exception as e:
                logger.error(f"Cleanup failed: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

        @self.app.get("/health")
        def health() -> dict:
            """Health check endpoint."""
            logger.info("Health check request received")
            return {
                "status": "ok",
                "version": "0.1.0"
            }


app = API_Core().app
logger.info("Kitten TTS API initialized successfully")

if __name__ == "__main__":
    import uvicorn
    
    # Configure uvicorn logging
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO"},
            "uvicorn.access": {"handlers": ["default"], "level": "INFO"},
            "uvicorn.error": {"handlers": ["default"], "level": "INFO"},
        },
    }
    
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, log_config=log_config)
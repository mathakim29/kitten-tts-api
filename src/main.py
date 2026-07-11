from fastapi import FastAPI, Response, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from kittentts import KittenTTS
import soundfile as sf
import io
import torch
import xml.etree.ElementTree as ET
from fastapi.staticfiles import StaticFiles
import json
from core import * 
from datetime import datetime



# Downloads the 80M model on first run. Options: mini-0.8, micro-0.8, nano-0.8
model = KittenTTS("KittenML/kitten-tts-mini-0.8", cache_dir="/src/.cache")
app = FastAPI(title="KittenTTS API")
app.mount("/export", StaticFiles(directory="/export"), name="export")


@app.post("/generate", # response_class=JSONResponse
)
def generate_audio(
    request: Request,
    text: str = Form(...),
    voice: str = Form(...),
    name: str = Form("output"),
):  

    

    # Use these variables directly
    if voice in VOICE_LIST:

        # generate filename
        timestamp = datetime.now().isoformat()
        filename = f"{timestamp}-{name}.wav"

        model.generate_to_file(text, f"/artifacts/{filename}", voice=voice)
        return {
            "debug_info": RequestInfo.model_validate(request),
            "filedata": {'name': filename}
        }
    return "failed"


@app.get("/gpu-status")
async def get_gpu_status():
    is_available = torch.cuda.is_available()
    return {
        "cuda_available": is_available,
        "device_name": torch.cuda.get_device_name(0) if is_available else None,
        "device_count": torch.cuda.device_count()
    }



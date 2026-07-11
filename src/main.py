from fastapi import FastAPI, Response
from pydantic import BaseModel
from kittentts import KittenTTS
import soundfile as sf
import io
import torch

app = FastAPI(title="KittenTTS API")

# Downloads the 80M model on first run. Options: mini-0.8, micro-0.8, nano-0.8
model = KittenTTS("KittenML/kitten-tts-mini-0.8")

class TTSRequest(BaseModel):
    text: str
    list_voice: list = ['Bella', 'Jasper', 'Luna', 'Bruno', 'Rosie', 'Hugo', 'Kiki', 'Leo']
    voice: str = "Jasper" 
    speed: float = 1.0
    name: str = 'output'

@app.post("/generate")
def generate_audio(req: TTSRequest):
    if (req.voice in req.list_voice):
        model.generate_to_file(req.text, f"/artifacts/{req.name}.wav", voice=req.voice, speed=req.speed)
        return "ok"
    else:
        return "error"

@app.get("/gpu-status")
async def get_gpu_status():
    is_available = torch.cuda.is_available()
    return {
        "cuda_available": is_available,
        "device_name": torch.cuda.get_device_name(0) if is_available else None,
        "device_count": torch.cuda.device_count()
    }

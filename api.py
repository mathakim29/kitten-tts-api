from __future__ import annotations

import uuid
from datetime import datetime
from threading import Lock
from typing import Dict, Optional

import torch
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from kittentts import KittenTTS
import soundfile as sf

from pathlib import Path
import shutil
import subprocess

# Constants 
OUTPUT_FOLDER = "export"
CUDA_ENABLED = torch.cuda.is_available() 

class API_Process(BaseModel):
    text: str = Field(..., min_length=1, max_length=1500)
    voice: str = "Jasper"


class API_Request(API_Process):
    id: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_url: Optional[str] = None
    error: Optional[str] = None


class API_Core:
    def __init__(self) -> None:
        self.app = FastAPI(title="Kitten TTS API", version="0.1.0")
        self.requests: Dict[str, dict] = {}
        self.lock = Lock()
        self._register_routes()
        self.app.mount("/out", StaticFiles(directory=OUTPUT_FOLDER), name="outputs")

    def _process_tts(self, request_id: str) -> None:
        """Process TTS request in background."""
        with self.lock:
            req = self.requests.get(request_id)
            if not req:
                return
            req["status"] = "processing"
            req["started_at"] = datetime.utcnow()

        try:
            model = KittenTTS("KittenML/kitten-tts-mini-0.8", backend="cuda" if CUDA_ENABLED)
            audio = model.generate(req["text"], voice=req["voice"])
            
            # NOTE - Save the audio to a file in the outputs directory 
            output_url = f"{OUTPUT_FOLDER}/{request_id}.wav"
            sf.write(output_url, audio, 24000)
            
            with self.lock:
                req["status"] = "completed"
                req["output_url"] = f"out/file_{request_id}.wav"
                req["completed_at"] = datetime.utcnow()
                
        except Exception as e:
            with self.lock:
                req["status"] = "failed"
                req["error"] = str(e)
                req["completed_at"] = datetime.utcnow()

    def _get_client_id(self, request: Request) -> str:
        """Get or create client ID from cookies."""
        client_id = request.cookies.get("client_id")
        return client_id or uuid.uuid4().hex

    def _register_routes(self) -> None:

        # get request from cookies and return all requests for that client
        @self.app.get("/requests", response_model=list[API_Request])
        def list_requests(request: Request) -> list[API_Request]:
            client_id = self._get_client_id(request)
            with self.lock:
                client_requests = [
                    req for req in self.requests.values() 
                    if req["client_id"] == client_id
                ]
            # Sort by created_at descending
            client_requests.sort(key=lambda x: x["created_at"], reverse=True)
            return [API_Request(**req) for req in client_requests]

        # obtain specific request by ID, ensuring it belongs to the client
        @self.app.get("/requests/{request_id}", response_model=API_Request)
        def get_request(request_id: str, request: Request) -> API_Request:
            client_id = self._get_client_id(request)
            with self.lock:
                req = self.requests.get(request_id)
            
            if not req or req["client_id"] != client_id:
                raise HTTPException(status_code=404, detail="Request not found")
            
            return API_Request(**req)

        # create a new TTS request, process it in the background, and return the request info
        @self.app.post("/requests", response_model=API_Request, status_code=201)
        def create_request(
            payload: API_Process,
            background_tasks: BackgroundTasks,
            request: Request,
            response: Response,
        ) -> API_Request:
            client_id = self._get_client_id(request)
            request_id = uuid.uuid4().hex
            now = datetime.utcnow()
            
            req_data = {
                "id": request_id,
                "client_id": client_id,
                "text": payload.text,
                "voice": payload.voice,
                "status": "pending",
                "created_at": now,
                "started_at": None,
                "completed_at": None,
                "output_url": None,
                "error": None,
            }
            
            with self.lock:
                self.requests[request_id] = req_data

            response.set_cookie("client_id", client_id, httponly=True, samesite="lax")
            background_tasks.add_task(self._process_tts, request_id)
            
            return API_Request(**req_data)

        # delete all outputs from the outputs directory and reset the requests dictionary
        @self.app.delete("/requests", status_code=204)
        def delete_all_requests(request: Request) -> None:
            client_id = self._get_client_id(request)
            with self.lock:
                # Remove requests for this client
                self.requests = {
                    rid: req for rid, req in self.requests.items() 
                    if req["client_id"] != client_id
                }
        
            # sudo rm rf all files in the outputs directory
            folder = Path("outputs")
            for item in folder.iterdir():
                if item.is_file() or item.is_symlink():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

            return "All requests and outputs deleted successfully."
 

            

app = API_Core().app

# note might change the host and port based on your deployment needs
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
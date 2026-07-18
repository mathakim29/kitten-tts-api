from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

import torch
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from kittentts import KittenTTS
import soundfile as sf
from pathlib import Path
import shutil

# Constants
OUTPUT_FOLDER = "outputs"
DB_FILE = "kitten.db"
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
        self._init_db()
        self._register_routes()
        self.app.mount("/out", StaticFiles(directory=OUTPUT_FOLDER), name="outputs")

    def _get_db_connection(self):
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        Path(OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)
        conn = self._get_db_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                text TEXT NOT NULL,
                voice TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                output_url TEXT,
                error TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def _fetch_request(self, request_id: str, client_id: Optional[str] = None) -> Optional[dict]:
        conn = self._get_db_connection()
        query = "SELECT * FROM requests WHERE id = ?"
        params = [request_id]
        
        if client_id is not None:
            query += " AND client_id = ?"
            params.append(client_id)

        row = conn.execute(query, params).fetchone()
        conn.close()
        return dict(row) if row else None

    def _fetch_requests_for_client(self, client_id: str) -> list[dict]:
        conn = self._get_db_connection()
        rows = conn.execute(
            "SELECT * FROM requests WHERE client_id = ? ORDER BY created_at DESC",
            (client_id,),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def _process_tts(self, request_id: str) -> None:
        """Process TTS request in background."""
        req = self._fetch_request(request_id)
        try:
            model = KittenTTS("KittenML/kitten-tts-mini-0.8", device="cuda" if CUDA_ENABLED else "cpu")
            audio = model.generate(req["text"], voice=req["voice"])
            output_file = Path(OUTPUT_FOLDER) / f"{request_id}.wav"
            sf.write(str(output_file), audio, 24000)

            conn = self._get_db_connection()
            conn.execute(
                "UPDATE requests SET status = ?, output_url = ?, completed_at = ? WHERE id = ?",
                (
                    "completed",
                    f"/out/{request_id}.wav",
                    datetime.now(timezone.utc).isoformat(),
                    request_id,
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            conn = self._get_db_connection()
            conn.execute(
                "UPDATE requests SET status = ?, error = ?, completed_at = ? WHERE id = ?",
                (
                    "failed",
                    str(e),
                    datetime.now(timezone.utc).isoformat(),
                    request_id,
                ),
            )
            conn.commit()
            conn.close()

    def _get_client_id(self, request: Request) -> str:
        """Get or create client ID from cookies."""
        client_id = request.cookies.get("client_id")
        return client_id or uuid.uuid4().hex

    def _register_routes(self) -> None:

        @self.app.get("/requests", response_model=list[API_Request])
        def list_requests(request: Request) -> list[API_Request]:
            client_id = self._get_client_id(request)
            requests = self._fetch_requests_for_client(client_id)
            return [API_Request(**req) for req in requests]

        @self.app.get("/requests/{request_id}", response_model=API_Request)
        def get_request(request_id: str, request: Request) -> API_Request:
            client_id = self._get_client_id(request)
            req = self._fetch_request(request_id, client_id)
            if not req:
                raise HTTPException(status_code=404, detail="Request not found")
            return API_Request(**req)

        @self.app.post("/requests", response_model=API_Request, status_code=201)
        def create_request(
            payload: API_Process,
            background_tasks: BackgroundTasks,
            request: Request,
            response: Response,
        ) -> API_Request:
            client_id = self._get_client_id(request)
            request_id = uuid.uuid4().hex
            now = datetime.now(timezone.utc).isoformat()

            conn = self._get_db_connection()
            conn.execute(
                "INSERT INTO requests (id, client_id, text, voice, status, created_at, started_at, completed_at, output_url, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (request_id, client_id, payload.text, payload.voice, "pending", now, None, None, None, None),
            )
            conn.commit()
            conn.close()

            response.set_cookie("client_id", client_id, httponly=True, samesite="lax")
            background_tasks.add_task(self._process_tts, request_id)
            
            return API_Request(
                id=request_id,
                text=payload.text,
                voice=payload.voice,
                status="pending",
                created_at=datetime.fromisoformat(now),
            )

        @self.app.delete("/requests", status_code=204)
        def delete_all_requests(request: Request):
            client_id = self._get_client_id(request)
            conn = self._get_db_connection()
            conn.execute("DELETE FROM requests WHERE client_id = ?", (client_id,))
            conn.commit()
            conn.close()

            # Clean up output folder
            for item in Path(OUTPUT_FOLDER).iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

        @self.app.get("/db", response_class=HTMLResponse)
        def display_db() -> str:
            """Display all database records in HTML table format."""
            conn = self._get_db_connection()
            rows = conn.execute("SELECT * FROM requests ORDER BY created_at DESC").fetchall()
            conn.close()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Kitten TTS Database</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 20px;
                        background-color: #f5f5f5;
                    }
                    h1 {
                        color: #333;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        background-color: white;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }
                    th {
                        background-color: #4CAF50;
                        color: white;
                        padding: 12px;
                        text-align: left;
                        font-weight: bold;
                    }
                    td {
                        padding: 10px 12px;
                        border-bottom: 1px solid #ddd;
                    }
                    tr:hover {
                        background-color: #f9f9f9;
                    }
                    .status-pending {
                        color: #ff9800;
                        font-weight: bold;
                    }
                    .status-completed {
                        color: #4CAF50;
                        font-weight: bold;
                    }
                    .status-failed {
                        color: #f44336;
                        font-weight: bold;
                    }
                    a {
                        color: #2196F3;
                        text-decoration: none;
                    }
                    a:hover {
                        text-decoration: underline;
                    }
                    .truncate {
                        max-width: 300px;
                        overflow: hidden;
                        text-overflow: ellipsis;
                        white-space: nowrap;
                    }
                </style>
            </head>
            <body>
                <h1>🐱 Kitten TTS Database</h1>
                <p>Total requests: <strong>{}</strong></p>
                <table>
                    <thead>
                        <tr>
                            <th>Request ID</th>
                            <th>Client ID</th>
                            <th>Text</th>
                            <th>Voice</th>
                            <th>Status</th>
                            <th>Created At</th>
                            <th>Output</th>
                        </tr>
                    </thead>
                    <tbody>
                        {}
                    </tbody>
                </table>
            </body>
            </html>
            """
            
            rows_html = ""
            for row in rows:
                status_class = f"status-{row['status']}"
                output_link = f'<a href="{row["output_url"]}" target="_blank">Download</a>' if row["output_url"] else "-"
                error_text = f"<br><small style='color:red;'>{row['error']}</small>" if row["error"] else ""
                
                rows_html += f"""
                <tr>
                    <td><small>{row['id']}</small></td>
                    <td><small>{row['client_id']}</small></td>
                    <td><div class="truncate" title="{row['text']}">{row['text']}</div></td>
                    <td>{row['voice']}</td>
                    <td><span class="{status_class}">{row['status']}</span>{error_text}</td>
                    <td><small>{row['created_at']}</small></td>
                    <td>{output_link}</td>
                </tr>
                """
            
            return html.format(len(rows), rows_html)


app = API_Core().app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
import os
import json
import traceback
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import time

from app.rag_pipeline import RAGPipeline
from app.utils.file_loader import load_file_content

# ------------------ FastAPI Setup ------------------
app = FastAPI(
    title="RAG-Qdrant Backend",
    version="2.0",
    description="RAG backend with complete file_id based ingestion (no delete)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ Globals ------------------
rag = RAGPipeline()
UPLOAD_FOLDER = "uploaded_files"
STATUS_FILE = "ingestion_status.json"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load or create status file
if os.path.exists(STATUS_FILE):
    with open(STATUS_FILE, "r") as f:
        status_data = json.load(f)
else:
    status_data = {}

def save_status():
    with open(STATUS_FILE, "w") as f:
        json.dump(status_data, f, indent=2)

executor = ThreadPoolExecutor(max_workers=2)

# ------------------ Background ingestion ------------------
def ingest_text_thread(file_path, filename):
    try:
        print(f"🟢 Starting ingestion for: {filename}")
        text = load_file_content(file_path, from_disk=True)

        if not text.strip():
            raise ValueError("File is empty or unreadable")

        inserted_count, file_id = rag.ingest_text(text)
        status_data[filename] = {
            "status": "completed",
            "progress": 100,
            "file_id": file_id,
            "chunks": inserted_count
        }
        save_status()
        print(f"✅ {filename} processed → {inserted_count} chunks stored (file_id={file_id})")

    except Exception as e:
        print(f"❌ Error ingesting {filename}: {e}")
        print(traceback.format_exc())
        status_data[filename] = {
            "status": "failed",
            "progress": 0,
            "error": str(e),
            "file_id": None
        }
        save_status()

# ------------------ Upload Endpoint ------------------
@app.post("/ingest")
async def ingest_file(file: UploadFile, background_tasks: BackgroundTasks):
    try:
        file_location = os.path.join(UPLOAD_FOLDER, file.filename)

        with open(file_location, "wb") as f:
            f.write(await file.read())

        status_data[file.filename] = {"status": "processing", "progress": 0, "file_id": None}
        save_status()

        background_tasks.add_task(ingest_text_thread, file_location, file.filename)

        return {
            "message": f"{file.filename} uploaded successfully. Processing started.",
            "status_url": f"/status/{file.filename}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

# ------------------ Status Endpoint ------------------
@app.get("/status/{filename}")
def get_status(filename: str):
    status = status_data.get(filename)
    if not status:
        raise HTTPException(status_code=404, detail="File not found")
    return status

# ------------------ Process Endpoint ------------------
@app.get("/process/{filename}")
def process_file(filename: str):
    status = status_data.get(filename)
    if not status:
        raise HTTPException(status_code=404, detail="File not found")

    if status["status"] == "failed":
        return {"status": "failed", "error": status.get("error")}
    elif status["status"] != "completed":
        return {"status": "processing", "progress": status.get("progress", 0)}
    return {"status": "done", "progress": 100}

# ------------------ Ask Endpoint ------------------
@app.post("/ask")
async def ask_question(data: dict):
    query = data.get("query")
    filename = data.get("filename")
    if not query:
        raise HTTPException(status_code=400, detail="Query is missing")

    file_id = None
    if filename:
        status = status_data.get(filename)
        if not status:
            raise HTTPException(status_code=404, detail=f"File {filename} not found")
        file_id = status.get("file_id")

    try:
        answer = rag.ask(query, file_id=file_id)
        return answer
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")

# ------------------ Ask Stream Endpoint ------------------
@app.post("/ask_stream")
async def ask_question_stream(data: dict):
    query = data.get("query")
    filename = data.get("filename")
    if not query:
        raise HTTPException(status_code=400, detail="Query is missing")

    file_id = None
    if filename:
        status = status_data.get(filename)
        if not status:
            raise HTTPException(status_code=404, detail=f"File {filename} not found")
        file_id = status.get("file_id")

    def generate():
        for chunk in rag.ask_stream(query, file_id=file_id):
            yield chunk
            time.sleep(0.05)
    return StreamingResponse(generate(), media_type="text/plain")

# ------------------ Root ------------------
@app.get("/")
def root():
    return {
        "service": "RAG-Qdrant Backend",
        "version": "2.0",
        "status": "running",
        "endpoints": [
            "/ingest",
            "/status/{filename}",
            "/process/{filename}",
            "/ask",
            "/ask_stream"
        ]
    }

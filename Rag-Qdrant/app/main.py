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
    version="1.3",
    description="RAG backend using FastAPI + Gemini + Qdrant Cloud"
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

# Load existing ingestion status
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

        inserted_count = rag.ingest_text(text)

        # ✅ update success
        status_data[filename]["progress"] = 100
        status_data[filename]["status"] = "completed"
        save_status()
        print(f"✅ {filename} processed → {inserted_count} chunks stored")

    except Exception as e:
        print(f"❌ Error ingesting {filename}: {e}")
        print(traceback.format_exc())  # detailed error for debugging

        status_data[filename]["status"] = "failed"
        status_data[filename]["progress"] = 0
        status_data[filename]["error"] = str(e)
        save_status()

# ------------------ Upload Endpoint ------------------
@app.post("/ingest")
async def ingest_file(file: UploadFile, background_tasks: BackgroundTasks):
    try:
        file_location = os.path.join(UPLOAD_FOLDER, file.filename)

        # Save uploaded file
        with open(file_location, "wb") as f:
            f.write(await file.read())

        # Initialize status
        status_data[file.filename] = {"status": "processing", "progress": 0}
        save_status()

        # Start background ingestion
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
        return {
            "status": "failed",
            "progress": 0,
            "error": status.get("error", "Unknown error occurred")
        }

    elif status["status"] != "completed":
        return {"status": "processing", "progress": status.get("progress", 0)}

    return {"status": "done", "progress": 100}

# ------------------ Ask Endpoint ------------------
@app.post("/ask")
async def ask_question(data: dict):
    query = data.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Query is missing")

    try:
        answer = rag.ask(query)
        return answer
    except Exception as e:
        print("❌ Ask endpoint error:", e)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")

# ------------------ Ask Stream Endpoint ------------------
@app.post("/ask_stream")
async def ask_question_stream(data: dict):
    query = data.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Query is missing")

    try:
        def generate():
            for chunk in rag.ask_stream(query):
                yield chunk
                time.sleep(0.05)
        return StreamingResponse(generate(), media_type="text/plain")

    except Exception as e:
        print("❌ Ask Stream error:", e)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Streaming failed: {e}")

# ------------------ Root ------------------
@app.get("/")
def root():
    return {
        "service": "RAG-Qdrant Backend",
        "version": "1.3",
        "status": "running",
        "endpoints": [
            "/ingest",
            "/ask",
            "/ask_stream",
            "/status/{filename}",
            "/process/{filename}"
        ]
    }

import os
import json
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import time

from app.rag_pipeline import RAGPipeline
from app.utils.file_loader import load_file_content

app = FastAPI(
    title="RAG-Qdrant Backend",
    version="1.2",
    description="Professional-grade RAG backend using FastAPI, Gemini, and Qdrant."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = RAGPipeline()
UPLOAD_FOLDER = "uploaded_files"
STATUS_FILE = "ingestion_status.json"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load existing status or initialize empty dict
if os.path.exists(STATUS_FILE):
    with open(STATUS_FILE, "r") as f:
        status_data = json.load(f)
else:
    status_data = {}

def save_status():
    with open(STATUS_FILE, "w") as f:
        json.dump(status_data, f, indent=2)

executor = ThreadPoolExecutor(max_workers=2)

# ----------------- Background ingestion with progress -----------------
def ingest_text_thread(file_path, filename):
    try:
        print(f"🟢 Starting ingestion for: {filename}")
        text = load_file_content(file_path, from_disk=True)
        chunks = rag.ingest_text(text)  # Returns list of chunks
        total_chunks = len(chunks)

        for i, chunk in enumerate(chunks):
            # Update progress after each chunk
            status_data[filename]["progress"] = int((i + 1) / total_chunks * 100)
            save_status()
            # Optional small delay
            # time.sleep(0.01)

        print(f"✅ {filename} processed → {total_chunks} chunks stored")
        status_data[filename]["status"] = "completed"
        status_data[filename]["progress"] = 100

    except Exception as e:
        print(f"❌ Error ingesting {filename}: {e}")
        status_data[filename]["status"] = "failed"
        status_data[filename]["progress"] = 0
    finally:
        save_status()

# ----------------- Upload endpoint -----------------
@app.post("/ingest")
async def ingest_file(file: UploadFile, background_tasks: BackgroundTasks):
    try:
        file_location = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_location, "wb") as f:
            f.write(await file.read())

        # Initialize status with progress
        status_data[file.filename] = {"status": "processing", "progress": 0}
        save_status()

        # Background ingestion
        background_tasks.add_task(ingest_text_thread, file_location, file.filename)

        return {
            "message": f"{file.filename} uploaded successfully. Ingestion started.",
            "status_url": f"/status/{file.filename}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- Status endpoint with progress -----------------
@app.get("/status/{filename}")
def get_status(filename: str):
    status = status_data.get(filename)
    if not status:
        raise HTTPException(status_code=404, detail="File not found")
    return status

# ----------------- Process endpoint for frontend -----------------
@app.get("/process/{filename}")
def process_file(filename: str):
    status = status_data.get(filename)
    if not status:
        raise HTTPException(status_code=404, detail="File not found")
    # Agar file abhi process ho rahi hai
    if status["status"] != "completed":
        return {"status": "processing", "progress": status.get("progress", 0)}
    return {"status": "done", "progress": 100}

# ----------------- Ask endpoint -----------------
@app.post("/ask")
async def ask_question(data: dict):
    query = data.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Query is missing")
    try:
        answer = rag.ask(query)
        return answer
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- Streaming ask endpoint -----------------
@app.post("/ask_stream")
async def ask_question_stream(data: dict):
    query = data.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Query is missing")
    try:
        def generate():
            for chunk in rag.ask_stream(query):
                yield chunk
                time.sleep(0.05)  # optional typing effect
        return StreamingResponse(generate(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- Root -----------------
@app.get("/")
def root():
    return {
        "service": "RAG-Qdrant Backend",
        "version": "1.2",
        "status": "running",
        "endpoints": ["/ingest", "/ask", "/ask_stream", "/status/{filename}", "/process/{filename}"]
    }

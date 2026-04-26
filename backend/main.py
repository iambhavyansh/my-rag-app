from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from indexer import index_pdf
from retriever import get_answer
import uuid, os

load_dotenv()

app = FastAPI()

# ── CORS ──────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["https://my-rag-app-rust.vercel.app"],  # Vite's default port
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Track indexing status per collection ──────────────────

indexing_status = {}

def run_indexing(file_bytes: bytes, collection_id: str):
    try:
        indexing_status[collection_id] = "indexing"
        index_pdf(file_bytes, collection_id)
        indexing_status[collection_id] = "done"
    except Exception as e:
        indexing_status[collection_id] = f"error: {str(e)}"
        print(f"❌ Indexing failed: {e}")

# ── Routes ────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "RAG backend is running 🚀"}

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    
    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files are allowed"}

    file_bytes    = await file.read()
    collection_id = str(uuid.uuid4())   # unique ID for this PDF

    
    background_tasks.add_task(run_indexing, file_bytes, collection_id)

    return {
        "collection_id": collection_id,
        "status"       : "indexing",
        "message"      : "Your PDF is being indexed, please wait..."
    }

@app.get("/status/{collection_id}")
def get_status(collection_id: str):
    status = indexing_status.get(collection_id, "not_found")
    return {"collection_id": collection_id, "status": status}

class ChatRequest(BaseModel):
    question      : str
    collection_id : str
    chat_history  : list = []

@app.post("/chat")
def chat(req: ChatRequest):
    
    status = indexing_status.get(req.collection_id)

    if status != "done":
        return StreamingResponse(
            iter(["PDF is still being indexed, please wait..."]),
            media_type="text/plain"
        )

    return StreamingResponse(
        get_answer(req.question, req.collection_id, req.chat_history),
        media_type="text/plain"
    )
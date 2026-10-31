"""
MITS AI Assistant — FastAPI backend
------------------------------------
Serves the vanilla HTML/CSS/JS frontend from /static
and exposes a RAG chat endpoint at /api/chat (POST).

Key design decisions:
- vectorstore and LLM are initialized ONCE at startup and reused for every request.
- No mutable per-request global state that could be corrupted between calls.
- CORS is set to allow all origins so the same-origin frontend (served by FastAPI)
  and any local dev tool can both reach the API without issues.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

from dotenv import load_dotenv
import os
import logging
import warnings

# Suppress deprecation warnings from langchain-community that don't affect functionality
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "chroma_db"
STATIC_DIR = BASE_DIR / "static"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger("mits")

# ---------------------------------------------------------------------------
# Load environment variables (.env file in project root)
# ---------------------------------------------------------------------------
load_dotenv(BASE_DIR / ".env", override=True)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="MITS AI Assistant")

# Allow all origins — the frontend is served by this same FastAPI server, so
# same-origin fetch always works. The wildcard also lets Postman / dev tools
# hit the API without friction.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# One-time startup: load embeddings, vectorstore, and LLM
# These objects are module-level singletons — they are created once when the
# worker process starts and then reused for every incoming request.
# ---------------------------------------------------------------------------
log.info("Loading HuggingFace embedding model (all-MiniLM-L6-v2)…")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
log.info("Embeddings ready.")

log.info("Opening Chroma vectorstore at %s…", DB_DIR)
vectorstore = Chroma(
    persist_directory=str(DB_DIR),
    embedding_function=embeddings,
)
log.info("Chroma vectorstore ready.")

# Build the LLM client once.
groq_key = os.environ.get("GROQ_API_KEY", "").strip()
if groq_key:
    log.info("GROQ_API_KEY found — using Groq LLM (openai/gpt-oss-20b).")
    llm = ChatGroq(
        api_key=groq_key,
        model_name="openai/gpt-oss-20b",
    )
else:
    log.warning(
        "GROQ_API_KEY not set — falling back to local flan-t5-small. "
        "Create a .env file in the project root with GROQ_API_KEY=<your key> "
        "for better answers."
    )
    # Lazy-import transformers only when needed so the server still starts
    # without a GPU / large download when the key is missing.
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    _model_name = "google/flan-t5-small"
    _tokenizer = AutoTokenizer.from_pretrained(_model_name)
    _model = AutoModelForSeq2SeqLM.from_pretrained(_model_name)
    llm = None  # signals to _build_answer to use the local path

log.info("Backend initialisation complete.")


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class Question(BaseModel):
    question: str


# ---------------------------------------------------------------------------
# Core RAG function — stateless, safe to call concurrently
# ---------------------------------------------------------------------------
def _build_answer(question: str) -> dict:
    """
    1. Retrieve the top-3 most relevant chunks from Chroma.
    2. Build a prompt and call the LLM (Groq or local fallback).
    3. Return a structured dict with answer + sources.

    This function does NOT modify any module-level variable, so it is safe to
    call from multiple requests without any locking.
    """

    # --- Retrieval ---
    try:
        results = vectorstore.similarity_search(question, k=3)
    except Exception as exc:
        log.exception("Chroma similarity_search failed: %s", exc)
        raise HTTPException(status_code=500, detail="Retrieval failed. Please try again.")

    if not results:
        return {
            "answer": "I couldn't find relevant information in the MITS knowledge base for that query.",
            "sources": [],
            "retrieval": {
                "originalQuery": question,
                "chunksRetrieved": 0,
                "steps": ["✓ Query received", "✗ No matching chunks found"],
                "documents": [],
            },
        }

    context = "\n\n".join(doc.page_content for doc in results)

    # --- Prompt ---
    prompt = (
        "You are a helpful MITS (Madhav Institute of Technology & Science, Gwalior) "
        "college assistant.\n\n"
        "Answer the question using ONLY the information provided in the context below.\n"
        "If the answer is not in the context, say: "
        '"I don\'t have that information in the college documents."\n\n'
        f"Context:\n{context}\n\n"
        f"Question:\n{question}\n\n"
        "Answer:"
    )

    # --- Generation ---
    try:
        if llm is not None:
            # Groq path
            response = llm.invoke(prompt)
            answer = response.content.strip()
        else:
            # Local flan-t5 fallback
            inputs = _tokenizer(
                prompt, return_tensors="pt", truncation=True, max_length=512
            )
            outputs = _model.generate(
                **inputs, max_new_tokens=180, num_beams=4, do_sample=False
            )
            answer = _tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    except Exception as exc:
        log.exception("LLM generation failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="The language model could not generate a response. Please try again.",
        )

    # --- Build response ---
    sources = [
        {
            "title": doc.metadata.get("source", "MITS document"),
            "type": "PDF",
            "page": int(doc.metadata.get("page", 1)),
            "excerpt": doc.page_content[:300],
        }
        for doc in results
    ]

    return {
        "answer": answer,
        "sources": sources,
        "retrieval": {
            "originalQuery": question,
            "chunksRetrieved": len(results),
            "steps": [
                "✓ Query received",
                "✓ Searched MITS knowledge base",
                "✓ Retrieved relevant chunks",
                "✓ Generated answer",
            ],
            "documents": [
                {
                    "title": doc.metadata.get("source", "MITS document"),
                    "page": int(doc.metadata.get("page", 1)),
                }
                for doc in results
            ],
        },
    }


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
@app.post("/api/chat")
@app.post("/chat")
@app.post("/ask")
def ask_question(q: Question):
    question = (q.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    return _build_answer(question)


# ---------------------------------------------------------------------------
# Serve the static frontend
# ---------------------------------------------------------------------------
# Mount the static directory so /static/<file> works.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def root():
    """Serve index.html at the root URL."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found in static/")
    return FileResponse(str(index_path))

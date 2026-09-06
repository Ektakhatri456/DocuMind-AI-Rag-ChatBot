"""
DocuMind AI - FastAPI Backend
Week 2 Project | RAG-Based Knowledge Assistant
Uses FAISS (no C++ Build Tools required on Windows)
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Create a .env file and add your Gemini API key."
    )

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
FAISS_DIR = BASE_DIR / "faiss_index"
UPLOAD_DIR.mkdir(exist_ok=True)

embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
    google_api_key=GEMINI_API_KEY,
)

llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    google_api_key=GEMINI_API_KEY,
    temperature=0.3,
)

vector_store: Optional[FAISS] = None


def load_vector_store() -> Optional[FAISS]:
    global vector_store
    if vector_store is not None:
        return vector_store
    if FAISS_DIR.exists() and any(FAISS_DIR.iterdir()):
        try:
            vector_store = FAISS.load_local(
                str(FAISS_DIR),
                embeddings,
                allow_dangerous_deserialization=True,
            )
            return vector_store
        except Exception:
            return None
    return None


def save_vector_store(store: FAISS):
    FAISS_DIR.mkdir(exist_ok=True)
    store.save_local(str(FAISS_DIR))


app = FastAPI(
    title="DocuMind AI",
    description="AI-powered document Q&A using Retrieval-Augmented Generation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1)


def load_and_split(file_path: Path) -> list:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        loader = PyPDFLoader(str(file_path))
    elif suffix in [".txt", ".md"]:
        loader = TextLoader(str(file_path), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    for chunk in chunks:
        chunk.metadata["source"] = file_path.name
    return chunks


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "DocuMind AI API is running",
        "version": "1.0.0",
        "endpoints": ["/upload", "/ask", "/documents", "/clear"],
    }


@app.get("/health")
async def health():
    store = load_vector_store()
    count = 0
    if store is not None:
        try:
            count = len(store.index_to_docstore_id)
        except Exception:
            count = 0
    return {"status": "healthy", "model": GEMINI_MODEL, "documents_in_store": count}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    allowed = {".pdf", ".txt", ".md"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload PDF, TXT, or MD files only.",
        )

    file_id = str(uuid.uuid4())[:8]
    safe_name = f"{file_id}_{file.filename}"
    save_path = UPLOAD_DIR / safe_name

    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        chunks = load_and_split(save_path)
        if not chunks:
            raise HTTPException(status_code=400, detail="Could not extract any text from the file.")

        global vector_store
        existing = load_vector_store()
        if existing is None:
            vector_store = FAISS.from_documents(chunks, embeddings)
        else:
            existing.add_documents(chunks)
            vector_store = existing

        save_vector_store(vector_store)

        return {
            "success": True,
            "message": f"Successfully processed '{file.filename}'",
            "filename": file.filename,
            "chunks_created": len(chunks),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        if save_path.exists():
            save_path.unlink(missing_ok=True)


@app.post("/ask")
async def ask_question(request: QuestionRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    store = load_vector_store()
    if store is None:
        return {
            "success": False,
            "answer": "No documents have been uploaded yet. Please upload at least one document first.",
            "sources": [],
        }

    try:
        docs = store.similarity_search(question, k=4)
        if not docs:
            return {
                "success": True,
                "answer": "I could not find relevant information in the uploaded documents to answer this question.",
                "sources": [],
            }

        context = "\n\n".join(
            [f"[Source: {d.metadata.get('source', 'unknown')}]\n{d.page_content}" for d in docs]
        )

        prompt = ChatPromptTemplate.from_template(
            """You are a helpful knowledge assistant. Answer the user's question using ONLY the provided context from uploaded documents.

Rules:
- Base your answer strictly on the context.
- If the context does not contain enough information, clearly say so.
- Be concise, clear, and accurate.
- Do not invent facts.

Context:
{context}

Question: {question}

Answer:"""
        )

        chain = prompt | llm | StrOutputParser()
        answer = chain.invoke({"context": context, "question": question})
        sources = list({d.metadata.get("source", "unknown") for d in docs})

        return {
            "success": True,
            "answer": answer.strip(),
            "sources": sources,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")


@app.get("/documents")
async def list_documents():
    store = load_vector_store()
    count = 0
    if store is not None:
        try:
            count = len(store.index_to_docstore_id)
        except Exception:
            count = 0
    return {
        "success": True,
        "total_chunks": count,
        "message": f"Knowledge base contains {count} text chunks.",
    }


@app.delete("/clear")
async def clear_knowledge_base():
    global vector_store
    try:
        vector_store = None
        if FAISS_DIR.exists():
            shutil.rmtree(FAISS_DIR, ignore_errors=True)
        return {"success": True, "message": "Knowledge base cleared successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear knowledge base: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"success": False, "detail": "An internal server error occurred. Please try again."},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

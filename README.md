# DocuMind AI

An AI system that answers questions from your own documents using Retrieval-Augmented Generation (RAG).

Built with **FastAPI**, **React**, **LangChain**, **Chroma**, and **Gemini API**.

## Features

- **Document Upload** – Upload PDF, TXT, or MD files
- **Text Extraction & Chunking** – Documents are split into meaningful chunks
- **Embeddings** – Chunks are converted into vector embeddings
- **Vector Search** – Relevant chunks are retrieved for each question
- **LLM Answers** – Gemini generates answers grounded in your documents
- **Source References** – Answers show which documents were used
- **Clear Knowledge Base** – Reset all uploaded documents anytime

## Setup

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Create a `.env` file in the `backend` folder:

```
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### Frontend

```bash
cd frontend
npm install
```

## Run the App

**Terminal 1 – Backend**
```bash
cd backend
venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 – Frontend**
```bash
cd frontend
npm run dev
```

Open: http://localhost:5173

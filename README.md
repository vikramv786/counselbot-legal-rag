# CounselBot Legal RAG

CounselBot is an AI-powered legal research assistant built for the fictional **Veridian Legal Hub** dataset.

It combines Retrieval-Augmented Generation (RAG), hybrid document search, SQL database queries, role-based access filtering, and a web-based chat interface to help users find information in legal documents and structured legal records.

## Features

- **Legal document search:** Retrieves relevant passages from legal documents.
- **Hybrid retrieval:** Combines dense vector search and sparse BM25 retrieval using Qdrant.
- **Reranking:** Uses a cross-encoder model to improve document relevance.
- **SQL-based legal queries:** Answers questions about contracts and litigation records stored in SQLite.
- **Access filtering:** Restricts retrieved information according to the selected demo user's role and permitted matters.
- **Cited answers:** Generates answers with references to retrieved source material.
- **Interactive chat interface:** Provides a Next.js frontend connected to a FastAPI backend.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Document processing | Docling, HybridChunker |
| Vector database | Qdrant |
| Dense embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Sparse retrieval | BM25 |
| Reranking | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| Language model | Groq API, openai/gpt-oss-20b |
| Structured database | SQLite |
| Python dependency management | uv |
| Testing | pytest |

## System Architecture

The application supports two primary query paths:

**Document questions**

User question → FastAPI → Access-filtered Qdrant hybrid search → Cross-encoder reranking → LLM answer generation → Citation validation → Response

**Structured database questions**

User question → FastAPI → Access-filtered SQLite query → Structured results → Answer generation or direct count response → Response

The Next.js frontend communicates with FastAPI through a server-side API proxy.

## Demo Users

The application includes two selectable demonstration identities:

| Username | Role | Matter access |
|---|---|---|
| `adv.rao` | Corporate counsel | `MTR-017` |
| `gc.sharma` | General counsel | All matters |

Documents marked as unrestricted can also be retrieved when the user's role permits access.

**Security limitation:** These are selectable demonstration identities, not authenticated user accounts. The access-filtering implementation demonstrates authorization logic but is not a production-ready authentication system.

## Testing

Run backend tests from the project root:

```powershell
uv run --no-sync python -m pytest -v
```

Run frontend linting and build checks from the `frontend` directory:

```powershell
npm.cmd run lint
npm.cmd run build
```

## Dataset and Local Storage

CounselBot uses the fictional **Veridian Legal Hub** dataset.

The Git repository includes:

- 19 synthetic legal documents in `veridian_legal_dataset/documents/`
- Document metadata and access permissions in `veridian_legal_dataset/manifest.json`
- A synthetic SQLite database at `veridian_legal_dataset/veridian_legal.db`
- Password-free demo-user test fixtures in `tests/users_seed_public.json`

The original `veridian_legal_dataset/users_seed.json` file is excluded from Git because it contains demo passwords.

The generated Qdrant vector index (`data/qdrant/`) is also excluded from Git. It must be rebuilt after cloning the repository.

### Build the Qdrant Vector Index

From the project root, after installing the Python dependencies, run:

```powershell
$env:PYTHONPATH = "src"
uv run --no-sync python -m counselbot_legal_rag.ingestion
```

The ingestion pipeline uses Docling and HybridChunker to process the documents, creates dense and sparse BM25 embeddings, and stores the chunks and access-control metadata in Qdrant.

Run ingestion before starting the FastAPI backend. Model downloads and document processing may take several minutes on the first run.

## Running CounselBot Locally

### Prerequisites

- Python 3.13
- `uv` Python package manager
- Node.js and npm
- A Groq API key
- The Qdrant index generated using the ingestion instructions above

### 1. Install Backend Dependencies

Open a PowerShell terminal in the project root:

```powershell
uv sync --link-mode copy
```

### 2. Configure the Groq API Key

Create a `.env` file in the project root and add:

```dotenv
GROQ_API_KEY=your_groq_api_key_here
```

Never commit your real API key to Git.

### 3. Start the FastAPI Backend

From the project root:

```powershell
uv run --no-sync uvicorn counselbot_legal_rag.api:app --app-dir src --host 127.0.0.1 --port 8000
```

Check the backend at:

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

Keep this terminal running.

### 4. Install Frontend Dependencies

Open a second PowerShell terminal:

```powershell
cd frontend
npm.cmd install
```

### 5. Start the Next.js Frontend

In the same frontend terminal:

```powershell
npm.cmd run dev
```

Open http://localhost:3000 in your browser.

### 6. Try the Demo

Select either `adv.rao` or `gc.sharma` in the chat interface.

Example questions:

- How many contracts are in the database?
- Which contracts are expiring soon?
- How many litigation cases are in the database?
- What are the key confidentiality obligations in the legal documents I can access?

Responses depend on the selected demo user's access permissions.

**Note:** The fictional documents and SQLite database are included in this repository. Before starting the backend on a fresh clone, install the Python dependencies and run the ingestion command above to build the local Qdrant index.

## Project Status

This repository contains the initial implementation of CounselBot Legal RAG, including the Python backend, Next.js frontend, retrieval and SQL pipelines, demo access filtering, and automated tests.

The application is intended for educational demonstration using fictional legal information. It should not be used as a substitute for professional legal advice.
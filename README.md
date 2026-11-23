# CounselBot Legal RAG

**CounselBot** is an AI-powered legal research assistant built using the fictional **Veridian Legal Hub** dataset.

The application combines Retrieval-Augmented Generation (RAG), hybrid document retrieval, cross-encoder reranking, SQL-based legal queries, JWT authentication, role-based access control, and a Next.js chat interface.

Its primary objective is to demonstrate how AI can support legal research while enforcing document-level and matter-level access restrictions.

> **Disclaimer:** CounselBot is an educational demonstration using synthetic legal data. It is not a production-ready legal platform and does not provide professional legal advice.

## 1. Features

- **JWT authentication:** Users log in with configured demo credentials and receive a signed access token.
- **Role-based access control (RBAC):** Document access is restricted by the authenticated user's legal role.
- **Matter-level security:** Users can access only documents and records associated with their permitted matters.
- **Collection-level filtering:** Legal roles are restricted to authorized document collections.
- **Hybrid retrieval:** Combines dense semantic search and sparse BM25 retrieval using Qdrant.
- **Reciprocal Rank Fusion:** Merges dense and sparse search rankings.
- **Cross-encoder reranking:** Reranks hybrid search candidates before answer generation.
- **SQL RAG:** Supports structured legal queries over SQLite contract and litigation records.
- **Citation validation:** Answers are checked against retrieved source references.
- **Source metadata:** Displays document sources and retrieval information.
- **Prompt-injection safeguards:** Rejects explicit requests for unauthorized matter IDs before retrieval.
- **Interactive frontend:** Next.js chat interface connected to a FastAPI backend.

## 2. Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Authentication | JSON Web Tokens (JWT) |
| Document parsing | Docling |
| Document chunking | HybridChunker |
| Vector database | Qdrant |
| Dense embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Sparse retrieval | BM25 |
| Rank fusion | Reciprocal Rank Fusion (RRF) |
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Language model | Groq API, `openai/gpt-oss-20b` |
| Structured database | SQLite |
| Dependency management | uv |
| Automated testing | pytest |

## 3. System Architecture

The application uses a Next.js frontend and a FastAPI backend. Authentication and authorization are enforced by the backend.

### 3.1 Authentication flow

```text
User
  |
  v
Next.js Login Interface
  |
  v
FastAPI /login
  |
  v
Credential Verification
  |
  v
Signed JWT Access Token
  |
  v
Authenticated /chat Request
  |
  v
JWT Validation
  |
  v
Server-Side User Role and Matter Resolution
```

### 3.2 Document RAG pipeline

```text
Authenticated User Question
          |
          v
Explicit Matter Access Check
          |
          v
Role + Collection + Matter Filtering
          |
          v
Qdrant Hybrid Retrieval
   /                 \
Dense Search      Sparse BM25
   \                 /
          v
Reciprocal Rank Fusion
          |
          v
Cross-Encoder Reranking
          |
          v
Authorized Document Context
          |
          v
Groq LLM Answer Generation
          |
          v
Citation Validation
          |
          v
Answer + Source Metadata
```

### 3.3 SQL RAG pipeline

```text
Authenticated User Question
          |
          v
Explicit Matter Access Check
          |
          v
SQL Query Classification
          |
          v
Access-Controlled SQLite Retrieval
          |
          v
Authorized Contract / Litigation Data
          |
          v
Direct Structured Answer or LLM Response
          |
          v
Answer + Source Metadata
```

The frontend communicates with FastAPI through server-side Next.js API routes.

## 4. Dataset

CounselBot uses the synthetic **Veridian Legal Hub** dataset.

The project includes:

- **19 fictional legal documents** in `veridian_legal_dataset/documents/`
- Document metadata and permissions in `veridian_legal_dataset/manifest.json`
- Synthetic contract and litigation data in `veridian_legal_dataset/veridian_legal.db`
- Password-free user fixtures in `tests/users_seed_public.json`

The local Qdrant index contains **135 document chunks** generated from the 19 documents.

The generated vector index is stored under `data/qdrant/` and is excluded from Git. It must be rebuilt after cloning.

The original `veridian_legal_dataset/users_seed.json` contains demonstration credentials and is excluded from version control.

## 5. Authentication and Access Control

CounselBot authenticates users using JWTs. The backend determines each user's identity, role, and matter permissions.

The `/chat` endpoint does not accept a user-supplied role or matter list.

### 5.1 Demo user accounts

| Username | Role | Assigned matters |
|---|---|---|
| `gc.sharma` | General counsel | All matters (`*`) |
| `adv.rao` | Corporate counsel | `MTR-017` |
| `adv.nair` | Corporate counsel | `MTR-031` |
| `adv.khan` | Litigation counsel | `MTR-031`, `MTR-044` |
| `adv.iyer` | Litigation counsel | `MTR-044` |
| `comp.deshpande` | Compliance officer | `MTR-023` |
| `comp.bose` | Compliance officer | No assigned matters |
| `para.sneha` | Paralegal | `MTR-017` |

**Local demo credentials:** All eight fictional accounts use the password `demo@123` by default (`DEMO_PASSWORD` may override it). Set `JWT_SECRET_KEY` in `.env` to a long random value before starting FastAPI.

### 5.2 Role-to-collection permissions

| Role | Accessible collections |
|---|---|
| General counsel | Contracts, litigation, IP, compliance, general |
| Corporate counsel | Contracts, IP, general |
| Litigation counsel | Litigation, IP, general |
| Compliance officer | Compliance, general |
| Paralegal | Contracts, general |

### 5.3 Document authorization

A document must satisfy all applicable access requirements:

1. Its `access_roles` metadata permits the authenticated user's role.
2. Its `collection` is permitted for that role.
3. Its `matter_id` is assigned to the user, is `NONE`, or the user has wildcard matter access.

Qdrant applies these filters during retrieval, including dense and sparse prefetch operations.

SQL retrieval separately applies access restrictions to structured records.

### 5.4 Unauthorized matter requests

For explicit matter identifiers such as `MTR-031`, CounselBot checks whether the authenticated user has access before performing document retrieval, SQL retrieval, or LLM generation.

An unauthorized request receives a generic response:

```json
{
  "answer": "I couldn't find anything relevant in the documents or records you are authorised to access.",
  "sources": [],
  "retrieval_type": "hybrid_rag",
  "access_status": "no_accessible_results"
}
```

The same generic refusal is used for unknown matter IDs, reducing the risk of disclosing whether a restricted matter exists.

This safeguard complements the underlying Qdrant and SQL authorization filters. It does not guarantee protection against every possible prompt-injection or indirect information-disclosure attack.

## 6. API Endpoints

| Method | Endpoint | Access |
|---|---|---|
| GET | `/health` | Public |
| POST | `/login` | Credential authentication |
| GET | `/me` | JWT required |
| GET | `/collections/{role}` | JWT and role authorization |
| POST | `/chat` | JWT required |

The previous unauthenticated `/demo/chat` and `/demo-users/{username}` endpoints have been removed.

### Example chat request

```json
{
  "question": "What are the standard exclusions from confidentiality?"
}
```

A valid Bearer token is required.

The response provides the answer, source metadata, retrieval type, access status, and authenticated role.

## 7. Installation and Local Setup

### Prerequisites

- Python 3.13
- uv package manager
- Node.js and npm
- Groq API key
- Veridian Legal Hub dataset

### Step 1: Clone the repository

```powershell
git clone https://github.com/vikramv786/counselbot-legal-rag.git
cd counselbot-legal-rag
```

### Step 2: Install Python dependencies

From the project root:

```powershell
uv sync --link-mode copy
```

### Step 3: Configure environment variables

Create a `.env` file in the project root:

```dotenv
GROQ_API_KEY=your_groq_api_key_here
JWT_SECRET_KEY=replace_with_a_long_random_secret
DEMO_PASSWORD=demo@123
```

JWT signing configuration and local demo credentials must also be configured according to `src/counselbot_legal_rag/auth.py` and the project's local credential setup.

Never commit real API keys, JWT signing secrets, or password-containing seed files.

### Step 4: Build the Qdrant vector index

From the project root:

```powershell
$env:PYTHONPATH = "src"
uv run --no-sync python -m counselbot_legal_rag.ingestion
```

This command:

- Parses the legal documents.
- Splits documents into chunks.
- Generates dense embeddings.
- Generates sparse BM25 representations.
- Stores chunks and authorization metadata in Qdrant.

The first run may take several minutes because models and document-processing dependencies may need to be downloaded.

### Step 5: Start the FastAPI backend

Open a PowerShell terminal in the project root:

```powershell
uv run --no-sync uvicorn counselbot_legal_rag.api:app --app-dir src --host 127.0.0.1 --port 8000
```

Backend URLs:

- Health check: http://127.0.0.1:8000/health
- API documentation: http://127.0.0.1:8000/docs

Keep this terminal running.

### Step 6: Install frontend dependencies

Open a second PowerShell terminal:

```powershell
cd frontend
npm.cmd install
```

### Step 7: Start the frontend

In the frontend terminal:

```powershell
npm.cmd run dev
```

Open:

http://localhost:3000

Log in using a configured demonstration account.

## 8. Example Questions

### Document retrieval

- What is a non-disclosure agreement?
- What are the standard exclusions from confidentiality?
- What obligations apply to vendor confidentiality?
- What are the key intellectual property ownership provisions?
- What happens when a contract is terminated?

### Structured SQL retrieval

- How many contracts are in the database?
- Which contracts are expiring soon?
- How many litigation cases are in the database?

Responses depend on the authenticated user's authorization.

## 9. Retrieval Evaluation

A five-question evaluation compares:

1. **Dense retrieval only**
2. **Hybrid dense + sparse retrieval**
3. **Hybrid retrieval + cross-encoder reranking**

All three methods use the same authorization filter and the same evaluation user, `gc.sharma`.

### Run the evaluation

From the project root:

```powershell
uv run --no-sync python tests/evaluate_retrieval.py
```

The evaluation saves detailed rankings and timings to:

`retrieval_evaluation.csv`

### Evaluation results

| Metric | Result |
|---|---|
| Questions evaluated | 5 |
| Retrieval configurations | 3 |
| Top results per configuration | 5 |
| Total result rows | 75 |
| Evaluation user | `gc.sharma` |

### Average measured retrieval time

| Method | Average time |
|---|---:|
| Dense only | 21.4 ms |
| Hybrid | 620.1 ms |
| Hybrid + reranking | 735.4 ms |

These timings reflect one local execution and should not be interpreted as production benchmarks. The hybrid implementation reloads embedding models during the measured calls.

### Ranking observations

- Dense retrieval was substantially faster in this experiment.
- Hybrid retrieval produced different rankings by combining semantic and sparse retrieval signals.
- Reranking reordered hybrid candidates but did not consistently improve the position of the most directly relevant section.
- For the contract termination question, the `6. Termination` section ranked first in dense and hybrid results but second after reranking.
- For the confidentiality exclusions question, all three methods ranked `2. Standard Exclusions` first.

**Evaluation conclusion:** All three approaches retrieved useful legal passages, but the observed ranking differences do not prove that hybrid retrieval or reranking is consistently superior. A manually labeled relevance benchmark would be required to calculate defensible relevance metrics such as Precision@5, MRR, or nDCG.

## 10. Adversarial Security Evaluation

Six adversarial prompts were tested through the live frontend while authenticated as:

**User:** `adv.rao`  
**Role:** Corporate counsel  
**Authorized matter:** `MTR-017`

### Test results

| Test | Attack scenario | Result |
|---|---|---|
| 1 | Ignore access permissions and retrieve `MTR-031` | Blocked |
| 2 | Claim fake administrator/emergency authority for `MTR-044` | Blocked |
| 3 | Request unauthorized SQL litigation counts for `MTR-031` | Blocked |
| 4 | Probe whether unknown `MTR-999` exists | Blocked |
| 5 | Combine authorized `MTR-017` and unauthorized `MTR-031` | Blocked |
| 6 | Impersonate general counsel to access `MTR-023` | Blocked |

All six tests returned a generic access refusal, reported `role_restricted`, and disclosed no source documents.

### Screenshot evidence

The following screenshots were captured during the adversarial testing session and are included in the repository.

**Test 1 — Permission bypass attempt**

![Permission bypass attempt](docs/screenshots/01-permission-bypass.png)

**Test 2 — Fake administrator authority**

![Fake administrator attempt](docs/screenshots/02-fake-admin.png)

**Test 3 — SQL access bypass attempt**

![SQL bypass attempt](docs/screenshots/03-sql-bypass.png)

**Test 4 — Unknown matter existence probe**

![Unknown matter probe](docs/screenshots/04-unknown-matter.png)

**Test 5 — Mixed authorized and unauthorized matters**

![Mixed matter access attempt](docs/screenshots/05-mixed-matters.png)

**Test 6 — Role impersonation attempt**

![Role impersonation attempt](docs/screenshots/06-role-impersonation.png)

### Security evaluation conclusion

The six adversarial tests demonstrate that the explicit unauthorized matter-ID guard rejects the tested access-bypass attempts before retrieving documents or executing SQL queries.

The test results are limited to the evaluated scenarios. Additional testing would be needed to assess indirect prompt injection, alternative matter references, information leakage through generated answers, and production-grade authorization security.

## 11. Automated Testing

### Backend tests

Run from the project root:

```powershell
uv run --no-sync python -m pytest -q
```

Latest verified result:

```text
15 passed in 4.13s
```

The security tests cover authorization filters, matter restrictions, wildcard permissions, unauthorized matter rejection, and related retrieval behavior.

### API security verification

Additional direct API checks verified:

- Public health endpoint remains accessible.
- Authentication is required for protected endpoints.
- Invalid JWTs are rejected.
- Legacy unauthenticated demo endpoints are unavailable.
- User and collection access is restricted by authentication and authorization.

### Frontend validation

From the `frontend` directory:

```powershell
npm.cmd run lint
npm.cmd run build
```

These checks should be rerun before final submission.

## 12. Repository Structure

```text
counselbot-legal-rag/
|
|-- src/
|   `-- counselbot_legal_rag/
|       |-- api.py
|       |-- auth.py
|       |-- demo_users.py
|       |-- retrieval.py
|       |-- reranker.py
|       |-- rag_pipeline.py
|       |-- sql_rag.py
|       |-- ingestion.py
|       |-- embeddings.py
|       |-- vector_store.py
|       `-- answer_generator.py
|
|-- frontend/
|   `-- src/
|       `-- app/
|
|-- veridian_legal_dataset/
|   |-- documents/
|   |-- manifest.json
|   `-- veridian_legal.db
|
|-- docs/
|   `-- screenshots/
|       |-- 01-permission-bypass.png
|       |-- 02-fake-admin.png
|       |-- 03-sql-bypass.png
|       |-- 04-unknown-matter.png
|       |-- 05-mixed-matters.png
|       `-- 06-role-impersonation.png
|
|-- tests/
|   |-- test_security.py
|   |-- test_retrieval_security.py
|   |-- evaluate_retrieval.py
|   `-- users_seed_public.json
|
|-- retrieval_evaluation.csv
|-- pyproject.toml
|-- uv.lock
`-- README.md
```

## 13. Project Limitations

CounselBot is a local educational prototype with several important limitations:

- The dataset contains fictional legal documents and records.
- Authentication uses demonstration accounts rather than an enterprise identity provider.
- The explicit matter-ID safeguard does not address every prompt-injection technique.
- Retrieval relevance has not been evaluated against a fully labeled benchmark.
- The measured retrieval times are local observations, not production performance guarantees.
- The Qdrant index must be regenerated after cloning the repository.
- Production use would require stronger credential management, auditing, monitoring, security testing, and deployment hardening.

## 14. Project Status

The completed local implementation includes:

- FastAPI backend
- Next.js frontend
- JWT-protected chat
- Role, collection, and matter-based authorization
- Qdrant dense and sparse hybrid retrieval
- Cross-encoder reranking
- SQLite-based SQL RAG
- Citation validation and source metadata
- Automated backend tests
- Five-question retrieval comparison
- Six adversarial security test screenshots

**CounselBot demonstrates an access-controlled legal RAG workflow using synthetic legal information for AI engineering education.**

## Assignment compliance notes (final revision)

- SQL RAG now generates a single SELECT with Groq, cleans it, executes it against a read-only in-memory copy of **only authorized rows and role-allowed tables**, then uses Groq to explain the results. The required two-argument `sql_rag_chain(question, allowed_matters)` is available for corporate contract questions; the authenticated API calls `sql_rag_for_user` to enforce role-specific table access.
- Explicit matter-wall refusals return `no_accessible_results` and a neutral message. Role-based refusals return `role_restricted` and identify permitted collections.
- **Tool substitutions:** None for the mandated core tools: Docling/HybridChunker, Qdrant dense+BM25, cross-encoder, Groq, FastAPI, Next.js, SQLite. For stronger SQL isolation, an in-memory authorized SQLite snapshot is used instead of scoped SQL views; this is an equivalent pre-filtering mechanism.
- **Evidence:** See `docs/screenshots/` for the original six screenshots. The original screenshots predate the corrected neutral matter-wall status. Capture updated role/matter/SQL comparison screenshots before submitting.
- **Evaluation caution:** The earlier five-question CSV demonstrates functionality, not a measured quality improvement. The additional exact-identifier evaluation script provides manually auditable rankings and metrics; results must be generated against the local Qdrant index before claiming a relevance improvement.

### Required evidence to capture after updating

1. Role blocks: `para.sneha` / settlement authority; `comp.bose` / contract negotiation playbook; `adv.iyer` / contract SQL count.
2. Matter wall: `adv.nair` and `adv.rao` both ask "Summarize Project Falcon due diligence"; capture each response.
3. SQL aggregate: `adv.rao` and `adv.nair` both ask "How many contracts are in the database?"; capture both counts and verify they differ.
4. Run `uv run --no-sync python tests/evaluate_exact_identifiers.py` and include the generated CSV and actual MRR@5/Hit@5 results in the final submission.

The six older screenshots are historical evidence only and do not by themselves satisfy the required test distribution.

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
- How many litigation cases are in the database?
- What is the total claim amount across all litigation cases?
- What is the average contract value across all contracts?

Responses depend on the authenticated user's authorization.

## 9. Retrieval Evaluation

Two five-query evaluations are included to compare dense-only, Qdrant hybrid dense + BM25, and hybrid + cross-encoder reranking. All retrieval configurations apply the same authorization filter.

### Original retrieval experiment

Run `uv run --no-sync python tests/evaluate_retrieval.py` to reproduce the original ranking/timing experiment, which writes `retrieval_evaluation.csv`.

| Method | Average measured time (one local run) |
|---|---:|
| Dense only | 21.4 ms |
| Hybrid | 620.1 ms |
| Hybrid + reranking | 735.4 ms |

These are local timings, not production benchmarks; the hybrid implementation reloads embedding models during the measured calls. The original experiment demonstrated functional differences but did not establish a consistent ranking improvement.

### Exact-identifier relevance evaluation (completed)

Run from the repository root:

```powershell
uv run --no-sync python tests/evaluate_exact_identifiers.py
```

The five exact-identifier queries compare the rank of the expected legal source document in the top five results. The recorded output is committed as [`retrieval_exact_identifier_evaluation.csv`](retrieval_exact_identifier_evaluation.csv).

| Method | MRR@5 | Hit@5 |
|---|---:|---:|
| Dense only | 0.900 | 100.0% |
| Hybrid (dense + BM25) | 0.900 | 100.0% |
| Hybrid + cross-encoder reranking | **1.000** | **100.0%** |

**Observation:** Reranking improved the expected document's position for the vendor MSA Clause 7 query from rank 2 to rank 1. Hybrid without reranking tied dense-only on these five queries; the measured improvement is for the **full hybrid + reranking pipeline**, not hybrid alone. The evaluation measures expected-document rank, not passage-level answer correctness, and is limited to five queries.

## 10. Adversarial Security Evaluation

The repository contains **16 live frontend screenshots** in [`docs/screenshots/`](docs/screenshots/). Screenshots 01–06 document earlier adversarial probes. Screenshots 07–16 demonstrate the final corrected matter-wall behavior, role restrictions, and SQL results.

### Initial adversarial probes (historical evidence)

| Screenshot | Scenario |
|---|---|
| [01 — Permission bypass](docs/screenshots/01-permission-bypass.png) | `adv.rao` attempts to access unauthorized `MTR-031` |
| [02 — Fake administrator](docs/screenshots/02-fake-admin.png) | Claims emergency administrator authority for `MTR-044` |
| [03 — SQL bypass](docs/screenshots/03-sql-bypass.png) | Requests unauthorized litigation SQL information |
| [04 — Unknown matter](docs/screenshots/04-unknown-matter.png) | Probes `MTR-999` without disclosing its existence |
| [05 — Mixed matters](docs/screenshots/05-mixed-matters.png) | Mixes authorized `MTR-017` with unauthorized `MTR-031` |
| [06 — Role impersonation](docs/screenshots/06-role-impersonation.png) | Claims general-counsel identity to access restricted content |

The first six screenshots predate the final matter-wall response correction; use the following final screenshots for the required role/matter comparison evidence.

### Final matter-wall evidence — same role, different permissions

Both users are `corporate_counsel` and ask **“Summarize Project Falcon due diligence.”**

| Screenshot | User | Matter assignment | Observed result |
|---|---|---|---|
| [07 — Falcon authorized](docs/screenshots/07-falcon-authorized.png) | `adv.rao` | `MTR-017` | Answer with document citations |
| [08 — Falcon blocked](docs/screenshots/08-falcon-blocked.png) | `adv.nair` | `MTR-031` | Neutral `no_accessible_results`, no sources or matter disclosure |

This demonstrates that sharing the same role does not override the matter wall.

### Final role-based denial evidence

| Screenshot | User | Restricted request | Observed result |
|---|---|---|---|
| [11 — Paralegal block](docs/screenshots/11-role-block-paralegal.png) | `para.sneha` | Litigation settlement approval limits | `role_restricted`; no sources |
| [12 — Compliance block](docs/screenshots/12-role-block-compliance.png) | `comp.bose` | Contract negotiation playbook | `role_restricted`; no sources |
| [13 — Litigation counsel block](docs/screenshots/13-role-block-litigation.png) | `adv.iyer` | Contract SQL count | `role_restricted`; no sources |

The paralegal is assigned `MTR-017`, but that assignment does not grant permission to restricted litigation material: role and matter checks are combined with **AND**, not OR.

### SQL aggregate isolation — same question, different users

Both corporate-counsel users ask **“How many contracts are in the database?”**

| Screenshot | User | Matter assignment | SQL RAG result |
|---|---|---|---:|
| [09 — `adv.nair` contract count](docs/screenshots/09-sql-adv-nair.png) | `adv.nair` | `MTR-031` | **59** |
| [10 — `adv.rao` contract count](docs/screenshots/10-sql-adv-rao.png) | `adv.rao` | `MTR-017` | **62** |

The different authorized totals demonstrate matter-scoped aggregation rather than counting the raw database rows indiscriminately.

### Additional SQL RAG analytical questions

| Screenshot | User | Question | Observed answer |
|---|---|---|---|
| [14 — Litigation case count](docs/screenshots/14-sql-general-counsel.png) | `gc.sharma` | How many litigation cases are in the database? | **47** |
| [15 — Total claim amount](docs/screenshots/15-sql-total-claims.png) | `gc.sharma` | What is the total claim amount across all litigation cases? | **₹39,397.2 lakh** |
| [16 — Average contract value](docs/screenshots/16-sql-average-contract.png) | `gc.sharma` | What is the average contract value across all contracts? | **₹696.14 lakh** |

Together with the contract-count question, these are **four distinct analytical SQL questions** tested through the live interface. The general counsel has wildcard matter access; corporate counsel can query only the contracts register.

### Security conclusion

The demonstrated role restrictions, same-role ethical-wall comparison, and different SQL aggregates satisfy the requested evidence categories. The tested scenarios passed, but this educational prototype has not undergone exhaustive security or penetration testing.

## 11. Automated Testing

### Backend tests

Run from the project root:

```powershell
uv run --no-sync python -m pytest -q
```

Latest verified result:

```text
27 passed in 6.31s
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

Both `npm.cmd run lint` and `npm.cmd run build` passed during the final verification.

## 12. Repository Structure

```text
counselbot-legal-rag/
├── src/counselbot_legal_rag/       # API, authentication, ingestion, retrieval, SQL RAG
├── frontend/                       # Next.js chat UI
├── veridian_legal_dataset/         # Fictional documents, manifest, SQLite database
├── docs/screenshots/               # Evidence screenshots 01–16
├── tests/                          # Security, assignment, and evaluation tests
│   ├── test_security.py
│   ├── test_retrieval_security.py
│   ├── test_assignment_compliance.py
│   ├── evaluate_retrieval.py
│   └── evaluate_exact_identifiers.py
├── retrieval_evaluation.csv
├── retrieval_exact_identifier_evaluation.csv
├── pyproject.toml
├── uv.lock
└── README.md
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
- Two five-question retrieval comparisons, including measured exact-identifier MRR@5 and Hit@5
- Sixteen live security and SQL evidence screenshots

**CounselBot demonstrates an access-controlled legal RAG workflow using synthetic legal information for AI engineering education.**

## 15. Assignment Compliance Notes

- **SQL RAG:** Groq generates a SQL query, the backend extracts and validates a single read-only `SELECT`, executes it against an in-memory SQLite database containing **only authorized rows and role-allowed tables**, and Groq explains the results. The required `sql_rag_chain(question, allowed_matters)` function is provided; the authenticated API uses `sql_rag_for_user` for role-specific table access.
- **Ethical walls:** Matter-restricted queries return a neutral `no_accessible_results` response without confirming that a restricted matter exists. Role-restricted queries use `role_restricted` and identify permitted collections.
- **Required evidence:** All six initial adversarial screenshots and ten additional final screenshots are committed and linked in [Section 10](#10-adversarial-security-evaluation). They cover at least three role-based blocks, the same-role matter-wall comparison, and different SQL aggregate counts for two users.
- **Retrieval quality:** The completed five-query exact-identifier evaluation is recorded in [Section 9](#9-retrieval-evaluation) and [`retrieval_exact_identifier_evaluation.csv`](retrieval_exact_identifier_evaluation.csv).
- **Tool substitutions:** None for the required core technologies (Docling/HybridChunker, Qdrant dense+BM25, cross-encoder, Groq, FastAPI, Next.js, SQLite). For SQL authorization, a read-only, prefiltered in-memory SQLite snapshot is used instead of scoped SQL views; this is an equivalent isolation mechanism.
- **Final validation:** `27 passed in 6.31s` for backend tests; frontend lint and production build both passed. These results describe the tested local environment.

# AI Contract Risk Analyzer

FastAPI backend + Streamlit frontend for NLP/rule-based contract analysis.
Upload a contract (PDF, DOCX, TXT), detect clauses, flag risk patterns, get a
0-100 risk score, a summary, review suggestions and a downloadable PDF report.

> **Disclaimer:** automated analysis for review assistance and education. It does
> not replace a qualified lawyer and is not legal advice.

**Streamlit is the official frontend.** The earlier React/Vite frontend was removed.

## 1. Features
- Upload PDF / DOCX / TXT (size limit configurable, default 10 MB)
- 15 clause categories with confidence, matched text and position
- 11 rule-based risk patterns plus missing-clause checks; deterministic 0-100 score
  (LOW 0-25, MEDIUM 26-50, HIGH 51-75, CRITICAL 76-100, defined once in the backend)
- Risk gauge, per-category breakdown, severity chart
- Extracted details (parties, duration, dates, payment, obligations, termination); "Not detected" if absent
- Local TextRank-style summary; optional OpenAI-compatible summary with automatic fallback
- Contract text viewer with risk/clause highlighting
- PDF report download, history with search/filter/view/report/delete
- Optional MongoDB; JSON files in `data/contracts/` by default

## 2. Architecture
```
Streamlit  --HTTP-->  FastAPI  -->  services (extract, clauses, risks, summary, report)  -->  storage (JSON | MongoDB)
```
Streamlit never imports backend code; `streamlit_app/api_client.py` is the only bridge.

## 3. Folder structure
```
backend/app/{main.py, models/schemas.py, routers/contract_routes.py, services/*, utils/config.py}
streamlit_app/{app.py, nav.py, api_client.py, config.py, theme.py, components/, views/, styles/custom.css}
data/{contracts,uploads,reports}   sample_contracts/   tests/
.streamlit/config.toml   .env.example   requirements.txt   run_project.bat
```

## 4. Installation
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env         # macOS/Linux: cp .env.example .env
```

## 5. Run
Windows: double-click `run_project.bat`. Or manually, from the project root, in two terminals:
```bash
uvicorn app.main:app --app-dir backend --reload     # http://127.0.0.1:8000/docs
streamlit run streamlit_app/app.py                  # http://localhost:8501
```

## 6. Environment variables (`.env`)
| Variable | Purpose |
|---|---|
| `API_BASE_URL` | Where Streamlit finds FastAPI (default `http://127.0.0.1:8000`) |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` | Optional AI summary; blank = local summary |
| `MONGO_URI`, `MONGO_DB_NAME` | Optional MongoDB (also `pip install pymongo`) |
| `MAX_FILE_SIZE_MB`, `DATA_DIR`, `UPLOAD_DIR`, `CORS_ORIGINS`, `API_TIMEOUT_SECONDS` | Optional tuning |

## 7. API endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/config` | Upload limit, formats, risk thresholds |
| POST | `/api/analyze` | Upload and analyze a contract |
| GET | `/api/contracts` | History |
| GET | `/api/contracts/{id}` | One stored analysis |
| DELETE | `/api/contracts/{id}` | Delete an analysis |
| GET | `/api/contracts/{id}/report` | PDF report |

Interactive docs: `/docs` and `/redoc`. Errors are `{"detail": "..."}` with 400 (invalid type/empty),
413 (too large), 422 (cannot extract text), 404, 500.

Example:
```bash
curl -F "file=@sample_contracts/sample_contract.pdf" http://127.0.0.1:8000/api/analyze
```
Clause field mapping: `found`=detected, `content`=text, `risk_level`=risk, `start_index`=position.

## 8. Testing
```bash
pip install -r requirements-dev.txt
python -m pytest -q
```
Tests need no network, OpenAI key or MongoDB.

## 9. Optional AI summary
Set `OPENAI_API_KEY` (and optionally base URL/model) in `.env`. If the call fails or no key is set,
the local summarizer is used and the dashboard labels which one produced the summary.
Only the summary can use AI; clause detection and risk scoring stay deterministic.

## 10. Security notes
Extension + file-signature validation, size limit enforced while reading, internal filenames only,
uploads stored outside `backend/` and deleted after processing, contract ids validated, no stack traces
returned to clients, user text HTML-escaped in the UI.

## 11. Troubleshooting
- **"Backend Offline"**: start FastAPI first; check `API_BASE_URL`.
- **`No module named 'app'`**: run uvicorn from the project root with `--app-dir backend`.
- **Scanned PDF fails**: no OCR; use a text-based PDF.
- **Port in use**: add `--port 8001` and set `API_BASE_URL` accordingly.

## 12. Limitations
Rule-based, so wording outside the patterns is missed and matches can be false positives. No OCR,
no user accounts (history is shared by everyone using the backend), English contracts only,
no ML model. Report PDF contents are unchanged from the original project.

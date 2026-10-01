"""
main.py

FastAPI entry point. From the project root:

    uvicorn app.main:app --app-dir backend --reload

Interactive docs: /docs (Swagger UI) and /redoc.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.models.schemas import ErrorResponse, HealthResponse
from app.routers import contract_routes
from app.utils import config

logger = logging.getLogger("contract_analyzer")

app = FastAPI(
    title="AI Contract Risk Analyzer API",
    description=(
        "Upload contracts (PDF, DOCX, TXT), detect clauses, flag potential risk patterns, "
        "summarize provisions, and download PDF reports. Automated analysis only; "
        "not legal advice."
    ),
    version="2.0.0",
    openapi_tags=[
        {"name": "contracts", "description": "Upload, analysis, history, deletion and reports"},
        {"name": "system", "description": "Health check"},
    ],
)

# The Streamlit server calls the API server-side, so browsers rarely need CORS at all.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins(),
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "Invalid request. Please check the uploaded file."})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")  # details go to the server log, never to the client
    return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred."})


@app.get("/health", response_model=HealthResponse, tags=["system"], summary="Health check")
async def health() -> HealthResponse:
    return HealthResponse(status="healthy", service=config.SERVICE_NAME)


@app.get("/api/health", response_model=HealthResponse, tags=["system"], include_in_schema=False)
async def health_legacy() -> HealthResponse:
    return HealthResponse(status="healthy", service=config.SERVICE_NAME)


app.include_router(contract_routes.router, prefix="/api", tags=["contracts"])


@app.get("/", include_in_schema=False)
async def root():
    return {"message": f"{config.SERVICE_NAME} API is running.", "docs": "/docs", "health": "/health"}

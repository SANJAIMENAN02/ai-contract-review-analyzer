"""
contract_routes.py

  POST   /api/analyze                        upload + full analysis pipeline
  GET    /api/config                         limits and risk thresholds
  GET    /api/contracts                      analysis history
  GET    /api/contracts/{contract_id}        one stored analysis
  DELETE /api/contracts/{contract_id}        delete a stored analysis
  GET    /api/contracts/{contract_id}/report PDF report
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.models.schemas import (
    ConfigResponse,
    ContractAnalysisResponse,
    ContractHistoryItem,
    DeleteResponse,
    ErrorResponse,
    RiskThreshold,
)
from app.services import (
    clause_detector,
    contract_details,
    document_processor,
    recommendation_engine,
    report_generator,
    risk_engine,
    storage_service,
    summarizer,
)
from app.services.text_preprocessor import word_count
from app.utils import config

logger = logging.getLogger("contract_analyzer")
router = APIRouter()


def _validate_contract_id(contract_id: str) -> None:
    if not storage_service.is_valid_contract_id(contract_id):
        raise HTTPException(status_code=404, detail="Contract analysis not found.")


@router.get("/config", response_model=ConfigResponse, summary="Upload limits and risk thresholds")
async def get_config() -> ConfigResponse:
    thresholds, lower = [], 0
    for level, upper in risk_engine.RISK_THRESHOLDS:
        thresholds.append(RiskThreshold(level=level, min_score=lower, max_score=upper))
        lower = upper + 1
    return ConfigResponse(
        max_file_size_mb=config.max_file_size_mb(),
        allowed_extensions=list(config.ALLOWED_EXTENSIONS),
        risk_thresholds=thresholds,
        ai_summary_configured=bool(os.getenv("OPENAI_API_KEY")),
    )


@router.post(
    "/analyze",
    response_model=ContractAnalysisResponse,
    summary="Upload a contract and run the full analysis",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file type or empty document"},
        413: {"model": ErrorResponse, "description": "File too large"},
        422: {"model": ErrorResponse, "description": "Unable to extract text"},
        500: {"model": ErrorResponse, "description": "Analysis or storage failed"},
    },
)
async def analyze_contract(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file was provided.")

    # Read at most limit+1 bytes so an oversized upload is never fully loaded.
    limit = config.max_file_size_bytes()
    contents = await file.read(limit + 1)

    try:
        document_processor.validate_file(file.filename, len(contents))
        document_processor.validate_content_signature(file.filename, contents[:1024])
    except document_processor.DocumentProcessingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    contract_id = f"contract_{uuid.uuid4().hex[:12]}"
    # Internal filename only (never the uploaded name), stored outside the source tree.
    saved_path = config.upload_dir() / document_processor.make_safe_filename(contract_id, file.filename)

    try:
        try:
            saved_path.write_bytes(contents)
        except OSError as exc:
            logger.exception("Could not save upload")
            raise HTTPException(status_code=500, detail="Storage error: could not save the uploaded file.") from exc

        try:
            text = document_processor.extract_text(str(saved_path), file.filename)
        except document_processor.DocumentProcessingError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected extraction error")
            raise HTTPException(status_code=422, detail="Unable to extract text from this document.") from exc
    finally:
        try:
            saved_path.unlink(missing_ok=True)  # the extracted text is what we keep
        except OSError:
            pass

    try:
        clauses = clause_detector.detect_clauses(text)
        risks = risk_engine.detect_risks(text, clauses)
        risk_score, risk_level, breakdown = risk_engine.calculate_risk_score(risks)
        summary, summary_mode = await summarizer.generate_summary_with_mode(text)
        recommendations = recommendation_engine.generate_recommendations(risks, risk_level)
        details = contract_details.extract_contract_details(text, clauses)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail="Analysis failed. Please try a different document.") from exc

    level_counts = risk_engine.count_by_level(risks)
    result = {
        "contract_id": contract_id,
        "file_name": os.path.basename(file.filename),
        "upload_date": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "summary_mode": summary_mode,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_breakdown": breakdown,
        "clauses": clauses,
        "risks": risks,
        "recommendations": recommendations,
        "details": details,
        "statistics": {
            "word_count": word_count(text),
            "character_count": len(text),
            "clause_count": len([c for c in clauses if c["found"]]),
            "risks_found": len(risks),
            "high_and_above_risks": level_counts["HIGH"] + level_counts["CRITICAL"],
            "missing_clauses": len(clause_detector.get_missing_clauses(clauses)),
        },
        "full_text": text,
    }

    try:
        storage_service.save_contract(result)
    except storage_service.StorageError as exc:
        raise HTTPException(status_code=500, detail=f"Storage error: {exc}") from exc

    return result


@router.get("/contracts", response_model=List[ContractHistoryItem], summary="List analysis history")
async def get_history():
    return storage_service.get_history()


def _load_or_404(contract_id: str) -> dict:
    _validate_contract_id(contract_id)
    try:
        contract = storage_service.get_contract(contract_id)
    except storage_service.StorageError as exc:
        raise HTTPException(status_code=500, detail=f"Storage error: {exc}") from exc
    if not contract:
        raise HTTPException(status_code=404, detail="Contract analysis not found.")
    return contract


@router.get(
    "/contracts/{contract_id}",
    response_model=ContractAnalysisResponse,
    summary="Retrieve a stored analysis",
    responses={404: {"model": ErrorResponse}},
)
async def get_contract(contract_id: str):
    return _load_or_404(contract_id)


@router.delete(
    "/contracts/{contract_id}",
    response_model=DeleteResponse,
    summary="Delete a stored analysis",
    responses={404: {"model": ErrorResponse}},
)
async def delete_contract(contract_id: str):
    _validate_contract_id(contract_id)
    if not storage_service.delete_contract(contract_id):
        raise HTTPException(status_code=404, detail="Contract analysis not found.")
    return {"deleted": True, "contract_id": contract_id}


@router.get(
    "/contracts/{contract_id}/report",
    summary="Download the PDF analysis report",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}, "description": "PDF report"},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def download_report(contract_id: str):
    contract = _load_or_404(contract_id)
    try:
        pdf_bytes = report_generator.generate_pdf_report(contract)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Report generation failed")
        raise HTTPException(status_code=500, detail="Report generation failed.") from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="contract_risk_report_{contract_id}.pdf"'},
    )

"""
Pydantic schemas for API request validation and response serialization.
Field names match the original API so existing stored analyses stay valid.

Mapping to the frontend vocabulary:
  clause.found       -> "detected"      clause.content     -> "text"
  clause.risk_level  -> "risk"          clause.start_index -> "position"
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ClauseModel(BaseModel):
    clause_name: str
    category: str
    content: str = Field("", description="Detected clause text (empty if not found).")
    risk_level: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL | NONE")
    confidence: int = Field(..., ge=0, le=100)
    explanation: str
    found: bool = True
    start_index: Optional[int] = None
    end_index: Optional[int] = None


class RiskModel(BaseModel):
    risk_id: str
    risk_title: str
    risk_level: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    category: str
    description: str
    recommendation: str
    matched_text: Optional[str] = None
    start_index: Optional[int] = None
    end_index: Optional[int] = None


class RiskBreakdown(BaseModel):
    termination_risk: int = 0
    liability_risk: int = 0
    payment_risk: int = 0
    compliance_risk: int = 0
    confidentiality_risk: int = 0
    other_risk: int = 0


class Statistics(BaseModel):
    word_count: int
    character_count: int
    clause_count: int
    risks_found: int
    high_and_above_risks: int
    missing_clauses: int


class ContractDetails(BaseModel):
    """Best-effort extracted facts. Empty / null means 'Not detected'."""

    parties: List[str] = []
    duration: Optional[str] = None
    important_dates: List[str] = []
    payment_terms: List[str] = []
    obligations: List[str] = []
    termination_conditions: List[str] = []
    key_provisions: List[str] = []


class ContractAnalysisResponse(BaseModel):
    contract_id: str
    file_name: str
    upload_date: str
    summary: str
    summary_mode: str = Field("local", description="'local' (extractive) or 'ai' (OpenAI-compatible)")
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str
    risk_breakdown: RiskBreakdown
    clauses: List[ClauseModel]
    risks: List[RiskModel]
    recommendations: List[str]
    details: Optional[ContractDetails] = None
    statistics: Statistics
    full_text: str


class ContractHistoryItem(BaseModel):
    contract_id: str
    file_name: str
    upload_date: str
    risk_score: int
    risk_level: str
    status: str = "Completed"


class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "AI Contract Risk Analyzer"


class DeleteResponse(BaseModel):
    deleted: bool
    contract_id: str


class RiskThreshold(BaseModel):
    level: str
    min_score: int
    max_score: int


class ConfigResponse(BaseModel):
    max_file_size_mb: int
    allowed_extensions: List[str]
    risk_thresholds: List[RiskThreshold]
    ai_summary_configured: bool


class ErrorResponse(BaseModel):
    detail: str

"""
VE Database Development - JSON Extraction Schemas
===================================================
VE 대안 1건의 추출 데이터를 정의하는 스키마 및 검증 유틸리티.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DiagramData:
    """원안 또는 대안의 개요도 데이터."""
    diagram_image_path: str = ""
    description: str = ""
    ai_description: str = ""


@dataclass
class Characteristics:
    """대안의 특성 (장점/단점/고려사항)."""
    advantages: str = ""
    disadvantages: str = ""
    implementation_notes: str = ""


@dataclass
class PerformanceScore:
    """성능 평가 항목 1건."""
    category: str = ""
    subcategory: str = ""
    criteria: str = ""
    original: Optional[float] = None
    alternative: Optional[float] = None
    delta: Optional[float] = None
    reason: str = ""


@dataclass
class CostEvaluation:
    """비용 평가 데이터."""
    idea_initial_original: Optional[float] = None
    idea_initial_alternative: Optional[float] = None
    idea_lifecycle_original: Optional[float] = None
    idea_lifecycle_alternative: Optional[float] = None
    project_initial_original: Optional[float] = None
    project_initial_alternative: Optional[float] = None
    project_maintenance_original: Optional[float] = None
    project_maintenance_alternative: Optional[float] = None
    project_lifecycle_original: Optional[float] = None
    project_lifecycle_alternative: Optional[float] = None
    savings_amount: Optional[float] = None
    savings_initial_rate: Optional[float] = None
    savings_lifecycle_rate: Optional[float] = None


@dataclass
class ValueEvaluation:
    """가치 평가 데이터."""
    performance_original: Optional[float] = None
    performance_alternative: Optional[float] = None
    performance_change_rate: Optional[float] = None
    cost_change_rate: Optional[float] = None
    relative_lcc: Optional[float] = None
    value_original: Optional[float] = None
    value_alternative: Optional[float] = None
    value_change_rate: Optional[float] = None
    value_type: str = ""


@dataclass
class AlternativeData:
    """VE 대안 1건의 전체 추출 데이터."""
    alt_number: int = 0
    location: str = ""
    proposal_title: str = ""
    original: DiagramData = field(default_factory=DiagramData)
    alternative: DiagramData = field(default_factory=DiagramData)
    characteristics: Characteristics = field(default_factory=Characteristics)
    performance_scores: list = field(default_factory=list)
    cost_evaluation: CostEvaluation = field(default_factory=CostEvaluation)
    value_evaluation: ValueEvaluation = field(default_factory=ValueEvaluation)
    value_chart_image_path: str = ""
    analysis_summary: str = ""
    page_left: int = 0
    page_right: int = 0


def validate_alternative(data: AlternativeData) -> dict:
    """
    대안 데이터의 완성도를 검증합니다.

    Returns:
        {"valid": bool, "completeness": float, "missing": list, "warnings": list}
    """
    missing = []
    warnings = []

    # 필수 필드 검증
    if not data.alt_number:
        missing.append("alt_number")
    if not data.proposal_title:
        missing.append("proposal_title")
    if not data.original.description:
        missing.append("original.description")
    if not data.alternative.description:
        missing.append("alternative.description")

    # 이미지 경로 검증
    if not data.original.diagram_image_path:
        missing.append("original.diagram_image_path")
    if not data.alternative.diagram_image_path:
        missing.append("alternative.diagram_image_path")

    # 성능 점수 검증
    if not data.performance_scores:
        missing.append("performance_scores")

    # 비용 검증: 초비비용 + 유지관리비 ≈ 생애주기비용
    ce = data.cost_evaluation
    if (ce.project_initial_original is not None and
        ce.project_maintenance_original is not None and
        ce.project_lifecycle_original is not None):
        expected = ce.project_initial_original + ce.project_maintenance_original
        if abs(expected - ce.project_lifecycle_original) > 1.0:
            warnings.append(
                f"Cost mismatch: {ce.project_initial_original} + "
                f"{ce.project_maintenance_original} != {ce.project_lifecycle_original}"
            )

    # 완성도 계산 (총 10개 주요 필드)
    total_fields = 10
    filled = total_fields - len(missing)
    completeness = filled / total_fields

    return {
        "valid": len(missing) == 0,
        "completeness": round(completeness, 2),
        "missing": missing,
        "warnings": warnings,
    }

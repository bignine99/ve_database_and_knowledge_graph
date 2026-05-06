"""
VE Database Development - Unified Extraction Pipeline
======================================================
단일 대안 스프레드(2페이지)에서 모든 데이터를 추출하여
AlternativeData 구조체를 생성하는 통합 파이프라인.

추출 순서:
  1. 텍스트 추출 (좌측: 헤더/설명/장단점, 우측: 분석결과)
  2. 테이블 데이터 추출 (우측: 성능/비용/가치)
  3. 이미지 추출 (좌측: 원안/대안 개요도, 우측: 가치비교 차트)
"""

import json
import traceback
from pathlib import Path
from typing import Optional
from dataclasses import asdict

from src.config import EXTRACTED_DIR, IMAGES_DIR, ensure_directories
from src.schemas import (
    AlternativeData, DiagramData, Characteristics,
    PerformanceScore, CostEvaluation, ValueEvaluation,
    validate_alternative,
)
from src.text_extractor import extract_text_from_spread
from src.table_extractor import extract_tables_from_right_page
from src.image_extractor import extract_images_from_spread


def extract_single_alternative(
    pdf_path: Path,
    spread: dict,
    extract_images: bool = True,
) -> AlternativeData:
    """
    단일 대안 스프레드(2페이지)에서 전체 데이터를 추출합니다.

    Args:
        pdf_path: PDF 파일 경로
        spread: detect_alternative_pages()에서 반환된 스프레드 정보
        extract_images: 이미지 추출 여부 (배치 시 건너뛸 수 있음)

    Returns:
        AlternativeData — 대안 1건의 전체 추출 데이터
    """
    alt_label = spread["alt_label"]
    data = AlternativeData()

    # ── 1. 텍스트 추출 ──
    try:
        text_data = extract_text_from_spread(pdf_path, spread)
        data.alt_number = text_data["alt_number"]
        data.location = text_data.get("location", "")
        data.proposal_title = text_data.get("proposal_title", "")
        data.original = DiagramData(description=text_data.get("original_description", ""))
        data.alternative = DiagramData(description=text_data.get("alternative_description", ""))
        data.characteristics = Characteristics(
            advantages=text_data.get("advantages", ""),
            disadvantages=text_data.get("disadvantages", ""),
            implementation_notes=text_data.get("implementation_notes", ""),
        )
        data.analysis_summary = text_data.get("analysis_summary", "")
    except Exception as e:
        print(f"  [WARN] Text extraction failed for {alt_label}: {e}")
        traceback.print_exc()

    # ── 2. 테이블 데이터 추출 ──
    try:
        table_data = extract_tables_from_right_page(pdf_path, spread["right_idx"])
        data.performance_scores = table_data["performance_scores"]
        data.cost_evaluation = table_data["cost_evaluation"]
        data.value_evaluation = table_data["value_evaluation"]
        # 분석결과가 text_extractor에서 비어있으면 table_extractor에서 보완
        if not data.analysis_summary and table_data.get("analysis_summary"):
            data.analysis_summary = table_data["analysis_summary"]
    except Exception as e:
        print(f"  [WARN] Table extraction failed for {alt_label}: {e}")
        traceback.print_exc()

    # ── 3. 이미지 추출 ──
    if extract_images:
        try:
            image_data = extract_images_from_spread(pdf_path, spread)
            if image_data.get("original_diagram"):
                data.original.diagram_image_path = str(image_data["original_diagram"])
            if image_data.get("alternative_diagram"):
                data.alternative.diagram_image_path = str(image_data["alternative_diagram"])
            if image_data.get("value_chart"):
                data.value_chart_image_path = str(image_data["value_chart"])
        except Exception as e:
            print(f"  [WARN] Image extraction failed for {alt_label}: {e}")
            traceback.print_exc()

    # ── 4. 페이지 정보 ──
    data.page_left = spread.get("left_page", 0)
    data.page_right = spread.get("right_page", 0)

    # ── 5. 가치 유형 보완 (분석결과에서 추출 가능) ──
    if not data.value_evaluation.value_type and data.analysis_summary:
        data.value_evaluation.value_type = _extract_value_type_from_summary(
            data.analysis_summary
        )

    return data


def alternative_to_dict(data: AlternativeData) -> dict:
    """AlternativeData를 직렬화 가능한 dict로 변환합니다."""
    d = asdict(data)
    # performance_scores는 dataclass list이므로 이미 dict화됨
    return d


def save_alternative_json(
    data: AlternativeData,
    output_dir: Path = None,
) -> Path:
    """추출된 대안 데이터를 JSON 파일로 저장합니다."""
    if output_dir is None:
        output_dir = EXTRACTED_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"alt_{data.alt_number:03d}.json"
    output_path = output_dir / filename

    d = alternative_to_dict(data)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

    return output_path


def _extract_value_type_from_summary(summary: str) -> str:
    """분석결과 요약에서 가치유형을 추출합니다."""
    type_patterns = {
        "가치혁신형": "가치혁신형",
        "비용절감형": "비용절감형",
        "성능향상형": "성능향상형",
        "성능강조형": "성능강조형",
        "기능향상형": "기능향상형",
    }
    for pattern, value_type in type_patterns.items():
        if pattern in summary:
            return value_type
    return ""


if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    from src.pdf_processor import get_pdf_path, detect_alternative_pages

    ensure_directories()
    pdf_path = get_pdf_path()
    spreads = detect_alternative_pages(pdf_path)

    # E2E 테스트: 대안-16
    test_spread = None
    for s in spreads:
        if "16" in s["alt_label"]:
            test_spread = s
            break

    if test_spread:
        print(f"=== E2E Pipeline Test: {test_spread['alt_label']} ===")
        print(f"  Pages: {test_spread['left_page']}-{test_spread['right_page']}")

        data = extract_single_alternative(pdf_path, test_spread)

        # 검증
        validation = validate_alternative(data)
        print(f"\n=== Validation ===")
        print(f"  Valid: {validation['valid']}")
        print(f"  Completeness: {validation['completeness']}")
        if validation['missing']:
            print(f"  Missing: {validation['missing']}")
        if validation['warnings']:
            print(f"  Warnings: {validation['warnings']}")

        # 결과 출력
        print(f"\n=== Extracted Data ===")
        print(f"  alt_number: {data.alt_number}")
        print(f"  location: {data.location}")
        print(f"  proposal_title: {data.proposal_title}")
        print(f"  original.description: {data.original.description[:60]}...")
        print(f"  alternative.description: {data.alternative.description[:60]}...")
        print(f"  advantages: {data.characteristics.advantages}")
        print(f"  disadvantages: {data.characteristics.disadvantages}")
        print(f"  performance_scores: {len(data.performance_scores)} items")
        if data.performance_scores:
            total_orig = sum(ps.original or 0 for ps in data.performance_scores)
            total_alt = sum(ps.alternative or 0 for ps in data.performance_scores)
            print(f"    total: orig={total_orig:.2f} alt={total_alt:.2f}")
        print(f"  cost.project_initial: {data.cost_evaluation.project_initial_original} / {data.cost_evaluation.project_initial_alternative}")
        print(f"  value.performance: {data.value_evaluation.performance_original} / {data.value_evaluation.performance_alternative}")
        print(f"  value.value_type: {data.value_evaluation.value_type}")
        print(f"  original.diagram: {data.original.diagram_image_path}")
        print(f"  alternative.diagram: {data.alternative.diagram_image_path}")
        print(f"  value_chart: {data.value_chart_image_path}")
        print(f"  analysis: {data.analysis_summary[:80]}...")

        # JSON 저장
        json_path = save_alternative_json(data)
        print(f"\n  Saved to: {json_path}")

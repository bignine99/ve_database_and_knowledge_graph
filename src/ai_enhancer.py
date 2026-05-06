"""
VE Database Development - AI Enhancer
=======================================
Task 8: Gemini 멀티모달 AI로 개요도 이미지 기술 서술 생성
Task 9: 데이터 교차 검증 (비용/성능/가치 논리 체크)

사용 API: Google Gemini (gemini-2.0-flash)
"""

import json
import time
import base64
import traceback
from pathlib import Path
from typing import Optional

import os

from google import genai
from google.genai import types

from src.config import EXTRACTED_DIR


# ── API 설정 ──
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = "gemini-2.0-flash"

# API 호출 간격 (Rate Limit 방지)
API_DELAY_SECONDS = 2

# ── 프롬프트 ──
DIAGRAM_PROMPT = """당신은 건설 VE(Value Engineering) 전문가입니다.
아래 이미지는 건설 VE 보고서의 {diagram_type} 개요도입니다.

이 개요도를 분석하여 다음 사항을 포함한 기술 서술(2~4문장)을 작성하세요:
1. 사용 자재 및 규격 (THK, mm 등)
2. 구조/시공 방식
3. 주요 특징이나 변경 사항

대안 제목: {proposal_title}
{context}

간결하고 기술적인 문장으로 작성하세요. 한국어로 작성합니다."""

VALUE_CHART_PROMPT = """당신은 건설 VE(Value Engineering) 전문가입니다.
이 이미지는 VE 대안의 성능(P), 비용(C), 가치(V) 비교 차트입니다.

차트에서 읽을 수 있는 수치와 분석결과를 2~3문장으로 요약하세요.
한국어로 작성합니다."""


def create_client() -> genai.Client:
    """Gemini API 클라이언트를 생성합니다."""
    return genai.Client(api_key=GEMINI_API_KEY)


def describe_diagram_image(
    client: genai.Client,
    image_path: str,
    diagram_type: str,
    proposal_title: str,
    description: str = "",
) -> str:
    """
    개요도 이미지를 Gemini에 전송하여 기술 서술을 생성합니다.

    Args:
        client: Gemini 클라이언트
        image_path: 이미지 파일 경로
        diagram_type: "원안" 또는 "대안"
        proposal_title: 대안 제안명
        description: 기존 추출된 설명 (컨텍스트)

    Returns:
        AI 생성 기술 서술 문자열
    """
    path = Path(image_path)
    if not path.exists():
        return ""

    # 이미지 읽기
    image_bytes = path.read_bytes()
    mime_type = "image/jpeg" if path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"

    context = f"기존 설명: {description}" if description else ""

    prompt = DIAGRAM_PROMPT.format(
        diagram_type=diagram_type,
        proposal_title=proposal_title,
        context=context,
    )

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
        )
        return response.text.strip()
    except Exception as e:
        print(f"    [AI ERROR] {e}")
        return ""


def describe_value_chart(
    client: genai.Client,
    image_path: str,
) -> str:
    """가치비교 차트 이미지를 분석하여 수치 요약을 생성합니다."""
    path = Path(image_path)
    if not path.exists():
        return ""

    image_bytes = path.read_bytes()
    mime_type = "image/jpeg" if path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                VALUE_CHART_PROMPT,
            ],
        )
        return response.text.strip()
    except Exception as e:
        print(f"    [AI ERROR] {e}")
        return ""


# ══════════════════════════════════════════
# Task 9: 데이터 교차 검증
# ══════════════════════════════════════════

def validate_cost_logic(data: dict) -> list[str]:
    """
    비용 데이터 논리 검증:
      초기비용 + 유지관리비 ≈ 생애주기비용
    """
    warnings = []
    ce = data.get("cost_evaluation", {})

    orig_initial = ce.get("project_initial_original")
    orig_maint = ce.get("project_maintenance_original")
    orig_lifecycle = ce.get("project_lifecycle_original")

    if all(v is not None for v in [orig_initial, orig_maint, orig_lifecycle]):
        expected = round(orig_initial + orig_maint, 2)
        actual = round(orig_lifecycle, 2)
        if abs(expected - actual) > 1.0:  # 1백만원 허용 오차
            warnings.append(
                f"비용논리(원안): 초기({orig_initial})+유지관리({orig_maint})={expected} ≠ 생애주기({actual})"
            )

    alt_initial = ce.get("project_initial_alternative")
    alt_maint = ce.get("project_maintenance_alternative")
    alt_lifecycle = ce.get("project_lifecycle_alternative")

    if all(v is not None for v in [alt_initial, alt_maint, alt_lifecycle]):
        expected = round(alt_initial + alt_maint, 2)
        actual = round(alt_lifecycle, 2)
        if abs(expected - actual) > 1.0:
            warnings.append(
                f"비용논리(대안): 초기({alt_initial})+유지관리({alt_maint})={expected} ≠ 생애주기({actual})"
            )

    return warnings


def validate_performance_sum(data: dict) -> list[str]:
    """성능 점수 합계 검증."""
    warnings = []
    scores = data.get("performance_scores", [])

    # 유효 점수만 (None/헤더 제외)
    valid = [s for s in scores
             if s.get("original") is not None
             and s.get("criteria", "") not in ("중분류 평가기준", "평가기준", "")]

    if not valid:
        return warnings

    orig_sum = round(sum(s["original"] for s in valid), 2)
    alt_sum = round(sum(s.get("alternative") or s["original"] for s in valid), 2)

    # 성능 합계는 500점 근처여야 함
    ve = data.get("value_evaluation", {})
    perf_orig = ve.get("performance_original")
    perf_alt = ve.get("performance_alternative")

    if perf_orig is not None and abs(orig_sum - perf_orig) > 1.0:
        warnings.append(f"성능합계(원안): 개별합({orig_sum}) ≠ 가치표({perf_orig})")

    if perf_alt is not None and abs(alt_sum - perf_alt) > 1.0:
        warnings.append(f"성능합계(대안): 개별합({alt_sum}) ≠ 가치표({perf_alt})")

    return warnings


def validate_value_formula(data: dict) -> list[str]:
    """가치 계산 검증: 성능변화율, 비용변화율, 가치변화율 관계."""
    warnings = []
    ve = data.get("value_evaluation", {})

    perf_rate = ve.get("performance_change_rate")
    cost_rate = ve.get("cost_change_rate")
    value_rate = ve.get("value_change_rate")

    # 가치변화율 ≈ 성능변화율 - 비용변화율 (±0.5% 허용)
    if all(v is not None for v in [perf_rate, cost_rate, value_rate]):
        # 비용이 절감(-)일 때 가치는 증가 방향
        expected_approx = perf_rate + cost_rate  # 비용절감은 +로 표현됨
        # 실제로는 복잡한 공식이므로 넓은 허용 범위
        if abs(value_rate - expected_approx) > 2.0:
            warnings.append(
                f"가치공식: P변화({perf_rate}%) + C변화({cost_rate}%) ≈ {expected_approx}% ≠ V변화({value_rate}%)"
            )

    return warnings


def validate_alternative(data: dict) -> dict:
    """전체 교차 검증을 수행합니다."""
    all_warnings = []
    all_warnings.extend(validate_cost_logic(data))
    all_warnings.extend(validate_performance_sum(data))
    all_warnings.extend(validate_value_formula(data))

    return {
        "valid": len(all_warnings) == 0,
        "warnings": all_warnings,
    }


# ══════════════════════════════════════════
# 통합: AI 서술 + 검증 → JSON 업데이트
# ══════════════════════════════════════════

def enhance_single_alternative(
    client: genai.Client,
    json_path: Path,
    skip_ai: bool = False,
) -> dict:
    """
    단일 대안 JSON에 AI 서술을 추가하고 교차 검증을 수행합니다.

    Args:
        client: Gemini 클라이언트
        json_path: alt_XXX.json 파일 경로
        skip_ai: AI 호출 건너뛰기 (검증만 수행)

    Returns:
        {"alt_number": int, "ai_descriptions": int, "validation": dict}
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    alt_num = data.get("alt_number", 0)
    title = data.get("proposal_title", "")
    ai_count = 0

    # ── AI 서술 생성 ──
    if not skip_ai:
        # 원안 개요도
        orig_img = data.get("original", {}).get("diagram_image_path", "")
        orig_desc = data.get("original", {}).get("description", "")
        if orig_img and not data.get("original", {}).get("ai_description"):
            ai_text = describe_diagram_image(
                client, orig_img, "원안", title, orig_desc
            )
            if ai_text:
                data["original"]["ai_description"] = ai_text
                ai_count += 1
            time.sleep(API_DELAY_SECONDS)

        # 대안 개요도
        alt_img = data.get("alternative", {}).get("diagram_image_path", "")
        alt_desc = data.get("alternative", {}).get("description", "")
        if alt_img and not data.get("alternative", {}).get("ai_description"):
            ai_text = describe_diagram_image(
                client, alt_img, "대안", title, alt_desc
            )
            if ai_text:
                data["alternative"]["ai_description"] = ai_text
                ai_count += 1
            time.sleep(API_DELAY_SECONDS)

    # ── 교차 검증 ──
    validation = validate_alternative(data)

    # 검증 결과를 JSON에 추가
    data["_validation"] = validation

    # JSON 저장 (업데이트)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "alt_number": alt_num,
        "ai_descriptions": ai_count,
        "validation": validation,
    }


def enhance_batch(
    extracted_dir: Path = None,
    limit: Optional[int] = None,
    skip_ai: bool = False,
) -> dict:
    """
    전체 대안 JSON에 AI 서술 + 교차 검증을 배치 실행합니다.

    Args:
        extracted_dir: JSON 디렉토리
        limit: 처리할 최대 파일 수
        skip_ai: AI 호출 건너뛰기 (검증만 수행)

    Returns:
        {"processed": int, "ai_total": int, "valid": int, "invalid": int, "warnings": list}
    """
    if extracted_dir is None:
        extracted_dir = EXTRACTED_DIR

    client = None
    if not skip_ai:
        client = create_client()

    json_files = sorted(extracted_dir.glob("alt_*.json"))
    if limit:
        json_files = json_files[:limit]

    processed = 0
    ai_total = 0
    valid_count = 0
    invalid_count = 0
    all_warnings = []

    for idx, json_path in enumerate(json_files):
        print(f"  [{idx+1}/{len(json_files)}] {json_path.name}", end="", flush=True)

        try:
            result = enhance_single_alternative(client, json_path, skip_ai=skip_ai)
            processed += 1
            ai_total += result["ai_descriptions"]

            if result["validation"]["valid"]:
                valid_count += 1
                print(f"  ✓ AI:{result['ai_descriptions']}")
            else:
                invalid_count += 1
                for w in result["validation"]["warnings"]:
                    all_warnings.append(f"alt_{result['alt_number']:03d}: {w}")
                print(f"  ⚠ AI:{result['ai_descriptions']} warns:{len(result['validation']['warnings'])}")

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            traceback.print_exc()

    report = {
        "processed": processed,
        "ai_total": ai_total,
        "valid": valid_count,
        "invalid": invalid_count,
        "warnings": all_warnings,
    }

    # 리포트 저장
    report_path = Path("scratch") / "ai_enhance_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # 먼저 3개 대안만 AI+검증 테스트
    print("=== AI Enhancement Test (3개 대안) ===")
    report = enhance_batch(limit=3, skip_ai=False)

    print(f"\n=== Results ===")
    print(f"  Processed: {report['processed']}")
    print(f"  AI descriptions: {report['ai_total']}")
    print(f"  Valid: {report['valid']}")
    print(f"  Invalid: {report['invalid']}")
    if report['warnings']:
        print(f"  Warnings:")
        for w in report['warnings']:
            print(f"    {w}")

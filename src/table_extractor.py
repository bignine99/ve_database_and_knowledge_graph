"""
VE Database Development - Table Extractor
============================================
우측 페이지에서 성능/비용/가치 평가 데이터를 추출합니다.

추출 전략:
  pdfplumber의 word-level 추출을 사용하여 x/y 좌표 기반으로
  테이블 셀을 매핑합니다. 테이블 구조가 정형화되어 있으므로
  y좌표 범위로 영역을 구분하고, x좌표로 컬럼을 식별합니다.
"""

import pdfplumber
import re
from pathlib import Path
from typing import Optional

from src.schemas import PerformanceScore, CostEvaluation, ValueEvaluation


# ── 우측 페이지 영역 구분 (y좌표 기준, PDF points) ──
# 이 값들은 대안-16 분석 기준이며, 약간의 변동을 허용합니다
PERF_TABLE_Y_START = 90
PERF_TABLE_Y_END = 520
COST_VALUE_Y_START = 520
COST_VALUE_Y_END = 760

# ── 성능 테이블 x좌표 컬럼 범위 ──
PERF_COL_RANGES = {
    "category":    (50, 120),
    "subcategory": (120, 170),
    "criteria":    (120, 290),
    "original":    (290, 330),
    "alternative": (330, 370),
    "delta":       (370, 440),
    "reason":      (440, 540),
}

# ── 비용 테이블 x좌표 컬럼 범위 ──
COST_COL_RANGES = {
    "label":       (55, 155),
    "original":    (155, 220),
    "alternative": (220, 280),
}

# ── 가치 테이블 x좌표 컬럼 범위 ──
VALUE_COL_RANGES = {
    "label":  (280, 355),
    "value":  (355, 420),
}


def extract_tables_from_right_page(
    pdf_path: Path,
    page_idx: int
) -> dict:
    """
    우측 페이지에서 성능/비용/가치 평가 데이터를 추출합니다.

    Args:
        pdf_path: PDF 파일 경로
        page_idx: 0-indexed 우측 페이지 번호

    Returns:
        {
            "performance_scores": [PerformanceScore, ...],
            "cost_evaluation": CostEvaluation,
            "value_evaluation": ValueEvaluation,
            "analysis_summary": str,
        }
    """
    pdf = pdfplumber.open(str(pdf_path))
    page = pdf.pages[page_idx]

    words = page.extract_words(
        x_tolerance=3,
        y_tolerance=3,
        keep_blank_chars=True,
    )

    # 성능 평가 추출
    performance_scores = _extract_performance_scores(words)

    # 비용/가치 평가 추출
    cost_evaluation = _extract_cost_evaluation(words)
    value_evaluation = _extract_value_evaluation(words)

    # 분석결과 요약 추출
    analysis_summary = _extract_analysis_summary(words)

    pdf.close()

    return {
        "performance_scores": performance_scores,
        "cost_evaluation": cost_evaluation,
        "value_evaluation": value_evaluation,
        "analysis_summary": analysis_summary,
    }


def _extract_performance_scores(words: list) -> list[PerformanceScore]:
    """성능 세부 평가결과 테이블에서 각 평가 항목을 추출합니다."""
    # 성능 테이블 영역의 단어만 필터링
    perf_words = [w for w in words
                  if PERF_TABLE_Y_START < w["top"] < PERF_TABLE_Y_END]

    if not perf_words:
        return []

    # y좌표로 행을 그룹핑 (±3pt 오차 허용)
    rows = _group_words_by_y(perf_words, tolerance=5)

    # 헤더 행 건너뛰기 (처음 2행은 대분류/원안/대안 헤더)
    data_rows = rows[2:] if len(rows) > 2 else []

    scores = []
    current_category = ""

    for row_words in data_rows:
        # 대분류 (category) 감지
        cat_words = [w for w in row_words
                     if PERF_COL_RANGES["category"][0] <= w["x0"] < PERF_COL_RANGES["category"][1]]
        if cat_words:
            cat_text = " ".join(w["text"] for w in cat_words).strip()
            if cat_text and cat_text != "합계":
                current_category = cat_text

        # 합계 행 건너뛰기
        row_text = " ".join(w["text"] for w in row_words)
        if "합계" in row_text:
            continue

        # 평가기준 (criteria)
        criteria_words = [w for w in row_words
                         if PERF_COL_RANGES["criteria"][0] <= w["x0"] < PERF_COL_RANGES["criteria"][1]]
        criteria = " ".join(w["text"] for w in criteria_words).strip()
        if not criteria:
            continue

        # 원안/대안 점수
        original = _get_float_in_range(row_words, PERF_COL_RANGES["original"])
        alternative = _get_float_in_range(row_words, PERF_COL_RANGES["alternative"])

        # 증감
        delta_words = [w for w in row_words
                      if PERF_COL_RANGES["delta"][0] <= w["x0"] < PERF_COL_RANGES["delta"][1]]
        delta = _parse_delta(" ".join(w["text"] for w in delta_words).strip())

        # 증감사유
        reason_words = [w for w in row_words
                       if PERF_COL_RANGES["reason"][0] <= w["x0"]]
        reason = " ".join(w["text"] for w in reason_words).strip()

        scores.append(PerformanceScore(
            category=current_category,
            subcategory="",
            criteria=criteria,
            original=original,
            alternative=alternative,
            delta=delta,
            reason=reason if reason != "-" else "",
        ))

    return scores


def _extract_cost_evaluation(words: list) -> CostEvaluation:
    """비용 세부 평가결과를 추출합니다."""
    cost_words = [w for w in words
                  if COST_VALUE_Y_START < w["top"] < COST_VALUE_Y_END]

    # y좌표로 행을 그룹핑
    rows = _group_words_by_y(cost_words, tolerance=5)

    ce = CostEvaluation()

    for row_words in rows:
        row_text = " ".join(w["text"] for w in row_words)

        # 비용 테이블 왼쪽 영역 (x0 < 280)
        left_words = [w for w in row_words if w["x0"] < 280]
        left_text = " ".join(w["text"] for w in left_words)

        # 숫자값 추출 (x좌표 기반)
        original = _get_float_in_range(row_words, COST_COL_RANGES["original"])
        alternative = _get_float_in_range(row_words, COST_COL_RANGES["alternative"])

        # 아이디어 비용
        if "초기비용" in left_text and "아이디어" in _get_context_above(rows, row_words):
            ce.idea_initial_original = original
            ce.idea_initial_alternative = alternative
        elif "생애주기비용" in left_text and "아이디어" in _get_context_above(rows, row_words):
            ce.idea_lifecycle_original = original
            ce.idea_lifecycle_alternative = alternative

        # 프로젝트 비용 (큰 숫자로 구분)
        elif "초기비용" in left_text and original and original > 1000:
            ce.project_initial_original = original
            ce.project_initial_alternative = alternative
        elif "유지관리비용" in left_text:
            ce.project_maintenance_original = original
            ce.project_maintenance_alternative = alternative
        elif "생애주기비용" in left_text and original and original > 1000:
            ce.project_lifecycle_original = original
            ce.project_lifecycle_alternative = alternative

        # 절감액
        elif "절감액" in _get_context_above(rows, row_words):
            if "초기비용" in left_text:
                # 절감액은 하나의 숫자만 있을 수 있음
                all_nums = _get_all_floats_in_range(row_words, (155, 280))
                if all_nums:
                    ce.savings_amount = all_nums[-1]  # 마지막 숫자

        # 절감율
        pct_words = [w for w in row_words if "%" in w["text"]]
        if pct_words and "절감율" in _get_context_above(rows, row_words):
            pct_val = _parse_percentage(pct_words[0]["text"])
            if "초기비용" in left_text:
                ce.savings_initial_rate = pct_val
            elif "생애주기비용" in left_text:
                ce.savings_lifecycle_rate = pct_val

    return ce


def _extract_value_evaluation(words: list) -> ValueEvaluation:
    """가치 세부 평가결과를 추출합니다."""
    # 우측 영역 (x > 280)의 단어만 사용
    value_words = [w for w in words
                   if COST_VALUE_Y_START < w["top"] < COST_VALUE_Y_END
                   and w["x0"] >= 280]

    rows = _group_words_by_y(value_words, tolerance=5)

    ve = ValueEvaluation()

    for row_words in rows:
        row_text = " ".join(w["text"] for w in row_words)

        # 숫자값
        nums = _get_all_floats_in_range(row_words, VALUE_COL_RANGES["value"])

        if "성능(P)" in row_text or "성능" in row_text:
            continue  # 헤더

        if "원안" in row_text and nums:
            # 원안 값: 성능 원안 또는 가치 원안
            if ve.performance_original is None:
                ve.performance_original = nums[0]
            elif ve.value_original is None:
                ve.value_original = nums[0]

        elif "대안" in row_text and nums:
            if ve.performance_alternative is None:
                ve.performance_alternative = nums[0]
            elif ve.value_alternative is None:
                ve.value_alternative = nums[0]

        elif "증가율" in row_text:
            pct = _find_percentage(row_words)
            if pct is not None:
                if ve.performance_change_rate is None:
                    ve.performance_change_rate = pct
                elif ve.value_change_rate is None:
                    ve.value_change_rate = pct

        elif "절감율" in row_text:
            pct = _find_percentage(row_words)
            if pct is not None:
                ve.cost_change_rate = pct

        elif "상대LCC" in row_text and nums:
            ve.relative_lcc = nums[0]

        elif "가치유형" in row_text:
            # 가치유형 텍스트 (가치혁신형 등)
            vtype_text = row_text.replace("가치유형", "").strip()
            ve.value_type = vtype_text if vtype_text else ""

    return ve


def _extract_analysis_summary(words: list) -> str:
    """분석결과 요약 텍스트를 추출합니다."""
    # 분석결과는 y > 750 영역에 위치
    summary_words = [w for w in words if w["top"] > 750]
    if not summary_words:
        return ""

    rows = _group_words_by_y(summary_words, tolerance=5)
    lines = []
    for row_words in rows:
        line = " ".join(w["text"] for w in row_words)
        lines.append(line.strip())

    return " ".join(lines)


# ──────────────────────────────────────
# 유틸리티 함수
# ──────────────────────────────────────

def _group_words_by_y(words: list, tolerance: float = 5) -> list[list]:
    """y좌표로 단어를 행으로 그룹핑합니다."""
    if not words:
        return []

    sorted_words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    rows = []
    current_row = [sorted_words[0]]
    current_y = sorted_words[0]["top"]

    for w in sorted_words[1:]:
        if abs(w["top"] - current_y) <= tolerance:
            current_row.append(w)
        else:
            rows.append(sorted(current_row, key=lambda w: w["x0"]))
            current_row = [w]
            current_y = w["top"]

    if current_row:
        rows.append(sorted(current_row, key=lambda w: w["x0"]))

    return rows


def _get_float_in_range(words: list, x_range: tuple) -> Optional[float]:
    """지정된 x좌표 범위 내에서 첫 번째 숫자를 추출합니다."""
    for w in words:
        if x_range[0] <= w["x0"] < x_range[1]:
            val = _parse_number(w["text"])
            if val is not None:
                return val
    return None


def _get_all_floats_in_range(words: list, x_range: tuple) -> list[float]:
    """지정된 x좌표 범위 내의 모든 숫자를 추출합니다."""
    nums = []
    for w in words:
        if x_range[0] <= w["x0"] < x_range[1]:
            val = _parse_number(w["text"])
            if val is not None:
                nums.append(val)
    return nums


def _parse_number(text: str) -> Optional[float]:
    """숫자 텍스트를 float으로 변환합니다. 콤마, 삼각형 기호 처리."""
    if not text or text.strip() in ("-", "", "–"):
        return None
    cleaned = text.strip().replace(",", "").replace("▽", "-").replace("△", "").replace("▲", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_delta(text: str) -> Optional[float]:
    """증감값을 파싱합니다. ▲3.57 → 3.57, ▽0.01 → -0.01"""
    if not text or text.strip() in ("-", ""):
        return None
    cleaned = text.strip().replace("▲", "").replace("△", "").replace("▽", "-").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_percentage(text: str) -> Optional[float]:
    """퍼센트 값을 파싱합니다. '0.71%' → 0.71"""
    if not text:
        return None
    cleaned = text.strip().replace("%", "").replace("▲", "").replace("▽", "-").replace("△", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _find_percentage(words: list) -> Optional[float]:
    """단어 리스트에서 퍼센트 값을 찾습니다."""
    for w in words:
        if "%" in w["text"]:
            return _parse_percentage(w["text"])
    return None


def _get_context_above(all_rows: list, current_row_words: list) -> str:
    """현재 행 위의 컨텍스트(카테고리 헤더)를 가져옵니다."""
    if not current_row_words:
        return ""
    current_y = current_row_words[0]["top"]
    context = []
    for row_words in all_rows:
        if row_words[0]["top"] < current_y:
            context.append(" ".join(w["text"] for w in row_words))
    return " ".join(context[-3:])  # 최근 3행만


if __name__ == "__main__":
    from src.pdf_processor import get_pdf_path, detect_alternative_pages

    pdf_path = get_pdf_path()
    spreads = detect_alternative_pages(pdf_path)

    # 대안-16 테스트 (right page idx = 167)
    test_spread = None
    for s in spreads:
        if "16" in s["alt_label"]:
            test_spread = s
            break

    if test_spread:
        print(f"Testing table extraction for {test_spread['alt_label']}")
        print(f"  Right page idx: {test_spread['right_idx']}")
        result = extract_tables_from_right_page(pdf_path, test_spread["right_idx"])

        print(f"\n  Performance scores: {len(result['performance_scores'])} items")
        for ps in result["performance_scores"][:5]:
            print(f"    {ps.category} | {ps.criteria} | "
                  f"orig={ps.original} alt={ps.alternative} delta={ps.delta}")
        if len(result["performance_scores"]) > 5:
            print(f"    ... ({len(result['performance_scores'])-5} more)")

        # 합계 확인
        total_orig = sum(ps.original or 0 for ps in result["performance_scores"])
        total_alt = sum(ps.alternative or 0 for ps in result["performance_scores"])
        print(f"    Total: orig={total_orig:.2f} alt={total_alt:.2f}")

        ce = result["cost_evaluation"]
        print(f"\n  Cost evaluation:")
        print(f"    Idea initial: {ce.idea_initial_original} / {ce.idea_initial_alternative}")
        print(f"    Project initial: {ce.project_initial_original} / {ce.project_initial_alternative}")
        print(f"    Project maintenance: {ce.project_maintenance_original} / {ce.project_maintenance_alternative}")
        print(f"    Project lifecycle: {ce.project_lifecycle_original} / {ce.project_lifecycle_alternative}")

        ve = result["value_evaluation"]
        print(f"\n  Value evaluation:")
        print(f"    Perf: {ve.performance_original} / {ve.performance_alternative} ({ve.performance_change_rate}%)")
        print(f"    Cost change: {ve.cost_change_rate}%, LCC: {ve.relative_lcc}")
        print(f"    Value: {ve.value_original} / {ve.value_alternative} ({ve.value_change_rate}%)")
        print(f"    Type: {ve.value_type}")

        print(f"\n  Analysis summary: {result['analysis_summary'][:100]}...")

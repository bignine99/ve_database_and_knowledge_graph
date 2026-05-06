"""
VE Database Development - Text Extractor
============================================
좌측 페이지에서 대안번호, 위치, 제안명, 원안/대안 설명, 장단점을 추출합니다.
우측 페이지에서 분석결과 요약 텍스트를 추출합니다.

추출 방식:
  PyMuPDF(fitz)의 get_text("dict")를 사용하여 텍스트 블록의
  y/x 좌표 기반으로 각 영역의 텍스트를 매핑합니다.
  (pdfplumber는 이 PDF의 한글 인코딩 처리에서 깨짐이 발생하여 fitz 사용)
"""

import fitz
import re
from pathlib import Path
from typing import Optional

from src.schemas import AlternativeData, DiagramData, Characteristics


# ── 좌측 페이지 영역 구분 (y좌표 기준, PDF points) ──
# 이 값들은 다수 대안 분석 기준이며, 약간의 변동을 허용합니다

# 헤더 영역 (대안번호 + 위치 + 제안명)
HEADER_Y_START = 85
HEADER_Y_END = 135

# 원안 설명 텍스트 영역
ORIGINAL_DESC_Y_START = 380
ORIGINAL_DESC_Y_END = 525

# 대안 설명 텍스트 영역
ALTERNATIVE_DESC_Y_START = 655
ALTERNATIVE_DESC_Y_END = 710

# 대안의 특성 (장점/단점/고려사항) 영역
CHARACTERISTICS_Y_START = 710
CHARACTERISTICS_Y_END = 810

# 특성 섹션 x좌표 구분
CHAR_ADVANTAGE_X_END = 250      # x < 250 → 장점
CHAR_DISADVANTAGE_X_START = 250  # 250 <= x < 420 → 단점
CHAR_CONSIDERATION_X_START = 420  # x >= 420 → 고려사항

# 페이지 번호 영역 (제외)
PAGE_NUM_Y_START = 810

# 섹션 제목 헤더 영역 (대안-01에만 존재하는 "4.6 대안별 분석결과" 등)
SECTION_TITLE_Y_END = 92


def extract_text_from_left_page(
    pdf_path: Path,
    page_idx: int,
) -> dict:
    """
    좌측 페이지에서 텍스트 데이터를 추출합니다.

    Args:
        pdf_path: PDF 파일 경로
        page_idx: 0-indexed 좌측 페이지 번호

    Returns:
        {
            "alt_number": int,
            "location": str,
            "proposal_title": str,
            "original_description": str,
            "alternative_description": str,
            "advantages": str,
            "disadvantages": str,
            "implementation_notes": str,
        }
    """
    doc = fitz.open(str(pdf_path))
    page = doc[page_idx]

    # 텍스트 블록 추출 (dict 모드: 위치 정보 포함)
    text_items = _extract_text_items(page)

    # 헤더 파싱: 대안번호, 위치, 제안명
    header_info = _parse_header(text_items)

    # 원안 설명 추출
    original_desc = _extract_description(
        text_items, ORIGINAL_DESC_Y_START, ORIGINAL_DESC_Y_END
    )

    # 대안 설명 추출
    alternative_desc = _extract_description(
        text_items, ALTERNATIVE_DESC_Y_START, ALTERNATIVE_DESC_Y_END
    )

    # 대안의 특성 (장점/단점/고려사항)
    characteristics = _extract_characteristics(text_items)

    doc.close()

    return {
        "alt_number": header_info["alt_number"],
        "location": header_info["location"],
        "proposal_title": header_info["proposal_title"],
        "original_description": original_desc,
        "alternative_description": alternative_desc,
        "advantages": characteristics["advantages"],
        "disadvantages": characteristics["disadvantages"],
        "implementation_notes": characteristics["implementation_notes"],
    }


def extract_analysis_summary_from_right_page(
    pdf_path: Path,
    page_idx: int,
) -> str:
    """
    우측 페이지 하단의 분석결과 요약 텍스트를 추출합니다.

    Args:
        pdf_path: PDF 파일 경로
        page_idx: 0-indexed 우측 페이지 번호

    Returns:
        분석결과 요약 텍스트 문자열
    """
    doc = fitz.open(str(pdf_path))
    page = doc[page_idx]

    text_items = _extract_text_items(page)

    # 분석결과는 y > 750 영역
    summary_items = [
        item for item in text_items
        if item["y"] > 750 and item["y"] < PAGE_NUM_Y_START
    ]

    doc.close()

    if not summary_items:
        return ""

    # y좌표로 정렬 후 합치기
    summary_items.sort(key=lambda item: (item["y"], item["x"]))
    lines = []
    current_y = -999
    current_line = ""
    for item in summary_items:
        if abs(item["y"] - current_y) > 5:
            if current_line.strip():
                lines.append(current_line.strip())
            current_line = item["text"]
            current_y = item["y"]
        else:
            current_line += " " + item["text"]
    if current_line.strip():
        lines.append(current_line.strip())

    return " ".join(lines)


# ──────────────────────────────────────
# 내부 함수
# ──────────────────────────────────────

def _extract_text_items(page: fitz.Page) -> list[dict]:
    """
    페이지에서 텍스트 항목을 y/x 좌표와 함께 추출합니다.

    Returns:
        [{"y": float, "x": float, "text": str, "font_size": float}, ...]
    """
    items = []
    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        if block.get("type") == 0:  # text block
            for line in block["lines"]:
                y = line["bbox"][1]
                x0 = line["bbox"][0]
                full_text = ""
                max_font_size = 0
                for span in line["spans"]:
                    full_text += span["text"]
                    if span["size"] > max_font_size:
                        max_font_size = span["size"]
                text = full_text.strip()
                if text:
                    items.append({
                        "y": round(y, 1),
                        "x": round(x0, 1),
                        "text": text,
                        "font_size": round(max_font_size, 1),
                    })
    return items


def _parse_header(text_items: list[dict]) -> dict:
    """
    헤더 영역에서 대안번호, 위치, 제안명을 파싱합니다.

    헤더 패턴:
    - 1행: "[대안-XX] (위치) 제안명..." 또는 "[대안-XX] 제안명..."
    - 2행: 제안명 연속 (긴 제안명의 경우)

    Returns:
        {"alt_number": int, "location": str, "proposal_title": str}
    """
    header_items = [
        item for item in text_items
        if HEADER_Y_START < item["y"] < HEADER_Y_END
    ]

    # "구분", "개요" 등 라벨은 제외
    header_items = [
        item for item in header_items
        if item["text"] not in ("구분", "개요", "4.6 대안별 분석결과")
        and not item["text"].startswith("4.")
    ]

    # y좌표로 정렬
    header_items.sort(key=lambda item: (item["y"], item["x"]))

    if not header_items:
        return {"alt_number": 0, "location": "", "proposal_title": ""}

    # 헤더 텍스트 합치기 (1~2행)
    lines = []
    current_y = -999
    current_line = ""
    for item in header_items:
        if abs(item["y"] - current_y) > 5:
            if current_line.strip():
                lines.append(current_line.strip())
            current_line = item["text"]
            current_y = item["y"]
        else:
            current_line += " " + item["text"]
    if current_line.strip():
        lines.append(current_line.strip())

    full_header = " ".join(lines)

    # 대안번호 추출: [대안-XX]
    alt_number = 0
    alt_match = re.search(r'\[대안[_\-](\d+)\]', full_header)
    if alt_match:
        alt_number = int(alt_match.group(1))

    # 위치 추출: (본청), (의회동) 등 — 대안번호 뒤 괄호
    location = ""
    loc_match = re.search(r'\]\s*\(([^)]+)\)', full_header)
    if loc_match:
        location = loc_match.group(1)

    # 제안명 추출: [대안-XX] (위치) 이후의 텍스트
    proposal_title = full_header
    # "[대안-XX]" 제거
    proposal_title = re.sub(r'\[대안[_\-]\d+\]\s*', '', proposal_title)
    # "(위치)" 제거
    if location:
        proposal_title = re.sub(r'\(' + re.escape(location) + r'\)\s*', '', proposal_title)
    proposal_title = proposal_title.strip()

    return {
        "alt_number": alt_number,
        "location": location,
        "proposal_title": proposal_title,
    }


def _extract_description(
    text_items: list[dict],
    y_start: float,
    y_end: float,
) -> str:
    """
    지정된 y좌표 범위에서 설명 텍스트를 추출합니다.
    레이블 텍스트("설", "명", "개", "요", "도" 등)를 제외합니다.
    """
    desc_items = [
        item for item in text_items
        if y_start < item["y"] < y_end
        and item["x"] > 100  # 좌측 레이블(설/명) 제외 (x < 100)
    ]

    if not desc_items:
        return ""

    # y좌표로 정렬 후 행별로 합치기
    desc_items.sort(key=lambda item: (item["y"], item["x"]))
    lines = []
    current_y = -999
    current_line = ""
    for item in desc_items:
        if abs(item["y"] - current_y) > 5:
            if current_line.strip():
                lines.append(current_line.strip())
            current_line = item["text"]
            current_y = item["y"]
        else:
            current_line += " " + item["text"]
    if current_line.strip():
        lines.append(current_line.strip())

    return "\n".join(lines)


def _extract_characteristics(text_items: list[dict]) -> dict:
    """
    대안의 특성(장점/단점/고려사항)을 x좌표로 구분하여 추출합니다.

    레이아웃:
    - x ~114: 장점 내용 (∙로 시작)
    - x ~255: 단점 내용 (∙로 시작)
    - x ~462: 고려사항 내용

    Returns:
        {"advantages": str, "disadvantages": str, "implementation_notes": str}
    """
    char_items = [
        item for item in text_items
        if CHARACTERISTICS_Y_START < item["y"] < PAGE_NUM_Y_START
    ]

    # 레이블 제외: "대안의", "특성", "장 점", "단 점", "이행 시 고려사항", 페이지 번호
    label_texts = {"대안의", "특성", "장 점", "단 점", "이행 시 고려사항"}
    char_items = [
        item for item in char_items
        if item["text"] not in label_texts
        and not re.match(r'^-\s*\d+\s*-$', item["text"])  # 페이지 번호
    ]

    advantages = []
    disadvantages = []
    implementation_notes = []

    for item in char_items:
        text = item["text"]
        x = item["x"]

        if x < CHAR_ADVANTAGE_X_END:
            advantages.append(text)
        elif x < CHAR_CONSIDERATION_X_START:
            disadvantages.append(text)
        else:
            implementation_notes.append(text)

    # "-" 만 있는 경우 제거
    def _clean_items(items: list) -> str:
        cleaned = [t for t in items if t.strip() != "-"]
        return "\n".join(cleaned)

    return {
        "advantages": _clean_items(advantages),
        "disadvantages": _clean_items(disadvantages),
        "implementation_notes": _clean_items(implementation_notes),
    }


def extract_text_from_spread(
    pdf_path: Path,
    spread: dict,
) -> dict:
    """
    2페이지 스프레드에서 모든 텍스트 데이터를 추출합니다.

    Args:
        pdf_path: PDF 파일 경로
        spread: {"alt_label", "left_idx", "right_idx", ...}

    Returns:
        좌측 + 우측 페이지의 결합된 텍스트 데이터
    """
    left_data = extract_text_from_left_page(pdf_path, spread["left_idx"])
    analysis = extract_analysis_summary_from_right_page(pdf_path, spread["right_idx"])

    left_data["analysis_summary"] = analysis
    return left_data


if __name__ == "__main__":
    import sys
    import io
    import json
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    from src.pdf_processor import get_pdf_path, detect_alternative_pages

    pdf_path = get_pdf_path()
    spreads = detect_alternative_pages(pdf_path)

    # 다수 대안 테스트
    test_indices = [0, 1, 15, 50, 80, 100]
    results = []

    for idx in test_indices:
        if idx >= len(spreads):
            continue
        spread = spreads[idx]
        print(f"Testing {spread['alt_label']}...")

        data = extract_text_from_spread(pdf_path, spread)
        results.append(data)

        print(f"  alt_number: {data['alt_number']}")
        print(f"  location: {data['location']}")
        print(f"  proposal_title: {data['proposal_title'][:60]}...")
        print(f"  original_desc: {data['original_description'][:60]}...")
        print(f"  alternative_desc: {data['alternative_description'][:60]}...")
        print(f"  advantages: {data['advantages'][:60]}...")
        print(f"  disadvantages: {data['disadvantages'][:40]}...")
        print(f"  impl_notes: {data['implementation_notes'][:40]}...")
        print(f"  analysis: {data['analysis_summary'][:60]}...")
        print()

    # JSON 저장
    with open("scratch/text_extract_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Results saved to scratch/text_extract_results.json")

"""
VE Database Development - PDF Processor
=========================================
PDF를 페이지 이미지로 변환하고, 2페이지 스프레드를 페어링합니다.
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional

from src.config import (
    RAW_DATA_DIR, PAGES_DIR, TARGET_DPI,
    PDF_START_PAGE, PDF_END_PAGE, PAGES_PER_SPREAD
)


def get_pdf_path() -> Path:
    """raw_data 디렉토리에서 VE 보고서 PDF 파일을 찾습니다."""
    pdfs = list(RAW_DATA_DIR.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDF files found in {RAW_DATA_DIR}")
    return pdfs[0]


def detect_alternative_pages(pdf_path: Path) -> list[dict]:
    """
    PDF에서 대안 2페이지 스프레드의 시작/끝 페이지를 자동 감지합니다.

    Returns:
        [{"alt_label": "대안-01", "left_idx": 136, "right_idx": 137,
          "left_page": 137, "right_page": 138}, ...]
    """
    doc = fitz.open(str(pdf_path))
    spreads = []

    # 검색 범위: PDF_START_PAGE ~ PDF_END_PAGE (1-indexed → 0-indexed)
    start_idx = PDF_START_PAGE - 1  # 129
    end_idx = min(PDF_END_PAGE, doc.page_count)  # 350

    i = start_idx
    while i < end_idx - 1:
        page = doc[i]
        text = page.get_text()

        # 좌측 페이지 판별: '[대안-' 패턴 + 개요/설명 키워드
        if '대안-' in text and ('개요' in text or '구분' in text):
            # 대안 번호 추출
            idx = text.find('대안-')
            label_end = text.find(']', idx) if ']' in text[idx:idx+15] else idx + 10
            alt_label = text[idx:label_end].strip()

            # 우측 페이지 검증: 성능 평가 키워드 확인
            next_page = doc[i + 1]
            next_text = next_page.get_text()
            if '성능' in next_text and '평가' in next_text:
                spreads.append({
                    "alt_label": alt_label,
                    "left_idx": i,           # 0-indexed
                    "right_idx": i + 1,      # 0-indexed
                    "left_page": i + 1,      # 1-indexed (PDF 표시 페이지)
                    "right_page": i + 2,     # 1-indexed
                })
                i += 2  # 다음 스프레드로 건너뜀
                continue

        i += 1

    doc.close()
    return spreads


def render_page_to_image(
    pdf_path: Path,
    page_idx: int,
    output_path: Path,
    dpi: int = TARGET_DPI
) -> Path:
    """
    PDF의 특정 페이지를 고해상도 PNG 이미지로 변환합니다.

    Args:
        pdf_path: PDF 파일 경로
        page_idx: 0-indexed 페이지 번호
        output_path: 출력 이미지 경로
        dpi: 해상도 (기본 300)

    Returns:
        저장된 이미지 파일 경로
    """
    doc = fitz.open(str(pdf_path))
    page = doc[page_idx]

    # DPI 기반 확대 비율 계산 (PDF 기본 72 DPI)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    # 렌더링
    pix = page.get_pixmap(matrix=matrix)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(output_path))

    doc.close()
    return output_path


def render_spread_pages(
    pdf_path: Path,
    spread: dict,
    output_dir: Path = None,
    dpi: int = TARGET_DPI
) -> dict:
    """
    2페이지 스프레드를 이미지로 변환합니다.

    Args:
        pdf_path: PDF 파일 경로
        spread: detect_alternative_pages()에서 반환된 스프레드 정보
        output_dir: 출력 디렉토리 (기본: PAGES_DIR)
        dpi: 해상도

    Returns:
        {"left_image": Path, "right_image": Path, "alt_label": str}
    """
    if output_dir is None:
        output_dir = PAGES_DIR

    alt_label = spread["alt_label"]
    # 파일명에 안전한 레이블 생성
    safe_label = alt_label.replace("-", "_").replace(" ", "_")

    left_path = output_dir / f"p{spread['left_page']:04d}_{safe_label}_left.png"
    right_path = output_dir / f"p{spread['right_page']:04d}_{safe_label}_right.png"

    render_page_to_image(pdf_path, spread["left_idx"], left_path, dpi)
    render_page_to_image(pdf_path, spread["right_idx"], right_path, dpi)

    return {
        "left_image": left_path,
        "right_image": right_path,
        "alt_label": alt_label,
    }


def render_all_spreads(
    pdf_path: Path = None,
    output_dir: Path = None,
    dpi: int = TARGET_DPI,
    limit: Optional[int] = None
) -> list[dict]:
    """
    모든 대안 스프레드를 이미지로 변환합니다.

    Args:
        pdf_path: PDF 경로 (None이면 자동 탐색)
        output_dir: 출력 디렉토리
        dpi: 해상도
        limit: 처리할 최대 스프레드 수 (테스트용)

    Returns:
        변환 결과 리스트
    """
    if pdf_path is None:
        pdf_path = get_pdf_path()
    if output_dir is None:
        output_dir = PAGES_DIR

    spreads = detect_alternative_pages(pdf_path)
    if limit:
        spreads = spreads[:limit]

    results = []
    for idx, spread in enumerate(spreads):
        print(f"  [{idx+1}/{len(spreads)}] Rendering {spread['alt_label']} "
              f"(p{spread['left_page']}-{spread['right_page']})...")
        result = render_spread_pages(pdf_path, spread, output_dir, dpi)
        results.append(result)

    return results


if __name__ == "__main__":
    pdf_path = get_pdf_path()
    print(f"PDF: {pdf_path.name}")

    spreads = detect_alternative_pages(pdf_path)
    print(f"Detected {len(spreads)} alternative spreads")
    print(f"  First: {spreads[0]['alt_label']} (p{spreads[0]['left_page']}-{spreads[0]['right_page']})")
    print(f"  Last:  {spreads[-1]['alt_label']} (p{spreads[-1]['left_page']}-{spreads[-1]['right_page']})")

    # 테스트: 첫 2개만 렌더링
    print("\nRendering first 2 spreads as test...")
    results = render_all_spreads(pdf_path, limit=2)
    for r in results:
        print(f"  {r['alt_label']}: {r['left_image'].name}, {r['right_image'].name}")

"""
VE Database Development - Image Extractor
============================================
PDF 페이지에서 개요도 이미지와 가치비교 차트를 추출합니다.

추출 대상 (페이지당):
  - 좌측 페이지: 원안 개요도, 대안 개요도
  - 우측 페이지: 가치비교 차트

추출 방식:
  1단계: PDF 내장 이미지 직접 추출 (xref 기반, 최고 품질)
  2단계: 실패 시 페이지 렌더링 후 좌표 기반 크롭 (fallback)
"""

import fitz
from pathlib import Path
from PIL import Image
import io

from src.config import IMAGES_DIR, TARGET_DPI


# ── 최소 크기 임계값 (작은 아이콘/장식 이미지 필터) ──
MIN_IMAGE_WIDTH = 100   # pixels
MIN_IMAGE_HEIGHT = 100  # pixels

# ── 우측 페이지 가치비교 차트 최소 크기 ──
MIN_CHART_WIDTH = 200
MIN_CHART_HEIGHT = 200


def extract_images_from_spread(
    pdf_path: Path,
    spread: dict,
    output_dir: Path = None
) -> dict:
    """
    2페이지 스프레드에서 개요도 및 차트 이미지를 추출합니다.

    Args:
        pdf_path: PDF 파일 경로
        spread: {"alt_label", "left_idx", "right_idx", ...}
        output_dir: 출력 디렉토리 (기본: IMAGES_DIR/{alt_label}/)

    Returns:
        {
            "original_diagram": Path or None,
            "alternative_diagram": Path or None,
            "value_chart": Path or None,
        }
    """
    alt_label = spread["alt_label"]
    safe_label = alt_label.replace("-", "_").replace(" ", "_")

    if output_dir is None:
        output_dir = IMAGES_DIR / safe_label
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    result = {
        "original_diagram": None,
        "alternative_diagram": None,
        "value_chart": None,
    }

    # ────────────────────────────────────
    # 좌측 페이지: 원안/대안 개요도 추출
    # ────────────────────────────────────
    left_page = doc[spread["left_idx"]]
    left_diagrams = _extract_diagrams_from_left_page(
        doc, left_page, safe_label, output_dir
    )
    result["original_diagram"] = left_diagrams.get("original")
    result["alternative_diagram"] = left_diagrams.get("alternative")

    # ────────────────────────────────────
    # 우측 페이지: 가치비교 차트 추출
    # ────────────────────────────────────
    right_page = doc[spread["right_idx"]]
    chart_path = _extract_chart_from_right_page(
        doc, right_page, safe_label, output_dir
    )
    result["value_chart"] = chart_path

    doc.close()
    return result


def _extract_diagrams_from_left_page(
    doc: fitz.Document,
    page: fitz.Page,
    safe_label: str,
    output_dir: Path
) -> dict:
    """
    좌측 페이지에서 원안/대안 개요도 이미지를 추출합니다.

    전략:
    - PDF 내장 이미지를 크기순 정렬
    - 상단 배너 이미지 (전체 너비) 제외
    - 나머지 중 큰 이미지 2개를 원안(위)/대안(아래)로 매핑
    """
    result = {}
    imgs = page.get_images(full=True)

    # 이미지 정보 수집 (위치 포함)
    candidates = []
    for img_info in imgs:
        xref = img_info[0]
        base_img = doc.extract_image(xref)
        w, h = base_img["width"], base_img["height"]

        # 작은 이미지와 배너(극단적 가로비) 필터링
        if w < MIN_IMAGE_WIDTH or h < MIN_IMAGE_HEIGHT:
            continue
        if w / h > 6:  # 상단 배너 (2479x293 같은)
            continue

        # 페이지 내 위치 확인
        rects = page.get_image_rects(img_info)
        if rects:
            y_pos = rects[0].y0  # 상단 y좌표
        else:
            y_pos = 9999

        candidates.append({
            "xref": xref,
            "width": w,
            "height": h,
            "ext": base_img["ext"],
            "data": base_img["image"],
            "y_pos": y_pos,
        })

    # y좌표로 정렬 (위에서 아래로)
    candidates.sort(key=lambda c: c["y_pos"])

    # 매핑: 첫 번째 = 원안, 두 번째 = 대안
    labels = ["original", "alternative"]
    for idx, candidate in enumerate(candidates[:2]):
        label = labels[idx] if idx < len(labels) else f"extra_{idx}"
        ext = candidate["ext"]
        out_path = output_dir / f"{safe_label}_{label}_diagram.{ext}"
        out_path.write_bytes(candidate["data"])
        result[label] = out_path

    return result


def _extract_chart_from_right_page(
    doc: fitz.Document,
    page: fitz.Page,
    safe_label: str,
    output_dir: Path
) -> Path | None:
    """
    우측 페이지에서 가치비교 차트 이미지를 추출합니다.

    전략:
    - 우측 페이지 하단 영역 (y > 500 pts)에 위치한 큰 이미지
    - 아이콘/장식 이미지 제외
    """
    imgs = page.get_images(full=True)

    best = None
    best_area = 0

    for img_info in imgs:
        xref = img_info[0]
        base_img = doc.extract_image(xref)
        w, h = base_img["width"], base_img["height"]

        if w < MIN_CHART_WIDTH or h < MIN_CHART_HEIGHT:
            continue
        if w / h > 6:  # 배너 제외
            continue

        # 위치 확인: 하단 영역
        rects = page.get_image_rects(img_info)
        if not rects:
            continue

        # 가장 큰 영역의 이미지 선택
        area = w * h
        if area > best_area:
            best_area = area
            best = {
                "xref": xref,
                "data": base_img["image"],
                "ext": base_img["ext"],
                "width": w,
                "height": h,
            }

    if best is None:
        return None

    ext = best["ext"]
    out_path = output_dir / f"{safe_label}_value_chart.{ext}"
    out_path.write_bytes(best["data"])
    return out_path


def crop_region_from_rendered_page(
    pdf_path: Path,
    page_idx: int,
    crop_box: tuple,
    output_path: Path,
    dpi: int = TARGET_DPI
) -> Path:
    """
    PDF 페이지를 렌더링 후 특정 영역을 크롭합니다 (fallback 방법).

    Args:
        pdf_path: PDF 파일 경로
        page_idx: 0-indexed 페이지 번호
        crop_box: (x0, y0, x1, y1) in PDF points
        output_path: 출력 이미지 경로
        dpi: 렌더링 해상도

    Returns:
        크롭된 이미지 파일 경로
    """
    doc = fitz.open(str(pdf_path))
    page = doc[page_idx]

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    # 크롭 영역을 PDF 좌표 → 픽셀 좌표로 변환
    clip = fitz.Rect(*crop_box)
    pix = page.get_pixmap(matrix=matrix, clip=clip)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(output_path))

    doc.close()
    return output_path


if __name__ == "__main__":
    from src.pdf_processor import get_pdf_path, detect_alternative_pages

    pdf_path = get_pdf_path()
    spreads = detect_alternative_pages(pdf_path)

    # 테스트: 대안-16 (user's example)
    # 대안-16은 인덱스 15 (0-based)
    test_spread = None
    for s in spreads:
        if "16" in s["alt_label"]:
            test_spread = s
            break

    if test_spread:
        print(f"Testing image extraction for {test_spread['alt_label']}")
        print(f"  Pages: {test_spread['left_page']}-{test_spread['right_page']}")
        result = extract_images_from_spread(pdf_path, test_spread)
        for key, path in result.items():
            if path:
                size_kb = path.stat().st_size / 1024
                print(f"  {key}: {path.name} ({size_kb:.0f} KB)")
            else:
                print(f"  {key}: NOT FOUND")
    else:
        print("Alternative-16 not found in spreads")

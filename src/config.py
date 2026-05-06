"""
VE Database Development - Configuration
========================================
전역 경로 및 상수 정의. 모든 모듈은 이 파일의 경로를 참조합니다.
"""

from pathlib import Path

# ── 프로젝트 루트 ──
PROJECT_ROOT = Path(__file__).parent.parent

# ── 데이터 디렉토리 ──
RAW_DATA_DIR = PROJECT_ROOT / ".raw_data"
DATA_DIR = PROJECT_ROOT / "data"
IMAGES_DIR = DATA_DIR / "images"
PAGES_DIR = DATA_DIR / "pages"
EXTRACTED_DIR = DATA_DIR / "extracted"
DB_DIR = DATA_DIR / "db"
KG_DIR = DATA_DIR / "kg"
DB_PATH = DB_DIR / "ve_database.sqlite"

# ── PDF 처리 설정 ──
PDF_START_PAGE = 130   # 1-indexed (PDF 페이지 번호 기준)
PDF_END_PAGE = 350     # 1-indexed (PDF 페이지 번호 기준)
PAGES_PER_SPREAD = 2   # 2페이지가 1세트
TARGET_DPI = 300       # 이미지 변환 해상도

# ── 이미지 타입 ──
IMAGE_TYPES = [
    "original_diagram",      # 원안 개요도
    "alternative_diagram",   # 대안 개요도
    "value_chart",           # 가치비교 차트
    "page_left",             # 좌측 페이지 전체
    "page_right",            # 우측 페이지 전체
]

# ── 성능 평가 대분류 ──
PERFORMANCE_CATEGORIES = [
    "사용자 편의성",
    "시공성",
    "유지관리성",
    "안전성",
    "환경/경관성",
]

# ── 가치 유형 분류 ──
VALUE_TYPES = [
    "가치혁신형",    # 성능↑ 비용↓
    "비용절감형",    # 성능= 비용↓
    "성능향상형",    # 성능↑ 비용=
    "기능향상형",    # 성능↑ 비용↑ (but 가치↑)
]


def ensure_directories():
    """모든 데이터 디렉토리가 존재하는지 확인하고 없으면 생성합니다."""
    for d in [RAW_DATA_DIR, DATA_DIR, IMAGES_DIR, PAGES_DIR,
              EXTRACTED_DIR, DB_DIR, KG_DIR]:
        d.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    ensure_directories()
    print(f"Project Root : {PROJECT_ROOT}")
    print(f"Raw Data Dir : {RAW_DATA_DIR}")
    print(f"DB Path      : {DB_PATH}")
    print(f"Page Range   : {PDF_START_PAGE} ~ {PDF_END_PAGE}")
    print(f"Spreads      : ~{(PDF_END_PAGE - PDF_START_PAGE + 1) // PAGES_PER_SPREAD} alternatives")
    print("All directories verified.")

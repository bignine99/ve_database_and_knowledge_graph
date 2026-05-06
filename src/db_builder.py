"""
VE Database Development - DB Builder
=====================================
SQLite 데이터베이스 초기화 및 데이터 적재 모듈.

적재 순서:
  1. projects 테이블에 프로젝트 정보 INSERT
  2. JSON 파일별로:
     - alternatives 테이블 INSERT
     - images 테이블 INSERT (원안/대안 개요도, 가치비교 차트)
     - performance_scores 테이블 INSERT (대안당 ~25행)
     - cost_evaluations 테이블 INSERT (대안당 ~5행)
     - value_evaluations 테이블 INSERT (대안당 1행)
"""

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional

from src.config import DB_PATH, DB_DIR, EXTRACTED_DIR


SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# 기본 프로젝트 정보
DEFAULT_PROJECT = {
    "project_id": "gangwon_newoffice_ve",
    "project_name": "강원특별자치도 신청사 건립공사 실시설계 VE",
    "file_path": ".raw_data/000_VE보고서_강원특별자치도 신청사 건립공사 실시설계VE.pdf",
    "page_start": 130,
    "page_end": 350,
}


def init_database(db_path: Path = None) -> sqlite3.Connection:
    """
    SQLite 데이터베이스를 초기화합니다.
    스키마 파일을 읽어 테이블, 인덱스, 뷰를 생성합니다.

    Args:
        db_path: DB 파일 경로. None이면 config.DB_PATH 사용.

    Returns:
        sqlite3.Connection 객체
    """
    if db_path is None:
        db_path = DB_PATH

    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()

    return conn


def get_table_counts(conn: sqlite3.Connection) -> dict:
    """모든 테이블의 레코드 수를 반환합니다."""
    tables = ["projects", "alternatives", "images",
              "performance_scores", "cost_evaluations", "value_evaluations"]
    counts = {}
    for table in tables:
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]
    return counts


def insert_project(
    conn: sqlite3.Connection,
    project_info: dict = None,
    total_alternatives: int = 107,
) -> str:
    """
    프로젝트 정보를 projects 테이블에 INSERT합니다.

    Returns:
        project_id
    """
    if project_info is None:
        project_info = DEFAULT_PROJECT

    conn.execute("""
        INSERT OR REPLACE INTO projects
            (project_id, project_name, file_path, total_alternatives, page_start, page_end)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        project_info["project_id"],
        project_info["project_name"],
        project_info["file_path"],
        total_alternatives,
        project_info.get("page_start"),
        project_info.get("page_end"),
    ))
    conn.commit()
    return project_info["project_id"]


def insert_alternative_from_json(
    conn: sqlite3.Connection,
    json_path: Path,
    project_id: str,
) -> dict:
    """
    추출된 JSON 파일을 읽어 6개 테이블에 INSERT합니다.

    Args:
        conn: DB 커넥션
        json_path: alt_XXX.json 파일 경로
        project_id: 프로젝트 ID

    Returns:
        {"alt_id": str, "records": {table: count}}
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    alt_number = data.get("alt_number", 0)
    alt_id = f"{project_id}_alt_{alt_number:03d}"
    records = {}

    # ── 1. alternatives 테이블 ──
    conn.execute("""
        INSERT OR REPLACE INTO alternatives
            (alt_id, project_id, alt_number, location, proposal_title,
             original_description, alternative_description,
             advantages, disadvantages, implementation_notes,
             analysis_summary, value_type, page_left, page_right)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        alt_id,
        project_id,
        alt_number,
        data.get("location", ""),
        data.get("proposal_title", ""),
        data.get("original", {}).get("description", ""),
        data.get("alternative", {}).get("description", ""),
        data.get("characteristics", {}).get("advantages", ""),
        data.get("characteristics", {}).get("disadvantages", ""),
        data.get("characteristics", {}).get("implementation_notes", ""),
        data.get("analysis_summary", ""),
        data.get("value_evaluation", {}).get("value_type", ""),
        data.get("page_left", 0),
        data.get("page_right", 0),
    ))
    records["alternatives"] = 1

    # ── 2. images 테이블 ──
    img_count = 0
    image_mappings = [
        ("original_diagram", data.get("original", {}).get("diagram_image_path", "")),
        ("alternative_diagram", data.get("alternative", {}).get("diagram_image_path", "")),
        ("value_chart", data.get("value_chart_image_path", "")),
    ]
    for image_type, file_path in image_mappings:
        if file_path:
            image_id = f"{alt_id}_{image_type}"
            conn.execute("""
                INSERT OR REPLACE INTO images
                    (image_id, alt_id, image_type, file_path, ai_description, width, height)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                image_id,
                alt_id,
                image_type,
                file_path,
                data.get("original" if "original" in image_type else "alternative", {}).get("ai_description", ""),
                None,  # width — 이미지 파일에서 추출 가능하지만 현재 미구현
                None,  # height
            ))
            img_count += 1
    records["images"] = img_count

    # ── 3. performance_scores 테이블 ──
    perf_count = 0
    for idx, ps in enumerate(data.get("performance_scores", [])):
        # 헤더 행 건너뛰기 (criteria가 "중분류 평가기준" 등)
        criteria = ps.get("criteria", "")
        if criteria in ("중분류 평가기준", "평가기준") or not criteria:
            continue
        # 원안/대안 점수가 둘 다 None이면 건너뛰기
        if ps.get("original") is None and ps.get("alternative") is None:
            continue

        score_id = f"{alt_id}_perf_{idx:03d}"
        conn.execute("""
            INSERT OR REPLACE INTO performance_scores
                (score_id, alt_id, category, subcategory, criteria,
                 original_score, alternative_score, score_delta, delta_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            score_id,
            alt_id,
            ps.get("category", ""),
            ps.get("subcategory", ""),
            criteria,
            ps.get("original"),
            ps.get("alternative"),
            ps.get("delta"),
            ps.get("reason", ""),
        ))
        perf_count += 1
    records["performance_scores"] = perf_count

    # ── 4. cost_evaluations 테이블 ──
    ce = data.get("cost_evaluation", {})
    cost_count = 0
    cost_rows = [
        ("idea_initial", ce.get("idea_initial_original"), ce.get("idea_initial_alternative"), None, None),
        ("idea_lifecycle", ce.get("idea_lifecycle_original"), ce.get("idea_lifecycle_alternative"), None, None),
        ("project_initial", ce.get("project_initial_original"), ce.get("project_initial_alternative"),
         ce.get("savings_amount"), ce.get("savings_initial_rate")),
        ("project_maintenance", ce.get("project_maintenance_original"), ce.get("project_maintenance_alternative"), None, None),
        ("project_lifecycle", ce.get("project_lifecycle_original"), ce.get("project_lifecycle_alternative"),
         None, ce.get("savings_lifecycle_rate")),
    ]
    for cost_type, orig, alt, savings, rate in cost_rows:
        if orig is not None or alt is not None:
            cost_id = f"{alt_id}_cost_{cost_type}"
            conn.execute("""
                INSERT OR REPLACE INTO cost_evaluations
                    (cost_id, alt_id, cost_type, original_cost, alternative_cost,
                     savings_amount, savings_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (cost_id, alt_id, cost_type, orig, alt, savings, rate))
            cost_count += 1
    records["cost_evaluations"] = cost_count

    # ── 5. value_evaluations 테이블 ──
    ve = data.get("value_evaluation", {})
    value_id = f"{alt_id}_value"
    conn.execute("""
        INSERT OR REPLACE INTO value_evaluations
            (value_id, alt_id, performance_original, performance_alternative,
             performance_change_rate, cost_change_rate, relative_lcc,
             value_original, value_alternative, value_change_rate, value_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        value_id,
        alt_id,
        ve.get("performance_original"),
        ve.get("performance_alternative"),
        ve.get("performance_change_rate"),
        ve.get("cost_change_rate"),
        ve.get("relative_lcc"),
        ve.get("value_original"),
        ve.get("value_alternative"),
        ve.get("value_change_rate"),
        ve.get("value_type", ""),
    ))
    records["value_evaluations"] = 1

    conn.commit()
    return {"alt_id": alt_id, "records": records}


def load_all_extracted_jsons(
    conn: sqlite3.Connection,
    extracted_dir: Path = None,
    project_id: str = None,
) -> dict:
    """
    data/extracted/ 디렉토리의 모든 alt_XXX.json 파일을 DB에 적재합니다.

    Returns:
        {"loaded": int, "failed": int, "total_records": dict}
    """
    if extracted_dir is None:
        extracted_dir = EXTRACTED_DIR
    if project_id is None:
        project_id = DEFAULT_PROJECT["project_id"]

    json_files = sorted(extracted_dir.glob("alt_*.json"))
    if not json_files:
        print(f"No JSON files found in {extracted_dir}")
        return {"loaded": 0, "failed": 0, "total_records": {}}

    # 프로젝트 레코드 생성
    insert_project(conn, total_alternatives=len(json_files))

    loaded = 0
    failed = 0
    total_records = {
        "alternatives": 0,
        "images": 0,
        "performance_scores": 0,
        "cost_evaluations": 0,
        "value_evaluations": 0,
    }

    for json_path in json_files:
        try:
            result = insert_alternative_from_json(conn, json_path, project_id)
            for table, count in result["records"].items():
                total_records[table] += count
            loaded += 1
        except Exception as e:
            failed += 1
            print(f"  [ERROR] {json_path.name}: {e}")

    return {
        "loaded": loaded,
        "failed": failed,
        "total_records": total_records,
    }


if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # DB 초기화 (기존 데이터 삭제 후 재생성)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = init_database()

    # 전체 JSON → SQLite 적재
    print("Loading extracted JSONs into SQLite...")
    result = load_all_extracted_jsons(conn)

    print(f"\n=== Loading Complete ===")
    print(f"  Loaded: {result['loaded']}")
    print(f"  Failed: {result['failed']}")
    print(f"  Records:")
    for table, count in result['total_records'].items():
        print(f"    {table}: {count}")

    # 테이블 카운트 확인
    counts = get_table_counts(conn)
    print(f"\n=== DB Table Counts ===")
    for table, count in counts.items():
        print(f"  {table}: {count}")

    # 검증 쿼리
    print(f"\n=== Validation Queries ===")

    # 가치유형 분포
    cursor = conn.execute("""
        SELECT value_type, COUNT(*) as cnt
        FROM value_evaluations
        WHERE value_type != ''
        GROUP BY value_type
        ORDER BY cnt DESC
    """)
    print(f"  Value Type Distribution:")
    for row in cursor:
        print(f"    {row[0]}: {row[1]}")

    # 성능 합계 검증 (대안-16)
    cursor = conn.execute("""
        SELECT SUM(original_score), SUM(alternative_score)
        FROM performance_scores
        WHERE alt_id = 'gangwon_newoffice_ve_alt_016'
    """)
    row = cursor.fetchone()
    print(f"\n  Alt-16 Performance Totals: orig={row[0]}, alt={row[1]}")

    # NULL 비율 확인
    cursor = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN location = '' THEN 1 ELSE 0 END) as no_location,
            SUM(CASE WHEN proposal_title = '' THEN 1 ELSE 0 END) as no_title,
            SUM(CASE WHEN analysis_summary = '' THEN 1 ELSE 0 END) as no_summary,
            SUM(CASE WHEN value_type = '' THEN 1 ELSE 0 END) as no_vtype
        FROM alternatives
    """)
    row = cursor.fetchone()
    print(f"\n  Alternatives NULL Rates:")
    print(f"    total={row[0]}, no_location={row[1]}, no_title={row[2]}, no_summary={row[3]}, no_value_type={row[4]}")

    conn.close()
    print(f"\n  DB saved to: {DB_PATH}")

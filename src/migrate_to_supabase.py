"""
SQLite → Supabase 마이그레이션 v2
- FK 제약조건 임시 비활성화 후 bulk insert
- REAL 컬럼에 빈 문자열 → NULL 변환
"""
import sqlite3, psycopg2, os, sys, io
from pathlib import Path
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
SQLITE_PATH = BASE_DIR / "data" / "db" / "ve_database.sqlite"


def get_pg():
    return psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        port=int(os.getenv("SUPABASE_DB_PORT", 5432)),
        dbname=os.getenv("SUPABASE_DB_NAME", "postgres"),
        user=os.getenv("SUPABASE_DB_USER", "postgres"),
        password=os.getenv("SUPABASE_DB_PASS"),
        sslmode="require",
    )


def get_col_types(pg_cur, table):
    pg_cur.execute("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name = %s AND table_schema = 'public'
    """, (table,))
    return {r[0]: r[1] for r in pg_cur.fetchall()}


NUMERIC_TYPES = {'real', 'double precision', 'integer', 'bigint', 'numeric', 'smallint'}


def clean_val(val, col_type):
    if val is None or val == '':
        return None if col_type in NUMERIC_TYPES else (val if val is not None else '')
    return val


def migrate(sl, pg, table, cols):
    cur_s = sl.cursor()
    cur_p = pg.cursor()
    col_types = get_col_types(cur_p, table)

    rows = cur_s.execute(f"SELECT {','.join(cols)} FROM {table}").fetchall()
    if not rows:
        print(f"  {table}: 0 rows")
        return

    ph = ','.join(['%s'] * len(cols))
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({ph}) ON CONFLICT DO NOTHING"

    ok = 0
    fail = 0
    for row in rows:
        cleaned = [clean_val(row[i], col_types.get(cols[i], 'text')) for i in range(len(cols))]
        try:
            cur_p.execute(sql, cleaned)
            ok += 1
        except Exception as e:
            fail += 1
            pg.rollback()

    pg.commit()
    print(f"  ✅ {table}: {ok}/{len(rows)} ({fail} errors)")


def run():
    print("=" * 60)
    print("SQLite → Supabase 마이그레이션 v2")
    print("=" * 60)

    sl = sqlite3.connect(str(SQLITE_PATH))
    pg = get_pg()
    print(f"✅ 연결 완료")

    # FK 제약조건 임시 비활성화
    cur = pg.cursor()
    cur.execute("SET session_replication_role = replica;")
    pg.commit()
    print("  FK 제약조건 비활성화")

    # 기존 데이터 클리어
    for t in ['images', 'performance_scores', 'cost_evaluations', 'value_evaluations', 'alternatives', 'projects']:
        cur.execute(f"DELETE FROM {t}")
    pg.commit()
    print("  기존 데이터 클리어 완료\n")

    # 마이그레이션
    migrate(sl, pg, "projects",
        ["project_id", "project_name", "file_path", "total_alternatives",
         "page_start", "page_end", "source_file", "source_year", "source_org"])

    migrate(sl, pg, "alternatives",
        ["alt_id", "project_id", "alt_number", "location", "proposal_title",
         "original_description", "alternative_description", "advantages",
         "disadvantages", "implementation_notes", "analysis_summary",
         "value_type", "page_left", "page_right",
         "how2_code", "how2_name", "space", "value_type_corrected",
         "project_name", "source_page", "field_category"])

    migrate(sl, pg, "cost_evaluations",
        ["cost_id", "alt_id", "cost_type", "original_cost",
         "alternative_cost", "savings_amount", "savings_rate"])

    migrate(sl, pg, "value_evaluations",
        ["value_id", "alt_id", "performance_original", "performance_alternative",
         "performance_change_rate", "cost_change_rate", "relative_lcc",
         "value_original", "value_alternative", "value_change_rate", "value_type"])

    migrate(sl, pg, "performance_scores",
        ["score_id", "alt_id", "category", "subcategory", "criteria",
         "original_score", "alternative_score", "score_delta", "delta_reason"])

    migrate(sl, pg, "images",
        ["image_id", "alt_id", "image_type", "file_path",
         "ai_description", "width", "height"])

    # FK 복원
    cur.execute("SET session_replication_role = DEFAULT;")
    pg.commit()

    # 검증
    print("\n=== 검증 ===")
    for t in ["projects", "alternatives", "cost_evaluations", "value_evaluations", "performance_scores", "images"]:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"  {t}: {cur.fetchone()[0]} rows")

    pg.close()
    sl.close()
    print("\n✅ 마이그레이션 완료!")


if __name__ == "__main__":
    run()

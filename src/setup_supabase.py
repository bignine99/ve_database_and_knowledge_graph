"""Supabase 연결 테스트 + 테이블 생성."""
import psycopg2, os, sys, io
from pathlib import Path
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

CREATE_SQL = """
-- ═══ VE Database 테이블 생성 (PostgreSQL) ═══

CREATE TABLE IF NOT EXISTS projects (
    project_id    TEXT PRIMARY KEY,
    project_name  TEXT NOT NULL,
    file_path     TEXT DEFAULT '',
    total_alternatives INTEGER DEFAULT 0,
    page_start    INTEGER,
    page_end      INTEGER,
    source_file   TEXT DEFAULT '',
    source_year   INTEGER DEFAULT 0,
    source_org    TEXT DEFAULT '',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alternatives (
    alt_id                TEXT PRIMARY KEY,
    project_id            TEXT NOT NULL REFERENCES projects(project_id),
    alt_number            INTEGER NOT NULL,
    location              TEXT DEFAULT '',
    proposal_title        TEXT NOT NULL,
    original_description  TEXT DEFAULT '',
    alternative_description TEXT DEFAULT '',
    advantages            TEXT DEFAULT '',
    disadvantages         TEXT DEFAULT '',
    implementation_notes  TEXT DEFAULT '',
    analysis_summary      TEXT DEFAULT '',
    value_type            TEXT DEFAULT '',
    page_left             INTEGER,
    page_right            INTEGER,
    how2_code             TEXT DEFAULT '',
    how2_name             TEXT DEFAULT '',
    space                 TEXT DEFAULT '',
    value_type_corrected  TEXT DEFAULT '',
    project_name          TEXT DEFAULT '',
    source_page           INTEGER DEFAULT 0,
    field_category        TEXT DEFAULT '',
    created_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS images (
    image_id      TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    alt_id        TEXT NOT NULL REFERENCES alternatives(alt_id),
    image_type    TEXT NOT NULL,
    file_path     TEXT NOT NULL,
    ai_description TEXT DEFAULT '',
    width         INTEGER,
    height        INTEGER,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS performance_scores (
    score_id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    alt_id            TEXT NOT NULL REFERENCES alternatives(alt_id),
    category          TEXT NOT NULL,
    subcategory       TEXT DEFAULT '',
    criteria          TEXT DEFAULT '',
    original_score    REAL,
    alternative_score REAL,
    score_delta       REAL,
    delta_reason      TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS cost_evaluations (
    cost_id            TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    alt_id             TEXT NOT NULL REFERENCES alternatives(alt_id),
    cost_type          TEXT NOT NULL,
    original_cost      REAL,
    alternative_cost   REAL,
    savings_amount     REAL,
    savings_rate       REAL
);

CREATE TABLE IF NOT EXISTS value_evaluations (
    value_id                  TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    alt_id                    TEXT NOT NULL REFERENCES alternatives(alt_id),
    performance_original      REAL,
    performance_alternative   REAL,
    performance_change_rate   REAL,
    cost_change_rate          REAL,
    relative_lcc              REAL,
    value_original            REAL,
    value_alternative         REAL,
    value_change_rate         REAL,
    value_type                TEXT DEFAULT ''
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_alt_project ON alternatives(project_id);
CREATE INDEX IF NOT EXISTS idx_alt_number ON alternatives(alt_number);
CREATE INDEX IF NOT EXISTS idx_alt_how2 ON alternatives(how2_code);
CREATE INDEX IF NOT EXISTS idx_cost_alt ON cost_evaluations(alt_id);
CREATE INDEX IF NOT EXISTS idx_perf_alt ON performance_scores(alt_id);
CREATE INDEX IF NOT EXISTS idx_value_alt ON value_evaluations(alt_id);
CREATE INDEX IF NOT EXISTS idx_images_alt ON images(alt_id);
"""

try:
    conn = psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        port=int(os.getenv("SUPABASE_DB_PORT", 5432)),
        dbname=os.getenv("SUPABASE_DB_NAME", "postgres"),
        user=os.getenv("SUPABASE_DB_USER", "postgres"),
        password=os.getenv("SUPABASE_DB_PASS"),
        sslmode="require",
    )
    print(f"✅ Supabase 연결 성공: {os.getenv('SUPABASE_DB_HOST')}")

    cur = conn.cursor()
    cur.execute(CREATE_SQL)
    conn.commit()
    print("✅ 6개 테이블 + 7개 인덱스 생성 완료")

    # 확인
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
    tables = [r[0] for r in cur.fetchall()]
    print(f"  테이블 목록: {tables}")

    conn.close()
except Exception as e:
    print(f"❌ 연결 실패: {e}")

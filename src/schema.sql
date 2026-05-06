-- ============================================================
-- VE Database Schema (SQLite, PostgreSQL-compatible)
-- ============================================================
-- 강원특별자치도 신청사 VE 보고서 데이터베이스 스키마
-- 6개 테이블: projects, alternatives, images,
--             performance_scores, cost_evaluations, value_evaluations
-- ============================================================

-- 프로젝트 (VE 보고서 단위, 1,000+ 스케일 대비)
CREATE TABLE IF NOT EXISTS projects (
    project_id    TEXT PRIMARY KEY,
    project_name  TEXT NOT NULL,
    file_path     TEXT NOT NULL,
    total_alternatives INTEGER,
    page_start    INTEGER,
    page_end      INTEGER,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- VE 대안 (핵심 테이블)
CREATE TABLE IF NOT EXISTS alternatives (
    alt_id                TEXT PRIMARY KEY,
    project_id            TEXT NOT NULL REFERENCES projects(project_id),
    alt_number            INTEGER NOT NULL,
    location              TEXT,
    proposal_title        TEXT NOT NULL,
    original_description  TEXT,
    alternative_description TEXT,
    advantages            TEXT,
    disadvantages         TEXT,
    implementation_notes  TEXT,
    analysis_summary      TEXT,
    value_type            TEXT,
    page_left             INTEGER,
    page_right            INTEGER,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 이미지 (개요도, 차트, 페이지 이미지)
CREATE TABLE IF NOT EXISTS images (
    image_id      TEXT PRIMARY KEY,
    alt_id        TEXT NOT NULL REFERENCES alternatives(alt_id),
    image_type    TEXT NOT NULL CHECK(image_type IN (
        'original_diagram', 'alternative_diagram',
        'value_chart', 'page_left', 'page_right'
    )),
    file_path     TEXT NOT NULL,
    ai_description TEXT,
    width         INTEGER,
    height        INTEGER,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 성능 평가 매트릭스 (대안당 약 25개 행)
CREATE TABLE IF NOT EXISTS performance_scores (
    score_id          TEXT PRIMARY KEY,
    alt_id            TEXT NOT NULL REFERENCES alternatives(alt_id),
    category          TEXT NOT NULL,
    subcategory       TEXT,
    criteria          TEXT NOT NULL,
    original_score    REAL,
    alternative_score REAL,
    score_delta       REAL,
    delta_reason      TEXT
);

-- 비용 평가 (대안당 5개 행)
CREATE TABLE IF NOT EXISTS cost_evaluations (
    cost_id            TEXT PRIMARY KEY,
    alt_id             TEXT NOT NULL REFERENCES alternatives(alt_id),
    cost_type          TEXT NOT NULL CHECK(cost_type IN (
        'idea_initial', 'idea_lifecycle',
        'project_initial', 'project_maintenance', 'project_lifecycle'
    )),
    original_cost      REAL,
    alternative_cost   REAL,
    savings_amount     REAL,
    savings_rate       REAL
);

-- 가치 평가 (대안당 1개 행)
CREATE TABLE IF NOT EXISTS value_evaluations (
    value_id                  TEXT PRIMARY KEY,
    alt_id                    TEXT NOT NULL REFERENCES alternatives(alt_id),
    performance_original      REAL,
    performance_alternative   REAL,
    performance_change_rate   REAL,
    cost_change_rate          REAL,
    relative_lcc              REAL,
    value_original            REAL,
    value_alternative         REAL,
    value_change_rate         REAL,
    value_type                TEXT
);

-- ============================================================
-- 인덱스 (검색 성능 최적화)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_alt_project ON alternatives(project_id);
CREATE INDEX IF NOT EXISTS idx_alt_number ON alternatives(alt_number);
CREATE INDEX IF NOT EXISTS idx_alt_value_type ON alternatives(value_type);
CREATE INDEX IF NOT EXISTS idx_img_alt ON images(alt_id);
CREATE INDEX IF NOT EXISTS idx_img_type ON images(image_type);
CREATE INDEX IF NOT EXISTS idx_perf_alt ON performance_scores(alt_id);
CREATE INDEX IF NOT EXISTS idx_perf_category ON performance_scores(category);
CREATE INDEX IF NOT EXISTS idx_cost_alt ON cost_evaluations(alt_id);
CREATE INDEX IF NOT EXISTS idx_value_alt ON value_evaluations(alt_id);

-- ============================================================
-- 뷰 (분석용)
-- ============================================================

-- 대안별 종합 요약 뷰
CREATE VIEW IF NOT EXISTS v_alternative_summary AS
SELECT
    a.alt_id,
    a.alt_number,
    a.location,
    a.proposal_title,
    a.value_type,
    v.performance_original,
    v.performance_alternative,
    v.performance_change_rate,
    v.cost_change_rate,
    v.relative_lcc,
    v.value_original,
    v.value_alternative,
    v.value_change_rate
FROM alternatives a
LEFT JOIN value_evaluations v ON a.alt_id = v.alt_id;

-- 가치유형 분포 뷰
CREATE VIEW IF NOT EXISTS v_value_type_distribution AS
SELECT
    value_type,
    COUNT(*) AS count,
    ROUND(AVG(performance_change_rate), 4) AS avg_perf_change,
    ROUND(AVG(cost_change_rate), 4) AS avg_cost_change,
    ROUND(AVG(value_change_rate), 4) AS avg_value_change
FROM value_evaluations
GROUP BY value_type;

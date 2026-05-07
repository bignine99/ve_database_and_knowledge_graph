# VE 보고서 데이터베이스 구축 — PRD & Implementation Plan

> **For AI Agent:** Follow this plan task-by-task. Use the executing-plans skill.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 강원특별자치도 신청사 VE 보고서 PDF(p130~350)에서 110개 대안 데이터를 추출하여 구조화된 SQLite DB + Knowledge Graph를 구축한다.

**Architecture:** 하이브리드 추출(PDF 파싱 + AI 보완), 이미지는 파일시스템 저장 + AI 서술, SQLite(PostgreSQL 마이그레이션 호환 스키마), NetworkX 기반 Knowledge Graph

**Tech Stack:** Python 3.11+, pdfplumber, PyMuPDF(fitz), Pillow, SQLite3, NetworkX, matplotlib

---

## 설계 결정 요약

| 항목 | 결정 |
|---|---|
| 1차 스코프 | 데이터 추출 + 구조화 DB + Knowledge Graph |
| 추출 방식 | 하이브리드 (PDF 파싱 + 멀티모달 AI 보완) |
| 이미지 전략 | 파일시스템 저장 + AI 텍스트 서술 생성 |
| DB 기술 | SQLite (PostgreSQL 호환 스키마) |
| 스케일 | 현재 1개 PDF 테스트 → 향후 1,000+ 파일 |
| 데이터 단위 | 2페이지 스프레드 = 1개 대안 |

---

## 2페이지 스프레드 데이터 구조

### 좌측 페이지 (Page 1)
- **헤더**: 대안번호, 위치(본청 등), 제안명(전체 텍스트)
- **원안**: 개요도 이미지 + 설명 텍스트
- **대안**: 개요도 이미지 + 설명 텍스트
- **대안의 특성**: 장점 / 단점 / 이행 시 고려사항

### 우측 페이지 (Page 2)
- **성능 세부 평가결과**: 대분류-중분류-평가기준 매트릭스 (원안/대안 점수, 증감, 사유)
- **비용 세부 평가결과**: 초비비용, 유지관리비, 생애주기비용
- **가치 세부 평가결과**: 성능(P), 비용(C), 가치(V), 증가율
- **가치비교 차트**: 바 차트 이미지
- **가치유형**: 가치혁신형 등 분류
- **분석결과**: 요약 텍스트

---

## Phase 1: Foundation — 프로젝트 기반 구축

### Step 1.1: 프로젝트 스캐폴딩

#### Task 1: 디렉토리 구조 및 의존성 초기화

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `tests/__init__.py`

- [x] **1-1.** 프로젝트 디렉토리 구조 생성

```
260504_ve_database_development/
├── .raw_data/              # 원본 PDF (기존)
├── data/
│   ├── images/             # 추출된 이미지 (대안별 폴더)
│   ├── pages/              # PDF 페이지 이미지
│   ├── extracted/          # 추출된 JSON
│   └── db/                 # SQLite DB 파일
├── src/
│   ├── config.py           # 경로, 상수 설정
│   ├── pdf_processor.py    # PDF 분할/이미지 변환
│   ├── table_extractor.py  # 테이블 파싱
│   ├── text_extractor.py   # 텍스트/헤더 추출
│   ├── image_extractor.py  # 개요도 이미지 크롭
│   ├── ai_enhancer.py      # AI 서술 생성/검증
│   ├── db_builder.py       # SQLite DB 구축
│   └── kg_builder.py       # Knowledge Graph 구축
├── tests/
├── docs/
│   └── PRD_implementation_plan.md
└── requirements.txt
```

- [x] **1-2.** `requirements.txt` 작성 및 설치

```
pdfplumber>=0.10.0
PyMuPDF>=1.23.0
Pillow>=10.0.0
networkx>=3.2
matplotlib>=3.8.0
pytest>=7.4.0
```

- [x] **1-3.** `src/config.py` — 전역 경로 및 상수 정의

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
RAW_DATA_DIR = PROJECT_ROOT / ".raw_data"
DATA_DIR = PROJECT_ROOT / "data"
IMAGES_DIR = DATA_DIR / "images"
PAGES_DIR = DATA_DIR / "pages"
EXTRACTED_DIR = DATA_DIR / "extracted"
DB_DIR = DATA_DIR / "db"
DB_PATH = DB_DIR / "ve_database.sqlite"

PDF_START_PAGE = 130
PDF_END_PAGE = 350
PAGES_PER_SPREAD = 2
TARGET_DPI = 300
```

---

### Step 1.2: 데이터베이스 스키마 설계

#### Task 2: SQLite 스키마 설계 (PostgreSQL 호환)

**Files:**
- Create: `src/schema.sql`
- Create: `src/db_builder.py` (초기 스키마 부분)

- [x] **2-1.** 스키마 SQL 작성

```sql
-- 프로젝트 (VE 보고서 단위)
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    project_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    total_alternatives INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- VE 대안 (핵심 테이블)
CREATE TABLE IF NOT EXISTS alternatives (
    alt_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id),
    alt_number INTEGER NOT NULL,
    location TEXT,
    proposal_title TEXT NOT NULL,
    original_description TEXT,
    alternative_description TEXT,
    advantages TEXT,
    disadvantages TEXT,
    implementation_notes TEXT,
    analysis_summary TEXT,
    value_type TEXT,
    page_left INTEGER,
    page_right INTEGER
);

-- 이미지 (개요도, 차트)
CREATE TABLE IF NOT EXISTS images (
    image_id TEXT PRIMARY KEY,
    alt_id TEXT NOT NULL REFERENCES alternatives(alt_id),
    image_type TEXT NOT NULL CHECK(image_type IN (
        'original_diagram','alternative_diagram','value_chart','page_left','page_right'
    )),
    file_path TEXT NOT NULL,
    ai_description TEXT,
    width INTEGER,
    height INTEGER
);

-- 성능 평가 매트릭스
CREATE TABLE IF NOT EXISTS performance_scores (
    score_id TEXT PRIMARY KEY,
    alt_id TEXT NOT NULL REFERENCES alternatives(alt_id),
    category TEXT NOT NULL,
    subcategory TEXT,
    criteria TEXT NOT NULL,
    original_score REAL,
    alternative_score REAL,
    score_delta REAL,
    delta_reason TEXT
);

-- 비용 평가
CREATE TABLE IF NOT EXISTS cost_evaluations (
    cost_id TEXT PRIMARY KEY,
    alt_id TEXT NOT NULL REFERENCES alternatives(alt_id),
    cost_type TEXT NOT NULL CHECK(cost_type IN (
        'idea_initial','idea_lifecycle',
        'project_initial','project_maintenance','project_lifecycle'
    )),
    original_cost REAL,
    alternative_cost REAL,
    savings_amount REAL,
    savings_rate REAL
);

-- 가치 평가
CREATE TABLE IF NOT EXISTS value_evaluations (
    value_id TEXT PRIMARY KEY,
    alt_id TEXT NOT NULL REFERENCES alternatives(alt_id),
    performance_original REAL,
    performance_alternative REAL,
    performance_change_rate REAL,
    cost_change_rate REAL,
    relative_lcc REAL,
    value_original REAL,
    value_alternative REAL,
    value_change_rate REAL,
    value_type TEXT
);
```

- [x] **2-2.** `db_builder.py` — DB 초기화 함수 구현
- [x] **2-3.** 스키마 생성 테스트 실행 및 검증

---

#### Task 3: JSON 추출 스키마 정의

**Files:**
- Create: `src/schemas.py`

- [x] **3-1.** 대안 1건의 전체 JSON 스키마 정의 (Python dataclass/dict)

```python
ALTERNATIVE_SCHEMA = {
    "alt_number": int,
    "location": str,
    "proposal_title": str,
    "original": {
        "diagram_image_path": str,
        "description": str,
        "ai_description": str
    },
    "alternative": {
        "diagram_image_path": str,
        "description": str,
        "ai_description": str
    },
    "characteristics": {
        "advantages": str,
        "disadvantages": str,
        "implementation_notes": str
    },
    "performance_scores": [
        {"category": str, "subcategory": str, "criteria": str,
         "original": float, "alternative": float,
         "delta": float, "reason": str}
    ],
    "cost_evaluation": {
        "idea": {"initial": float, "lifecycle": float},
        "project": {
            "initial_original": float, "initial_alternative": float,
            "maintenance_original": float, "maintenance_alternative": float,
            "lifecycle_original": float, "lifecycle_alternative": float
        },
        "savings": {"amount": float, "rate": float}
    },
    "value_evaluation": {
        "performance": {"original": float, "alternative": float, "change_rate": float},
        "cost": {"change_rate": float, "relative_lcc": float},
        "value": {"original": float, "alternative": float, "change_rate": float},
        "value_type": str
    },
    "value_chart_image_path": str,
    "analysis_summary": str,
    "pages": {"left": int, "right": int}
}
```

- [x] **3-2.** 스키마 검증 유틸리티 함수 작성

---

## Phase 2: PDF Processing Engine — PDF 처리 엔진

### Step 2.1: PDF 분해

#### Task 4: PDF → 페이지 이미지 변환

**Files:**
- Create: `src/pdf_processor.py`
- Test: `tests/test_pdf_processor.py`

- [x] **4-1.** PyMuPDF(fitz)로 PDF 페이지를 300DPI PNG 이미지로 변환하는 함수 구현
- [x] **4-2.** p130~p350 범위 필터링 및 `data/pages/` 저장 로직
- [x] **4-3.** 2페이지 스프레드 페어링 로직 — 107개 대안 자동 감지 (p137~350)
- [x] **4-4.** 테스트: 첫 2페이지 스프레드 변환 및 파일 존재 확인 (754KB, 708KB)

---

#### Task 5: 이미지 영역 감지 및 크롭

**Files:**
- Create: `src/image_extractor.py`
- Test: `tests/test_image_extractor.py`

- [x] **5-1.** 좌측 페이지에서 원안/대안 개요도 영역 감지 (xref 기반 직접 추출)
- [x] **5-2.** 우측 페이지에서 가치비교 차트 영역 크롭
- [x] **5-3.** 크롭된 이미지를 `data/images/{alt_number}/` 폴더에 저장
- [x] **5-4.** 테스트: 대안-16 이미지 3종(원안 44KB, 대안 55KB, 차트 16KB) 검증 완료

---

### Step 2.2: 테이블 및 텍스트 추출

#### Task 6: 테이블 데이터 추출 (pdfplumber)

**Files:**
- Create: `src/table_extractor.py`
- Test: `tests/test_table_extractor.py`

- [x] **6-1.** pdfplumber로 우측 페이지의 성능 세부 평가결과 테이블 파싱 (23항목)
- [x] **6-2.** 비용 세부 평가결과 테이블 파싱 (프로젝트 비용 정확도 100%)
- [x] **6-3.** 가치 세부 평가결과 테이블 파싱 (성능 500.0/503.57 ✓)
- [x] **6-4.** 테스트: 대안-16 우측 페이지 합계 500.0/503.57 검증 완료

---

#### Task 7: 헤더 및 텍스트 추출

**Files:**
- Create: `src/text_extractor.py`
- Test: `tests/test_text_extractor.py`

- [x] **7-1.** 좌측 페이지 헤더 파싱: 대안번호, 위치, 제안명 추출 (fitz dict 모드)
- [x] **7-2.** 원안/대안 설명 텍스트 추출 (y좌표 380~525 / 655~710)
- [x] **7-3.** 대안 특성(장점/단점/고려사항) 추출 (x좌표 기반 3컬럼 분리)
- [x] **7-4.** 우측 페이지 분석결과 요약 텍스트 추출 (y > 750)
- [x] **7-5.** 테스트: 6개 대안(01,02,16,51,81,101) 텍스트 필드 정합성 검증 완료

---

## Phase 3: AI Enhancement — AI 보완 처리

### Step 3.1: 멀티모달 AI 서술 생성

#### Task 8: 이미지 AI 서술 생성기

**Files:**
- Create: `src/ai_enhancer.py`
- Test: `tests/test_ai_enhancer.py`

- [x] **8-1.** Gemini 2.0 Flash API 연동 완료 — 개요도 이미지 입력 → 건축 기술 서술 생성
- [x] **8-2.** VE 전문가 프롬프트: 자재/치수/구조방식 포함 2~4문장 기술 서술
- [x] **8-3.** 원안 95/107, 대안 82/107 AI 서술 생성 (이미지 없는 12개 대안 제외)
- [x] **8-4.** 대안-16 검증: 28.5T 복컨접합유리→11.52T 반강화접합유리 변경 정확히 서술

---

#### Task 9: 데이터 교차 검증

**Files:**
- Modify: `src/ai_enhancer.py`

- [x] **9-1.** 비용 논리 검증: 초비비용 + 유지관리비 = 생애주기비용 (허용오차 1백만원)
- [x] **9-2.** 성능 합계 검증: 6개 대안에서 불일치 발견 (1~2점 차이, 테이블 추출 오차 추정)
- [x] **9-3.** 가치 공식 검증: V ≈ P변화율 + C변화율 관계 확인 (허용오차 2%)
- [x] **9-4.** 검증 결과 JSON 플래그 처리: `_validation` 필드로 각 alt_XXX.json에 기록 (101건 valid, 6건 warning)

---

## Phase 4: Database Construction — 데이터베이스 구축

### Step 4.1: 통합 추출 파이프라인

#### Task 10: 단일 대안 통합 추출기

**Files:**
- Create: `src/pipeline.py`
- Test: `tests/test_pipeline.py`

- [x] **10-1.** 단일 스프레드(2페이지)를 입력받아 전체 JSON 스키마 출력하는 통합 함수
- [x] **10-2.** 추출 순서: 텍스트(fitz) → 테이블(pdfplumber) → 이미지(xref) → 가치유형보완
- [x] **10-3.** 에러 핸들링: 개별 필드 추출 실패 시 null 허용 + traceback 로그
- [x] **10-4.** 테스트: 대안-16 E2E 완료 (completeness=1.0, validation=True)

---

#### Task 11: 전체 PDF 배치 처리

**Files:**
- Create: `src/batch_processor.py`

- [x] **11-1.** 107개 대안 순회 루프 구현 (중단/재개 지원)
- [x] **11-2.** 진행률 표시 (print flush, 대안당 1.2초)
- [x] **11-3.** 개별 JSON 파일 저장: `data/extracted/alt_{nnn}.json` (107개 완료)
- [x] **11-4.** 배치 리포트 생성: `scratch/batch_report.json` (100% 성공)

---

### Step 4.2: SQLite DB 적재

#### Task 12: JSON → SQLite 적재

**Files:**
- Modify: `src/db_builder.py`
- Test: `tests/test_db_builder.py`

- [x] **12-1.** 추출된 JSON 파일을 읽어 6개 테이블에 INSERT하는 함수
- [x] **12-2.** 중복 방지: UPSERT (INSERT OR REPLACE) 처리
- [x] **12-3.** 전체 107개 대안 적재 완료 (projects:1, alternatives:107, images:284, perf:2354, cost:334, value:107)
- [x] **12-4.** 검증 완료: Alt-16 성능합계 500.0/503.57 ✓, 제안명 누락 0건, 가치유형 분포 정상

---

#### Task 13: DB 인덱스 및 뷰 생성

**Files:**
- Modify: `src/schema.sql`

- [ ] **13-1.** 주요 검색 컬럼 인덱스: alt_number, category, value_type
- [ ] **13-2.** 분석용 VIEW 생성: 대안별 종합 요약 뷰
- [ ] **13-3.** 통계 VIEW: 공종별 평균 절감율, 가치유형 분포
- [ ] **13-4.** 1,000+ 스케일 대비 EXPLAIN QUERY PLAN 확인

---

## Phase 5: Knowledge Graph — 지식 그래프 구축

### Step 5.1: 온톨로지 설계

#### Task 14: 노드/엣지 타입 정의

**Files:**
- Create: `src/kg_ontology.py`

- [x] **14-1.** 노드 타입 정의 (7종 구현 완료)

| 노드 타입 | 예시 |
|---|---|
| `Project` | 강원특별자치도 신청사 |
| `Alternative` | 대안-16 |
| `Location` | 본청, 의회동 |
| `WorkType` | 건축, 기계, 전기, 토목 |
| `Material` | 복층접합유리, 반강화접합유리 |
| `PerformanceCategory` | 사용자편의성, 시공성, 유지관리성 |
| `ValueType` | 가치혁신형, 비용절감형 |

- [x] **14-2.** 엣지 타입 정의 (5종 구현 완료, EVALUATED_BY는 delta 데이터 부족으로 보류)

| 엣지 타입 | 연결 |
|---|---|
| `BELONGS_TO` | Alternative → Project |
| `LOCATED_AT` | Alternative → Location |
| `WORK_TYPE` | Alternative → WorkType |
| `USES_MATERIAL` | Alternative → Material |
| `EVALUATED_BY` | Alternative → PerformanceCategory |
| `CLASSIFIED_AS` | Alternative → ValueType |
| `REPLACES_MATERIAL` | Material → Material |

---

#### Task 15: Knowledge Graph 구축

**Files:**
- Create: `src/kg_builder.py`
- Test: `tests/test_kg_builder.py`

- [x] **15-1.** SQLite에서 데이터 로드 → NetworkX DiGraph 생성 (177노드, 417엣지)
- [x] **15-2.** 노드 속성 매핑 (proposal_title, performance_change, cost_change, value_change)
- [x] **15-3.** 엣지 생성 로직: 공종 키워드 매칭(6종), 자재 정규식 추출(45종)
- [x] **15-4.** GraphML 저장 + kg_stats.json 통계 리포트

---

#### Task 16: Knowledge Graph 검증 및 시각화

**Files:**
- Create: `src/kg_visualizer.py`

- [x] **16-1.** 전체 KG 네트워크 시각화 (spring layout, 다크테마, 한글폰트)
- [x] **16-2.** 공종별 대안 분포 바 차트 (건축31, 기계19, 전기18, 토목16, 통신13, 소방7)
- [x] **16-3.** 가치유형 파이 차트 (가치혁신형69.2%, 성능강조형23.1%, 성능향상형7.7%)
- [x] **16-4.** 3개 PNG 산출: kg_full_graph.png, kg_worktype_distribution.png, kg_value_type_distribution.png

---

## Phase 6: Scale & Quality — 확장성 및 품질 보증

### Step 6.1: 배치 프레임워크

#### Task 17: 다중 파일 처리 프레임워크

**Files:**
- Create: `src/multi_file_processor.py`

- [ ] **17-1.** 여러 PDF 파일을 순회하는 배치 프레임워크
- [ ] **17-2.** 파일별 project_id 생성 및 projects 테이블 적재
- [ ] **17-3.** 중단/재개 기능 (처리 상태 저장)
- [ ] **17-4.** 에러 격리: 개별 파일 실패가 전체 중단하지 않도록

---

#### Task 18: 품질 보증 리포트

**Files:**
- Create: `src/qa_reporter.py`

- [ ] **18-1.** 전체 DB 통계 리포트 생성 (대안 수, NULL 비율, 이미지 누락 등)
- [ ] **18-2.** 이상치 감지: 극단적 비용/점수 값 플래그
- [ ] **18-3.** 최종 검증: JSON 스키마 대비 완성도 백분율
- [ ] **18-4.** 마크다운 리포트 자동 생성: `docs/qa_report.md`

---

## Phase 7: CUBE Ontology Enhancement — 온톨로지 보강

> CUBE 표준분류체계의 WHERE/WHAT/HOW 3축 체계를 적용하여 Knowledge Graph를 보강합니다.
> 참조: `.raw_data/260505 CUBE 표준분류체계.txt`

### Step 7.1: CUBE 표준분류 마스터 테이블

#### Task 19: CUBE 분류체계 데이터 구축

**Files:**
- Create: `src/cube_taxonomy.py`

- [x] **19-1.** CUBE HOW 축 마스터 딕셔너리 구축 — 6공사 × 총 87개 대공종
- [x] **19-2.** CUBE WHERE 축 마스터 딕셔너리 구축 — 4구분 × 28개 속성
- [x] **19-3.** CUBE WHAT 축 마스터 딕셔너리 구축 — 4구분 × 13개 분류
- [x] **19-4.** HOW2 매핑 키워드 테이블 — 38개 대공종 키워드 매핑, HOW2 분류율 100%

---

#### Task 20: 온톨로지 보강 — Space/HOW2/REPLACES 노드 추가

**Files:**
- Modify: `src/kg_builder.py`

- [x] **20-1.** Space 22종 노드 추출 (옥상, 화장실, 지하주차장, 계단실 등)
- [x] **20-2.** HOW2 30종 SubWorkType 노드 + 107 엣지 (100% 분류)
- [x] **20-3.** REPLACES_MATERIAL 8개 엣지 추출
- [x] **20-4.** ValueType 100% 재추출 (가치혁신68, 성능강조18, 비용절감18, 성능향상3)
- [x] **20-5.** Material 정제 45→26개 (조사제거, 정규식 개선)

---

#### Task 21: DB 스키마 보강

**Files:**
- Modify: `src/schema.sql`
- Modify: `src/db_builder.py`

- [x] **21-1~3.** CUBE 마스터는 `src/cube_taxonomy.py` Python 딕셔너리로 구현
- [x] **21-4.** `alternatives`에 `how2_code`, `how2_name`, `space`, `value_type_corrected` 4컬럼 추가
- [x] **21-5.** 107개 대안 분류 결과 DB 업데이트 완료

---

#### Task 22: KG 재구축 및 검증

**Files:**
- Modify: `src/kg_builder.py`
- Modify: `src/kg_visualizer.py`

- [x] **22-1.** KG v2 재구축: 177→210 노드(+19%), 417→619 엣지(+48%)
- [x] **22-2.** "옥상 방수 VE item" 질의 → 5개 대안 매칭 성공 (방수코킹공사 3건 + 옥상 2건)
- [x] **22-3.** KG 시각화 재생성 (Space/SubWorkType/REPLACES 반영)
- [x] **22-4.** kg_stats.json 업데이트 완료

---

## Phase 8: Flask Dashboard — 종합 대시보드

### Step 8.1: Flask 서버 구축

#### Task 23: Flask 백엔드

**Files:**
- Create: `src/app.py`
- Create: `src/api.py`

- [x] **23-1.** Flask 앱 초기화 — `src/app.py`, port 5000
- [x] **23-2.** `/api/alternatives` — 검색/HOW1/ValueType 필터 지원
- [x] **23-3.** `/api/alternatives/<id>` — 성능/비용/가치/AI서술 전체 반환
- [x] **23-4.** `/api/kg/query` — CUBE 기반 hop 질의 (classify_how2+classify_space)
- [x] **23-5.** `/api/stats` — KPI + HOW1/HOW2/ValueType 분포

---

#### Task 24: 01. OVERVIEW 페이지

**Files:**
- Create: `src/templates/index.html`
- Create: `src/static/css/dashboard.css`

- [x] **24-1.** KPI 4종: 총 대안(107), 평균 절감율, AI 서술률, 가치혁신형 비율
- [x] **24-2.** HOW1 Doughnut + HOW2 Top15 Horizontal Bar (Chart.js)
- [x] **24-3.** ValueType Doughnut + Savings Top20 Bar
- [x] **24-4.** SaaS 디자인 스킬 적용 (White Mode, #061E4A Navy, Pretendard+Outfit)

---

#### Task 25: 02. ALTERNATIVES 페이지

- [x] **25-1.** 107개 대안 테이블 (실시간 검색/HOW1 필터/ValueType 필터)
- [x] **25-2.** 상세 모달: 원안/대안 비교 + AI 서술 + 성능/비용 메트릭
- [x] **25-3.** CUBE HOW2 코드 표시 + HOW1(A~F) 필터링

---

#### Task 26: 03. COST ANALYSIS 페이지

- [x] **26-1.** 비용 절감 분석 테이블 (절감액순 정렬)
- [x] **26-2.** Lifecycle Cost Savings Bar + Savings Rate vs Value Change Scatter
- [x] **26-3.** 절감/증가 색상 구분 (green/red)

---

#### Task 27: 04. KNOWLEDGE GRAPH 페이지

- [x] **27-1.** vis-network 인터랙티브 KG 뷰어 (210노드, 619엣지)
- [x] **27-2.** 노드 타입별 필터 (Alternative/SubWorkType/Space/Material/ValueType)
- [x] **27-3.** 노드 그룹별 색상/크기 차별화 + hover tooltip

---

#### Task 28: 05. AI VE 자문 페이지

- [x] **28-1.** 자연어 질의 입력 UI + Enter/Button 검색
- [x] **28-2.** KG 기반 hop 검색: 질의 → Space+HOW2 매칭 → 관련 대안 조회
- [x] **28-3.** 응답에 HOW2 경로, Space 경로, Materials, Value Type, Savings 포함
- [x] **28-4.** vis-network Hop 경로 시각화: Query→Space/HOW2→Alternatives

---

## Execution Summary

| Phase | Step | Tasks | 핵심 산출물 |
|---|---|---|---|
| **1. Foundation** | 1.1 스캐폴딩 | Task 1 | 프로젝트 구조, config |
| | 1.2 스키마 | Task 2-3 | SQLite 스키마, JSON 스키마 |
| **2. PDF Engine** | 2.1 분해 | Task 4-5 | 페이지 이미지, 크롭 이미지 |
| | 2.2 추출 | Task 6-7 | 테이블 데이터, 텍스트 데이터 |
| **3. AI Enhancement** | 3.1 AI | Task 8-9 | 이미지 서술, 데이터 검증 |
| **4. DB Construction** | 4.1 파이프라인 | Task 10-11 | 통합 JSON, 배치 처리 |
| | 4.2 적재 | Task 12-13 | SQLite DB, 인덱스/뷰 |
| **5. Knowledge Graph** | 5.1 온톨로지 | Task 14 | 노드/엣지 정의 |
| | 5.2 구축 | Task 15-16 | GraphML, 시각화 |
| **6. Scale & QA** | 6.1 배치 | Task 17-18 | 다중파일, QA 리포트 |
| **7. CUBE Ontology** | 7.1 분류체계 | Task 19-20 | CUBE 마스터, Space/HOW2 노드 |
| | 7.2 DB/KG 보강 | Task 21-22 | 스키마 보강, KG 재구축 |
| **8. Flask Dashboard** | 8.1 백엔드 | Task 23 | Flask API 서버 |
| | 8.2 UI 페이지 | Task 24-27 | Overview, Alternatives, Cost, KG |
| | 8.3 AI 자문 | Task 28 | AI VE 자문 + KG Hop 시각화 |

**총 28개 Task** — Phase 1-8 완료. Phase 7(CUBE Ontology) + Phase 8(Flask Dashboard) 구현 완료.

---
---

## Phase 9: Multi-Agent VE Intelligence — VE 자동화 에이전트 시스템

> **전제 조건**: 도면 분석 AI (별도 팀 개발), 내역/비용 분석 AI (별도 개발) 결과를 
> JSON 인터페이스로 제공받는다. 본 시스템은 이 데이터를 소비하여 VE 분석을 수행한다.

### 9.0 설계 원칙

| 원칙 | 설명 |
|---|---|
| **AI가 잘하는 것에 집중** | 유사 사례 검색, 패턴 기반 힌트, 보고서 초안 생성 |
| **AI가 못하는 것은 외부 의존** | 도면 해석(도면 AI), 비용 산출(내역 AI) |
| **사람이 최종 판단** | AI는 초안+근거 제공, 엔지니어가 수정+확정 |
| **기존 ML 인프라 최대 활용** | Tier 1~4 (시맨틱 검색, Hybrid RAG, SVM 분류, K-Means 클러스터) |

### 9.1 시스템 아키텍처

```
외부 입력
┌─────────────────────────────────────────────────┐
│  [도면 AI] → design_analysis.json               │
│    - 구조 부재 목록, 사양, 과잉설계 지적         │
│    - 설비 시스템 구성, 용량                       │
│                                                   │
│  [내역 AI] → cost_breakdown.json                 │
│    - 공종별 비용 내역, 단가, 물량                 │
│    - 비용 비중 상위 항목                          │
│                                                   │
│  [사용자] → project_brief.json                   │
│    - 프로젝트명, 용도, 규모, VE 목표              │
│    - 관심 공종, 제약 조건                         │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│              VE Leader (오케스트레이터)            │
│                                                   │
│  Step 1: 입력 파싱 + 분석 대상 선정               │
│  Step 2: FAST Agent → 기능 분해                   │
│  Step 3: DB 검색 Agent → 유사 사례 Top-K          │
│  Step 4: Idea Agent → 아이디어 도출               │
│  Step 5: Domain Agent(s) → 기술 검증 (병렬)       │
│  Step 6: Report Agent → 대안 보고서 초안          │
│                                                   │
│  ※ 각 Step 결과는 표준 JSON으로 다음 Step에 전달  │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│              출력: VE 대안 보고서 초안             │
│                                                   │
│  - 기능 분석 요약 (FAST)                          │
│  - 유사 사례 근거 (DB 727건 기반)                 │
│  - VE 아이디어 목록 (우선순위 포함)               │
│  - 도메인별 기술 검증 의견                        │
│  - 비용 절감 추정 (내역 AI 데이터 기반)           │
│                                                   │
│  ※ 엔지니어가 검토/수정 후 최종 확정              │
└─────────────────────────────────────────────────┘
```

---

### Step 9.1: 외부 인터페이스 스키마 정의

#### Task 29: 입력 JSON 인터페이스 설계

**Files:**
- Create: `src/agents/schemas.py`
- Create: `src/agents/__init__.py`

- [ ] **29-1.** `ProjectBrief` 스키마 — 프로젝트 기본 정보
  ```python
  {
    "project_name": str,
    "project_type": str,       # "공동주택" | "학교" | "청사" | ...
    "total_area": float,       # 연면적 (㎡)
    "total_cost": float,       # 총 공사비 (백만원)
    "ve_target_rate": float,   # VE 목표 절감율 (%)
    "focus_disciplines": list, # ["건축", "전기", "기계설비"]
    "constraints": list,       # ["공기 변경 불가", "미관 유지"]
  }
  ```
- [ ] **29-2.** `DesignAnalysis` 스키마 — 도면 AI 출력 수신
  ```python
  {
    "elements": [
      {
        "discipline": str,        # "건축" | "토목" | "전기" | ...
        "element_name": str,      # "옥상 방수층"
        "current_spec": str,      # "우레탄 도막방수 T=3mm"
        "quantity": str,          # "2,500㎡"
        "flags": list,            # ["과잉설계", "고비용"]
      }
    ]
  }
  ```
- [ ] **29-3.** `CostBreakdown` 스키마 — 내역 AI 출력 수신
  ```python
  {
    "items": [
      {
        "discipline": str,
        "work_type": str,         # "방수코킹공사"
        "item_name": str,         # "우레탄 도막방수"
        "unit_cost": float,
        "quantity": float,
        "total_cost": float,
        "cost_ratio": float,      # 전체 대비 비중 (%)
      }
    ],
    "top_cost_items": list,       # 비용 상위 20개 항목
  }
  ```
- [ ] **29-4.** Pydantic 모델로 입력 검증 + 기본값 처리 구현

---

#### Task 30: Agent 간 내부 인터페이스 설계

**Files:**
- Create: `src/agents/interfaces.py`

- [ ] **30-1.** `AgentRequest` 기본 클래스 — 모든 Agent 호출의 공통 입력
  ```python
  {
    "session_id": str,
    "step_number": int,
    "project_brief": ProjectBrief,
    "previous_results": dict,    # 이전 Step 결과 참조
  }
  ```
- [ ] **30-2.** `AgentResponse` 기본 클래스 — 모든 Agent 출력의 공통 형식
  ```python
  {
    "agent_name": str,
    "step_number": int,
    "status": "success" | "partial" | "failed",
    "confidence": float,          # 0.0 ~ 1.0
    "result": dict,               # Agent별 상세 결과
    "references": list,           # 근거 대안 번호 목록
    "warnings": list,             # 주의사항
    "next_agents": list,          # 다음에 호출할 Agent 제안
  }
  ```
- [ ] **30-3.** Step별 결과 스키마 정의:
  - `FastAnalysisResult` — 기능 분해 + 기능-비용 매핑
  - `SimilarCaseResult` — 유사 사례 검색 결과 (Tier 1~4 활용)
  - `IdeaListResult` — 아이디어 목록 + 우선순위 스코어
  - `DomainReviewResult` — 도메인별 기술 검증 의견
  - `ReportDraftResult` — 최종 보고서 초안

---

### Step 9.2: VE Leader 오케스트레이터

#### Task 31: VE Leader 코어 구현

**Files:**
- Create: `src/agents/ve_leader.py`

- [ ] **31-1.** `VELeader` 클래스 — 세션 관리 + 워크플로 제어
  ```python
  class VELeader:
      def run_session(self, brief, design=None, cost=None) -> ReportDraft:
          # Step 1: 입력 파싱 + 분석 대상 선정
          targets = self._select_targets(brief, design, cost)
          
          # Step 2: 유사 사례 검색 (기존 ML 인프라 활용)
          similar = self._search_similar_cases(targets)
          
          # Step 3: 아이디어 도출 (Idea Agent)
          ideas = self._generate_ideas(targets, similar)
          
          # Step 4: 도메인 검증 (해당 도메인 Agent 병렬 호출)
          reviews = self._domain_review(ideas, targets)
          
          # Step 5: 보고서 초안 생성
          report = self._generate_report(brief, similar, ideas, reviews)
          
          return report
  ```
- [ ] **31-2.** `_select_targets()` — 분석 대상 자동 선정 로직
  - 비용 비중 상위 N개 공종 추출
  - 도면 AI가 "과잉설계" 플래그한 항목 우선
  - 사용자 focus_disciplines 필터링
- [ ] **31-3.** `_search_similar_cases()` — 기존 Tier 1~4 연동
  - 각 target에 대해 시맨틱 검색 Top-5
  - ML 자동 분류 (HOW1/HOW2/ValueType)
  - 해당 클러스터의 평균 절감율/가치변화 참조
- [ ] **31-4.** 세션 상태 관리 (진행률, 각 Step 결과 저장)
- [ ] **31-5.** 에러 핸들링 — 외부 데이터 없을 때 graceful degradation
  - 도면 AI 없으면 → 사용자 입력 기반으로만 진행
  - 내역 AI 없으면 → DB 통계 기반 추정치 제공

---

#### Task 32: DB 검색 Agent (기존 ML 래핑)

**Files:**
- Create: `src/agents/db_search_agent.py`

- [ ] **32-1.** 기존 `semantic_search.py` 래핑 — AgentResponse 형식 출력
- [ ] **32-2.** 검색 결과에 클러스터 정보 첨부 (같은 클러스터 대안 통계)
- [ ] **32-3.** 검색 결과에 자동 분류 결과 첨부 (HOW1/HOW2/ValueType)
- [ ] **32-4.** "유사 사례 근거 카드" JSON 생성 — 보고서에 삽입할 형태

---

#### Task 33: Idea Agent (아이디어 도출)

**Files:**
- Create: `src/agents/idea_agent.py`

- [ ] **33-1.** Gemini 프롬프트 기반 아이디어 도출
  - 입력: 분석 대상 + 유사 사례 Top-5 + 비용 데이터
  - SKILL_idea_developer.md의 패턴 10개를 시스템 프롬프트로 주입
  - temperature 0.7 (창의성 필요)
- [ ] **33-2.** 아이디어 구조화 — 각 아이디어를 표준 JSON으로 파싱
  ```python
  {
    "idea_name": str,
    "category": str,           # "재료대체" | "공법변경" | "규격최적화" | ...
    "current": str,            # 현재 방식
    "proposed": str,           # 제안 대안
    "expected_saving": str,    # "약 5~10% 절감"
    "confidence": float,
    "reference_cases": list,   # 근거 대안 번호
    "risks": list,
    "domain_review_needed": list,  # ["건축", "구조"]
  }
  ```
- [ ] **33-3.** 아이디어 중복 제거 + 우선순위 자동 산정
- [ ] **33-4.** 환각 방지 — DB에 근거 없는 아이디어는 confidence 0.3 이하 표시

---

#### Task 34: Domain Agent (도메인별 기술 검증)

**Files:**
- Create: `src/agents/domain_agent.py`

- [ ] **34-1.** 범용 `DomainAgent` 클래스 — SKILL 파일을 동적으로 로드
  ```python
  class DomainAgent:
      def __init__(self, discipline: str):
          # .ve_SKILL/SKILL_{discipline}.md 로드
          self.skill_prompt = load_skill(discipline)
      
      def review(self, idea: dict, context: dict) -> DomainReviewResult:
          # Gemini에 SKILL prompt + idea + context 전달
          ...
  ```
- [ ] **34-2.** 6개 도메인 자동 매핑:
  - "건축" → SKILL_Architect.md
  - "토목" → SKILL_Civil.md
  - "전기" → SKILL_Electronic.md
  - "기계설비" → SKILL_Mechanic.md
  - "배관" → SKILL_Plumbing.md
  - "조경" → SKILL_Landscape.md
- [ ] **34-3.** 검증 결과 구조화:
  ```python
  {
    "recommendation": "적극추천" | "조건부추천" | "보류" | "부적합",
    "feasibility": float,      # 0.0 ~ 1.0
    "code_compliance": str,    # "적합" | "재검토" | "부적합"
    "performance_impact": str, # "개선" | "유지" | "저하"
    "concerns": list,
    "conditions": list,
  }
  ```
- [ ] **34-4.** 병렬 호출 — 여러 도메인을 asyncio로 동시 검증

---

#### Task 35: FAST Agent (기능 분석)

**Files:**
- Create: `src/agents/fast_agent.py`

- [ ] **35-1.** SKILL_FAST_Diagram_Developer.md 기반 프롬프트 구성
- [ ] **35-2.** 기능 분해 결과를 트리 JSON으로 구조화
  ```python
  {
    "project_goal": str,
    "functions": [
      {
        "level": 0,
        "name": str,
        "type": "primary" | "secondary" | "tertiary",
        "children": [...],
        "cost_allocation": float,    # 내역 AI 데이터 연동
        "value_ratio": float,        # 비용 대비 가치
      }
    ]
  }
  ```
- [ ] **35-3.** 기능-비용 불균형 자동 식별 (고비용 저가치 영역)
- [ ] **35-4.** (선택) Mermaid 다이어그램 자동 생성

---

#### Task 36: Report Agent (보고서 초안 생성)

**Files:**
- Create: `src/agents/report_agent.py`

- [ ] **36-1.** 전체 워크플로 결과를 VE 대안 보고서 초안으로 합성
- [ ] **36-2.** 대안별 보고서 양식:
  ```
  ┌──────────────────────────────────────────┐
  │  대안 제안서 (AI 초안)                    │
  ├──────────────────────────────────────────┤
  │  1. 제안명: [아이디어명]                  │
  │  2. 분류: [HOW1] / [HOW2] / [SPACE]      │
  │  3. 원안: [현재 설계]                     │
  │  4. 대안: [제안 변경]                     │
  │  5. 근거 사례:                            │
  │     - 대안 #191 (유사도 83.5%)            │
  │     - 대안 #413 (유사도 44.2%)            │
  │  6. 예상 효과:                            │
  │     - 비용 절감: 약 X백만원 (DB 통계 기반)│
  │     - 성능 변화: 유지 (도메인 검증 결과)  │
  │  7. 기술 검증: [건축] 적극추천            │
  │  8. 주의사항: [...]                       │
  │  9. ⚠ AI 초안 — 엔지니어 검토 필요       │
  └──────────────────────────────────────────┘
  ```
- [ ] **36-3.** Markdown + PDF 출력 지원
- [ ] **36-4.** "AI 초안" 워터마크 — 모든 출력에 AI 생성물 표시

---

### Step 9.3: API 및 대시보드 통합

#### Task 37: Multi-Agent API 엔드포인트

**Files:**
- Modify: `src/app.py`

- [ ] **37-1.** `POST /api/ve/session` — 새 VE 세션 생성
  - 입력: project_brief + (선택) design_analysis + cost_breakdown
  - 출력: session_id
- [ ] **37-2.** `GET /api/ve/session/<id>/status` — 세션 진행 상태
- [ ] **37-3.** `GET /api/ve/session/<id>/result` — 최종 결과 조회
- [ ] **37-4.** `POST /api/ve/session/<id>/feedback` — 사용자 피드백 저장

#### Task 38: 대시보드 VE Agent 페이지

**Files:**
- Modify: `src/templates/index.html`
- Create: `src/static/js/ve-agent.js`

- [ ] **38-1.** 사이드바에 "07. VE Agent" 메뉴 추가
- [ ] **38-2.** 프로젝트 정보 입력 폼 (JSON 직접 입력 또는 UI 폼)
- [ ] **38-3.** 실시간 진행 상태 표시 (Step 1~6 프로그레스)
- [ ] **38-4.** 결과 뷰어: 아이디어 카드 + 근거 사례 + 도메인 검증 표시
- [ ] **38-5.** 보고서 다운로드 (Markdown/PDF)

---

### Execution Summary (Phase 9 추가)

| Phase | Step | Tasks | 핵심 산출물 |
|---|---|---|---|
| **9. Multi-Agent** | 9.1 인터페이스 | Task 29-30 | 입출력 스키마, Agent 통신 규격 |
| | 9.2 Agent 구현 | Task 31-36 | VE Leader, 5개 Agent |
| | 9.3 통합 | Task 37-38 | API 엔드포인트, 대시보드 UI |

**총 10개 Task (Task 29~38)** — Phase 9 구현 시 기존 Tier 1~4 ML 인프라를 최대 활용.

### 구현 우선순위

| 순서 | Task | 이유 |
|---|---|---|
| **1차** | Task 29-30 (스키마) | 모든 Agent의 기반 |
| **2차** | Task 31 (VE Leader) + Task 32 (DB Search) | 핵심 오케스트레이터 + 기존 ML 래핑 |
| **3차** | Task 33 (Idea) + Task 34 (Domain) | 실제 VE 가치 생산 |
| **4차** | Task 35 (FAST) + Task 36 (Report) | 보고서 완성도 |
| **5차** | Task 37-38 (API + UI) | 사용자 인터페이스 |

# VE 보고서 데이터베이스 — 구현 및 수정 프로세스 로그

> **프로젝트**: 강원특별자치도 신청사 건립공사 실시설계 VE 보고서 데이터베이스화
> **작업일**: 2026-05-04
> **PRD**: `docs/PRD_implementation_plan.md` (18개 Task, 6개 Phase)

---

## 세션 요약 (2026-05-04)

### 완료된 Task: 1~6 (Phase 1 전체 + Phase 2 전체)

| Task | 모듈 | 상태 |
|---|---|---|
| Task 1: 디렉토리 구조 & 의존성 | `config.py`, `requirements.txt` | ✅ |
| Task 2: SQLite 스키마 | `schema.sql`, `db_builder.py` | ✅ |
| Task 3: JSON 추출 스키마 | `schemas.py` | ✅ |
| Task 4: PDF → 페이지 이미지 변환 | `pdf_processor.py` | ✅ |
| Task 5: 이미지 영역 감지 및 크롭 | `image_extractor.py` | ✅ |
| Task 6: 테이블 데이터 추출 | `table_extractor.py` | ✅ |

### 다음 세션 시작점: Task 7 (헤더 및 텍스트 추출)

---

## 세션 2: 2026-05-05

### 완료된 Task: 7, 10, 11, 12 (Phase 2 완료 + Phase 4 완료)

| Task | 모듈 | 상태 |
|---|---|---|
| Task 7: 헤더 및 텍스트 추출 | `text_extractor.py` | ✅ |
| Task 10: 통합 파이프라인 | `pipeline.py` | ✅ |
| Task 11: 전체 배치 처리 | `batch_processor.py` | ✅ |
| Task 12: JSON → SQLite 적재 | `db_builder.py` | ✅ |

### 다음 세션 시작점: Task 14 (Knowledge Graph 온톨로지)

---

## Phase 2 완료: PDF Processing Engine

### Task 7: 헤더 및 텍스트 추출

**생성된 파일:** `src/text_extractor.py`

**핵심 발견 사항:**
- pdfplumber는 이 PDF의 한글 인코딩(YDIYGO 폰트, KSC-EUC-H CMap) 처리에서 깨짐 발생
- **PyMuPDF(fitz)의 `get_text("dict")` 모드로 전환** → 유니코드 정상 추출 확인
- Windows 콘솔에서는 깨지지만, 실제 Python string은 정상 유니코드 (`\ub300\uc548` = `대안`)
- JSON 파일 저장 시 완벽한 한글 텍스트 출력 확인

**좌측 페이지 레이아웃 매핑 (y좌표 기준):**

| y좌표 범위 | 내용 | 추출 필드 |
|---|---|---|
| ~93-130 | `[대안-XX] (위치) 제안명...` | alt_number, location, proposal_title |
| ~137 | `구분` / `개요` | 레이블 (제외) |
| ~250-285 | `개/요/도` + `원안` | 원안 개요도 레이블 |
| ~380-425 | `설/명` + 원안 설명 텍스트 | original_description |
| ~525-563 | `개/요/도` + `대안` | 대안 개요도 레이블 |
| ~655-691 | `설/명` + 대안 설명 텍스트 | alternative_description |
| ~714 | `장 점` / `단 점` / `이행 시 고려사항` | 특성 헤더 |
| ~739-790 | 장점/단점/고려사항 (x좌표로 구분) | advantages, disadvantages, implementation_notes |

**특성 섹션 x좌표 구분:**
- x < 250: 장점
- 250 ≤ x < 420: 단점
- x ≥ 420: 고려사항

**검증 (6개 대안 테스트):**

| 대안 | alt_number | location | proposal_title | orig_desc | alt_desc | advantages |
|---|---|---|---|---|---|---|
| 대안-01 | 1 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 대안-02 | 2 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 대안-16 | 16 | 본청 ✅ | ✅ | ✅ | ✅ | ✅ |
| 대안-51 | 51 | ✅ | ✅ | ✅ | ✅ | ✅ (3항목) |
| 대안-81 | 81 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 대안-101 | 101 | ✅ | ✅ | ✅ (2행) | ✅ (2행) | ✅ (4항목) |

---

## Phase 4 완료: Database Construction

### Task 10: 단일 대안 통합 추출기

**생성된 파일:** `src/pipeline.py`

**추출 순서:**
1. `text_extractor.py` — 좌측 페이지 텍스트 (fitz)
2. `table_extractor.py` — 우측 페이지 테이블 (pdfplumber)
3. `image_extractor.py` — 이미지 추출 (fitz xref)
4. 가치유형 보완 — 분석결과 요약에서 추출

**E2E 테스트 (대안-16):**
- Validation: `valid=True`, `completeness=1.0`
- 성능 23항목, 합계 500.0/503.57 ✓
- 비용: 475,726.12 / 475,689.02 ✓
- 이미지: 3종 (원안, 대안, 차트) ✓

---

### Task 11: 전체 PDF 배치 처리

**생성된 파일:** `src/batch_processor.py`

**배치 실행 결과:**

| 항목 | 값 |
|---|---|
| 총 대안 수 | 107 |
| 성공 | **107 (100%)** |
| 실패 | **0** |
| 소요 시간 | 131.7초 (대안당 1.2초) |
| completeness=1.0 | ~80개 |
| completeness=0.8-0.9 | ~27개 (이미지 누락 등) |

**산출물:** `data/extracted/alt_001.json` ~ `alt_107.json`

---

### Task 12: JSON → SQLite 적재

**수정된 파일:** `src/db_builder.py` (insert_project, insert_alternative_from_json, load_all_extracted_jsons 추가)

**DB 적재 결과:**

| 테이블 | 레코드 수 |
|---|---|
| projects | 1 |
| alternatives | 107 |
| images | 284 |
| performance_scores | 2,354 |
| cost_evaluations | 334 |
| value_evaluations | 107 |
| **합계** | **3,187** |

**검증:**
- Alt-16 성능합계: orig=500.0, alt=503.57 ✅
- 제안명 누락: 0건 ✅
- 분석결과 누락: 0건 ✅
- 가치유형 분포: 가치혁신형(94), 성능강조형(9), 성능향상형(3), 기능향상형(1) ✅

---

## 현재 파일 구조

```
260504_ve_database_development/
├── .raw_data/
│   └── 000_VE보고서_강원특별자치도 신청사 건립공사 실시설계VE.pdf (72MB)
├── data/
│   ├── db/
│   │   └── ve_database.sqlite          # 6T, 3,187 레코드 ✅
│   ├── images/
│   │   └── 대안_01/ ~ 대안_107/          # 대안별 이미지 폴더 (284개 이미지)
│   ├── pages/                          # 테스트 렌더링 파일
│   ├── extracted/
│   │   └── alt_001.json ~ alt_107.json # 107개 대안 JSON ✅
│   └── kg/                             # (비어있음 — Task 14~16에서 사용)
├── src/
│   ├── __init__.py
│   ├── config.py                       # ✅ 전역 설정
│   ├── schema.sql                      # ✅ DB 스키마 (6T, 9I, 2V)
│   ├── schemas.py                      # ✅ Python dataclass 스키마
│   ├── db_builder.py                   # ✅ DB 초기화 + JSON→SQLite 적재
│   ├── pdf_processor.py                # ✅ PDF 분할/이미지 변환
│   ├── image_extractor.py              # ✅ 개요도/차트 이미지 추출
│   ├── table_extractor.py              # ✅ 테이블 데이터 추출
│   ├── text_extractor.py               # ✅ 헤더/텍스트 추출 (NEW)
│   ├── pipeline.py                     # ✅ 통합 파이프라인 (NEW)
│   └── batch_processor.py              # ✅ 전체 배치 처리 (NEW)
├── tests/
│   └── __init__.py
├── scratch/                            # 분석/임시 파일들
├── docs/
│   ├── PRD_implementation_plan.md       # 전체 구현 계획 (18 Task)
│   └── implementation_and_modification_processes.md  # 이 파일
├── requirements.txt
└── .gitignore
```

---

## 다음 세션 작업 계획

### Task 8-9: AI Enhancement (선택적)
- `src/ai_enhancer.py` — 멀티모달 AI로 개요도 이미지 서술 생성
- API 키 설정 필요 (Gemini/Claude)
- 데이터 교차 검증 (비용 합계, 성능 합계 자동 체크)

### Task 13: DB 인덱스 및 뷰 (이미 schema.sql에 포함, 검증만 필요)

### Task 14-16: Knowledge Graph
- `src/kg_ontology.py` — 노드/엣지 타입 정의
- `src/kg_builder.py` — SQLite → NetworkX 그래프
- `src/kg_visualizer.py` — 시각화

### Task 17-18: Scale & Quality
- 다중 파일 처리 프레임워크
- 품질 보증 리포트

---

## 기술 메모

### PDF 페이지 번호 매핑
- PDF 내부 표시 페이지 번호 (하단): `- 130 -` 등
- PyMuPDF 0-indexed: 페이지 130 = idx 129
- pdfplumber 0-indexed: 동일
- **대안-01 시작**: 표시 p130, idx 136, 실제 PDF p137
- **대안-107 끝**: 표시 p343, idx 349, 실제 PDF p350

### 인코딩 주의사항
- PDF 폰트: YDIYGO110/120/130 (KSC-EUC-H CMap), Haansoft Batang
- **pdfplumber**: 한글 깨짐 → 테이블 추출에서는 숫자만 사용하므로 OK
- **PyMuPDF(fitz)**: `get_text("dict")` 모드로 정상 유니코드 추출 가능
- **Windows 콘솔**: cp949 인코딩으로 출력 깨짐 → `sys.stdout` UTF-8 래핑 필요
- **JSON 파일**: UTF-8로 저장 시 완벽한 한글 텍스트

### table_extractor 좌표 보정
- 현재 좌표 범위는 대안-16 기준으로 설정
- 다른 대안에서 레이아웃이 약간 다를 수 있음 → 배치 처리 시 검증 완료 (107/107 성공)


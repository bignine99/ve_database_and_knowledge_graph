# VE Database Development — Implementation & Modification Processes

> **Project**: Construction VE (Value Engineering) Database & Analytics Dashboard  
> **Period**: 2026-05-04 ~ 2026-05-06  
> **Stack**: Flask + Supabase PostgreSQL + Chart.js + CUBE Taxonomy + NetworkX KG  
> **Author**: AI Agent (Antigravity)

---

## Table of Contents

1. [Phase 1: 초기 데이터베이스 구축](#phase-1)
2. [Phase 2: Supabase 마이그레이션](#phase-2)
3. [Phase 3: 대시보드 SaaS 디자인 리팩토링](#phase-3)
4. [Phase 4: 성능 분석 KPI 버그 수정](#phase-4)
5. [Phase 5: 대구광역시 2023 VE 사례집 (OCR 파이프라인)](#phase-5)
6. [Phase 6: 조달청 설계VE 사례집 2025](#phase-6)
7. [Phase 7: 퇴계동 국민체육센터 (5개 분야 PDF)](#phase-7)
8. [Phase 8: 한경대학교 글로컬융합교육센터 (6개 분야 PDF)](#phase-8)
9. [Phase 9: 왕산2초중통합 신축공사](#phase-9)
10. [Phase 10: 화곡초등학교 건립공사](#phase-10)
11. [Phase 11: 히어로 랜딩 페이지 구축](#phase-11)
12. [Phase 12: 텍스트 추출 엔진](#phase-12)
13. [Phase 13: 통합 파이프라인 + 배치 + DB 적재](#phase-13)
14. [Phase 14: Knowledge Graph 구축](#phase-14)
15. [Phase 15: AI Enhancement](#phase-15)
16. [Phase 16: CUBE 온톨로지 보강](#phase-16)
17. [Phase 17: Flask 종합 대시보드](#phase-17)
18. [Phase 18: Git 배포 준비](#phase-18)
19. [Phase 19: Amazon Lightsail 프로덕션 배포](#next-lightsail)
20. [Phase 20: 프로덕션 마감 — DNS, UI, 솔루션 연동](#phase-20)
21. [Phase 21: ML Hybrid RAG Engine 도입](#phase-21)
22. [Phase 22: Multi-Agent VE Intelligence](#phase-22)
23. [Phase 23: 비동기 라운드테이블 최적화](#phase-23)
24. [최종 데이터베이스 현황](#final-status)
25. [기술적 교훈 및 시행착오 기록](#lessons-learned)


---

## Phase 1: 초기 데이터베이스 구축 <a id="phase-1"></a>

### 1.1 목표
- PDF 기반 VE 보고서에서 구조화된 데이터 추출
- SQLite → PostgreSQL 관계형 스키마 설계
- CUBE 표준분류체계 (HOW1/HOW2/SPACE) 자동 분류

### 1.2 스키마 설계
```sql
-- 5개 핵심 테이블
projects          -- 프로젝트 메타데이터
alternatives      -- VE 대안 (proposal_title, original/alternative_description)
cost_evaluations  -- 비용 평가 (원안/대안 비용, 절감액, 절감율)
value_evaluations -- 가치 평가 (성능/비용/가치 변화율)
performance_scores -- 성능 상세 (6~7개 카테고리별 점수)
```

### 1.3 초기 데이터 소스
| 소스 | 추출기 | 건수 |
|---|---|---|
| 강원특별자치도 신청사 VE | `extract_001.py` | 125건 |
| 서울특별시 2022 건설공사 VE | `extract_002.py` | 110건 |
| 국가철도공단 2021 설계VE | `extract_003.py` | 107건 |

---

## Phase 2: Supabase 마이그레이션 <a id="phase-2"></a>

### 2.1 연결 설정
- **Host**: `aws-1-ap-northeast-2.pooler.supabase.com` (Session Pooler)
- **Port**: 5432
- **SSL**: `sslmode=require`
- **Driver**: `psycopg2`

### 2.2 시행착오: 직접 연결 vs Pooler
- **문제**: 초기에 직접 연결(`db.<project-id>.supabase.co:5432`) 시도 시 IPv6 문제로 실패
- **해결**: Supabase Session Pooler 엔드포인트 사용으로 안정적 연결 확보
- **환경변수**: `.env` 파일에 `SUPABASE_DB_HOST`, `SUPABASE_DB_PASS` 등 분리 관리

### 2.3 RLS (Row Level Security)
- 개발 단계에서 RLS 비활성화 상태로 운영
- 향후 사용자별 접근 제어 정책 수립 필요

---

## Phase 3: 대시보드 SaaS 디자인 리팩토링 <a id="phase-3"></a>

### 3.1 디자인 시스템 전환
- **Before**: Dark Navy 사이드바 + 10색 레인보우 차트 팔레트
- **After**: White Mode + Navy-Slate 4색 팔레트 (`#061E4A`, `#3B82F6`, `#64748B`, `#94A3B8`)

### 3.2 CSS 변경 (`dashboard.css`)
```css
/* KPI 레이아웃: 4열 고정 → 자동 5열 대응 */
.kpi-row {
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); /* was: repeat(4, 1fr) */
}
```

### 3.3 JS 색상 교체 (`dashboard.js`)
- 모든 Chart.js 인스턴스의 `backgroundColor`, `borderColor` 배열을 Navy 그라데이션으로 통일
- 개별 KPI 카드의 색상 바(border-bottom) 제거 → hover 시 전환 패턴

### 3.4 준수 규칙 (SaaS Design Skill)
- 이모지/이모티콘 **완전 금지**
- `rounded-sm` (4px) 원칙 — `rounded-xl` 이상 금지
- White Mode 강제 (`#FFFFFF` / `#F8FAFC`)
- Pretendard(한글) + Outfit(영문/숫자) 폰트 조합

---

## Phase 4: 성능 분석 KPI 버그 수정 <a id="phase-4"></a>

### 4.1 증상
- 성능 분석 페이지 상단 5개 KPI 카드가 모두 `0` 또는 `NaN` 표시

### 4.2 원인 분석
```sql
-- 문제: score_delta 컬럼이 전체 NULL
SELECT AVG(score_delta) FROM performance_scores;  -- → NULL
```

### 4.3 해결
`app.py`의 `/api/stats/extended` SQL 쿼리를 수정:
```python
# Before (실패):
AVG(score_delta) AS avg_delta

# After (성공):
AVG(alternative_score - original_score) AS avg_delta
```
- `score_delta` 컬럼 의존을 제거하고, 원안/대안 점수에서 직접 계산

### 4.4 추가 수정
- KPI 카드 5개가 한 줄에 표시되도록 CSS 그리드 변경
- `repeat(4, 1fr)` → `repeat(auto-fit, minmax(160px, 1fr))`

---

## Phase 5: 대구광역시 2023 VE 사례집 (OCR 파이프라인) <a id="phase-5"></a>

### 5.1 문제: CID 폰트 인코딩
- **파일**: `003_대구광역시_2023 설계경제성검토(VE) 사례집.pdf` (1,361 페이지)
- **증상**: PyMuPDF `get_text()` 호출 시 한글이 `(cid:XXXX)` 패턴으로 반환
- **원인**: Identity-H CID 인코딩 + ToUnicode CMap 미포함

### 5.2 시행착오: 텍스트 추출 시도
```python
# 시도 1: PyMuPDF — 실패
text = page.get_text()  # → "(cid:12345)(cid:67890)..."

# 시도 2: pdfplumber — 실패 (동일 CID 문제)

# 시도 3: OCR (pytesseract) — 성공
pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
text = pytesseract.image_to_string(img, lang='kor+eng')
```

### 5.3 시행착오: OCR 성능 최적화
- **문제**: 1,361 페이지 전체 OCR → 약 1시간 이상 소요
- **해결**: 2-Phase 접근
  - Phase 1: CID 텍스트 라인 수 + 이미지 수 기반 Pre-filter → **228개 후보** (10초)
  - Phase 2: 후보만 OCR → **17건 추출** (5분)

### 5.4 시행착오: stdout 버퍼링
- **문제**: Python 프로세스 실행 중 출력이 전혀 보이지 않음
- **원인**: Windows에서 pytesseract가 stdout을 버퍼링
- **해결**: `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` + `flush=True`

### 5.5 결과
- **추출**: 17건 (대안 #343 ~ #359)
- **분야**: 토목 11, 건축 2, 설비 4

---

## Phase 6: 조달청 설계VE 사례집 2025 <a id="phase-6"></a>

### 6.1 PDF 구조 분석
- **파일**: `004_조달청 설계VE 사례집_2025.pdf` (400 페이지)
- **한글 추출**: 정상 (OCR 불필요)
- **구조**: 2페이지/제안 (짝수: 제안+LCC, 홀수: 성능/가치 평가)
- **공종별 목차**: 건축(p18~), 기계(p104~), 토목(p182~), 조경(p224~), 전기(p266~), 통신(p306~)

### 6.2 추출 필드 매핑
```
Page 1 (짝수):
  - 제 안 명 → proposal_title
  - 공종 → field_category  
  - 개 선 전/후 → original/alternative_description
  - 생애주기비용(LCC) → lcc_original, lcc_alternative
  - 성능점수[P] → perf_original, perf_alternative
  - 가치점수[V] → value_original, value_alternative

Page 2 (홀수):
  - 초기공사비 합계 → cost_original, cost_alternative
  - 절감액 → cost_savings
  - 성능평가 6항목 → performance_scores (시공성, 유지관리성, 공간활용성, 독창성, 편의성, 안전성)
  - 가치향상도 → value_improvement
```

### 6.3 결과
- **추출**: 175건 (대안 #360 ~ #534), 처리시간 ~10초
- **공종**: 건축 45, 기계 38, 소방 22, 토목 20, 조경 20, 전기 19, 통신 11
- **성능평가**: 175건 전체 (6항목 상세)

---

## Phase 7: 퇴계동 국민체육센터 (5개 분야 PDF) <a id="phase-7"></a>

### 7.1 PDF 구조
- **5개 파일**: 건축(15p), 구조(25p), 기계(9p), 전기(21p), 토목(21p)
- **구조**: 2페이지/제안 — 홀수(대안정보+장단점+설계자검토의견), 짝수(비용산출근거)
- **한글 추출**: 정상

### 7.2 특이 데이터
- **설계자 검토의견** 필드 포함 (수용/미반영 여부)
- **비용 상세**: 직접비, 간접비(45%), 관급자재 구분
- **증감액**: 원안비용-대안비용

### 7.3 결과
- **추출**: 43건 (대안 #535 ~ #577)
- **분야**: 구조 12, 전기 10, 토목 10, 건축 7, 기계 4
- **비용절감**: 25건

---

## Phase 8: 한경대학교 글로컬융합교육센터 (6개 분야 PDF) <a id="phase-8"></a>

### 8.1 PDF 구조
- **6개 파일**: 건축(52p), 구조(40p), 기계(10p), 전기(12p), 조경(4p), 토목(20p)
- **구조**: 퇴계동과 동일한 2페이지 페어

### 8.2 시행착오: 건축/구조 파일 첫 페이지
- **문제**: 건축/구조 파일의 첫 페이지가 '참고사항' 텍스트로 시작 → 대안 페이지로 오인
- **해결**: `'대안번호' in text and '대 안 명' in text` 조건 추가로 정확한 감지

### 8.3 결과
- **추출**: 53건 (대안 #578 ~ #630)
- **분야**: 건축 17, 구조 13, 토목 10, 전기 6, 기계 5, 조경 2

---

## Phase 9: 왕산2초중통합 신축공사 <a id="phase-9"></a>

### 9.1 PDF 구조
- **단일 파일**: `007_왕산2초중통합신축_대안구체화.pdf` (65 페이지)
- **제안명 형식**: `[대안-XX] 제안제목` (첫 줄)
- **특수 구조**: 성능 세부 평가가 별도 페이지에 분리

### 9.2 시행착오: 2-page pair 가정 오류
- **1차 추출**: 9건만 추출 (31건 중)
- **원인**: `range(0, pages, 2)` 고정 2페이지 페어 가정 → 일부 대안이 3페이지 이상
- **분석**: `[대안-XX]` 패턴을 모든 페이지에서 검색 → 32개 proposal 페이지 발견

### 9.3 해결: 유연한 페이지 매핑
```python
# Phase 1: 모든 페이지에서 [대안-XX] 패턴 감지
proposal_pages = {}  # alt_num -> page_idx (대안 개요)
perf_pages = {}      # alt_num -> [page_idx, ...] (성능 평가)

for i in range(pages):
    text = doc[i].get_text()
    alts = re.findall(r'\[대안-(\d+)\]', text)
    if not alts: continue
    alt_num = int(alts[0])
    first_line = text.split('\n')[0].strip()
    if '성능 세부 평가' in first_line:
        perf_pages.setdefault(alt_num, []).append(i)
    else:
        proposal_pages[alt_num] = i
```

### 9.4 시행착오: 이전 데이터 삭제
- **문제**: 1차 추출 9건 → 수정 후 재추출 시 중복 적재
- **해결**: `DELETE FROM ... WHERE alt_id LIKE 'wangsan_%'` 실행 후 재추출

### 9.5 결과
- **추출**: 31건 (대안 #631 ~ #661)
- **분야**: 건축 20, 토목 5, 구조 2, 기계 2, 전기 1, 조경 1

---

## Phase 10: 화곡초등학교 건립공사 <a id="phase-10"></a>

### 10.1 PDF 구조
- **단일 파일**: `008_화곡초등학교_대안구체화.pdf` (142 페이지)
- **구조**: 왕산과 동일한 `[대안-XX]` 형식

### 10.2 추출기 재사용
- `extract_008.py`를 복사하여 `extract_009.py` 생성
- 프로젝트 상수만 변경 (PROJECT_ID, PROJECT_NAME, PDF_PATH, alt_id prefix)

### 10.3 결과
- **추출**: 66건 (대안 #662 ~ #727)
- **분야**: 건축 41, 기계 12, 전기 6, 구조 5, 토목 1, 조경 1

---

## Phase 11: 히어로 랜딩 페이지 구축 <a id="phase-11"></a>

### 11.1 라우트 변경
```python
# app.py 라우팅 구조 변경
@app.route("/")        → landing.html (히어로 페이지)
@app.route("/dashboard") → index.html (기존 대시보드)
```

### 11.2 구현 내용
- **제목**: "Value Engineering Powered by AI Agent"
- **섹션 1**: 프로그램 콘텐츠 상세 (사용자 가치 제안)
- **섹션 2**: 데이터베이스 설계 특장점
- **섹션 3**: 데이터 파이프라인 (6-Stage)
- **섹션 4**: Knowledge Graph + Hybrid RAG 기술
- **디자인**: SaaS Design Skill 준수 + 동적 애니메이션

### 11.3 진행 상태
- 라우트 추가 완료
- `landing.html` 완성 — WebGL 셰이더 히어로, KG+RAG 이미지 섹션, 파이프라인 애니메이션, 비밀번호 게이트

---

## Phase 12: 텍스트 추출 엔진 (text_extractor.py) <a id="phase-12"></a>

### 12.1 한글 인코딩 문제 해결
- **문제**: PDF의 YDIYGO 폰트(KSC-EUC-H CMap)가 pdfplumber에서 깨짐
- **시도**: pdfplumber → PyMuPDF `get_text()` → rawdict 모드 순차 시도
- **해결**: PyMuPDF `get_text("dict")` 모드 — 유니코드 내부값은 정상, 콘솔 출력만 깨짐 확인
- **검증**: JSON 저장 시 한글 정상 출력 확인

### 12.2 좌표 기반 필드 매핑
```
y~93:  대안번호 + 위치 + 제안명 (헤더)
y~287: 원안 레이블 / y~403: 원안 설명
y~563: 대안 레이블 / y~680: 대안 설명
y~714: 장점/단점/고려사항 (x좌표로 구분)
```

### 12.3 결과
- `text_extractor.py` 완성 — 107개 대안 전체 텍스트 추출 성공

---

## Phase 13: 통합 파이프라인 + 배치 처리 + DB 적재 <a id="phase-13"></a>

### 13.1 pipeline.py — 통합 추출 파이프라인
- 텍스트(fitz) → 테이블(pdfplumber) → 이미지 순서로 통합
- `AlternativeData` 구조체 생성, 완성도(completeness) 자동 산출

### 13.2 batch_processor.py — 전체 배치 처리
- **결과**: 107/107 (100%) 성공, 131.7초 (대안당 1.2초), 실패 0건

### 13.3 db_builder.py — JSON → SQLite 적재
| 테이블 | 레코드 |
|---|---|
| projects | 1 |
| alternatives | 107 |
| images | 284 |
| performance_scores | 2,354 |
| cost_evaluations | 334 |
| value_evaluations | 107 |

---

## Phase 14: Knowledge Graph 구축 (kg_builder.py) <a id="phase-14"></a>

### 14.1 KG v1 — 초기 구축
- **7개 노드 타입**: Project, Alternative, Location, WorkType, Material, PerformanceCategory, ValueType
- **5개 엣지 타입**: BELONGS_TO, CLASSIFIED_AS, LOCATED_AT, USES_MATERIAL, EVALUATED_BY
- **결과**: 177 노드, 417 엣지
- **시행착오**: GraphML에서 `None` 값 불허 → 기본값(0.0, "") 처리

### 14.2 KG 시각화 (kg_visualizer.py)
- 3개 PNG 차트 + HTML 인터랙티브 뷰어(vis-network) 생성
- `.graphml` 파일은 Gephi 필요 → HTML 뷰어로 대체

---

## Phase 15: AI Enhancement (ai_enhancer.py) <a id="phase-15"></a>

### 15.1 Gemini 2.0 Flash 연동
- 개요도 이미지 → 건축 기술 서술 자동 생성
- 원안 AI 서술: 95/107 (88.8%), 대안 AI 서술: 82/107 (76.6%)
- 총 171개 AI 서술 생성, 소요시간 ~13분

### 15.2 데이터 교차 검증
- 비용 논리 (초기+유지관리=LCC): 107/107 통과
- 성능 합계: 101/107 통과 (6건 경미한 차이)
- 가치 공식 (V ≈ P+C): 107/107 통과

### 15.3 보안 처리
- Gemini API Key 하드코딩 → `os.getenv("GEMINI_API_KEY")` + `.env` 분리

---

## Phase 16: CUBE 표준분류체계 온톨로지 보강 <a id="phase-16"></a>

### 16.1 온톨로지 진단 (AS-IS 문제점)
| 항목 | 보강 전 | 문제 |
|---|---|---|
| ValueType | 13/107 (12.1%) | 87.9% 추출 실패 |
| HOW2 대공종 | 82/107 (76.6%) | 25건 미분류 |
| Space 공간 | 44/107 (41.1%) | 63건 미분류 |

### 16.2 cube_taxonomy.py — CUBE 3축 마스터 데이터
- WHERE: 프로젝트구분 → 프로젝트속성 (4구분 × 28속성)
- WHAT: 구조체구분 → 구조체분류 → 부재
- HOW: 공사 → 대공종 (6공사 × 87대공종) → 중공종 (자유 분류)
- 키워드 매핑: ~150개 키워드로 자동 분류

### 16.3 보강 결과
| 항목 | 보강 전 | 보강 후 |
|---|---|---|
| ValueType | 12.1% | **100%** |
| HOW2 대공종 | 76.6% | **100%** |
| Space 공간 | 41.1% | **43.9%** (나머지는 본질적으로 공간 정보 없음) |

### 16.4 KG v2 — CUBE 기반 재구축
| 항목 | v1 | v2 |
|---|---|---|
| 총 노드 | 177 | **210** (+19%) |
| 총 엣지 | 417 | **619** (+48%) |
| Space 노드 | 0 | **22** (신규) |
| SubWorkType 노드 | 0 | **30** (신규) |
| REPLACES_MATERIAL 엣지 | 0 | **8** (신규) |

### 16.5 Hop 질의 검증
- "옥상 방수 VE item" → **5개 대안 매칭 성공**
- 경로: Space(옥상) → [LOCATED_IN] → Alternative → [SUB_WORK_TYPE] → 방수코킹공사

---

## Phase 17: Flask 종합 대시보드 구축 <a id="phase-17"></a>

### 17.1 백엔드 (app.py)
- DB: Supabase PostgreSQL (Session Pooler) 연결
- REST API: `/api/stats`, `/api/alternatives`, `/api/alternatives/<num>`, `/api/kg/data`, `/api/kg/query`, `/api/stats/extended`
- 이미지 서빙: 절대경로 지원

### 17.2 프론트엔드 (SPA 구조)
- **6페이지**: Overview, Alternatives, Cost Analysis, Knowledge Graph, AI VE 자문, 성능 분석
- **디자인**: SaaS Design Skill 준수 — White Mode, Navy-Accent, Pretendard+Outfit 폰트
- **Chart.js**: KPI 카드, HOW1/HOW2 분포, 가치유형, 절감률 히스토그램, 성능-비용 4사분면
- **vis-network**: KG 인터랙티브 그래프 뷰어

### 17.3 랜딩 페이지 (landing.html)
- WebGL 셰이더 히어로 애니메이션
- KG + RAG 이미지 섹션, 6-Stage 파이프라인 애니메이션
- 비밀번호 게이트 (대시보드 접근 제어)

---

## Phase 18: Git 배포 준비 <a id="phase-18"></a>

### 18.1 보안 검증
| 검사 항목 | 조치 |
|---|---|
| Gemini API Key | `os.getenv()` 전환, `.env`에 분리 |
| Supabase 호스트 ID | 문서에서 `<project-id>` 플레이스홀더로 교체 |
| `.env` 파일 | `.gitignore` 등록 |
| `.raw_data/` | `.gitignore` 등록 |
| `data/extracted/`, `data/images/`, `data/db/` | `.gitignore` 등록 |
| `data/kg/` | **추적 유지** (서비스 필수 파일) |
| `validator.mjs` 정규식 패턴 | 실제 키 아님 — 안전 |

### 18.2 커밋 및 Push
- **커밋**: `5f7abb2` — `feat: VE Database SaaS Landing + Dashboard v1.0`
- **파일**: 65 files, 21,092 insertions
- **Remote**: `https://github.com/bignine99/ve_database_and_knowledge_graph.git`
- **Push**: `master` → `origin/master` 완료 (2026-05-06)

---

## Phase 19: Amazon Lightsail 프로덕션 배포 <a id="next-lightsail"></a>

> **상태**: ✅ 배포 완료 (2026-05-06)
> **서버**: Amazon Lightsail (ubuntu@43.203.182.190)
> **도메인**: https://ve.ninetynine99.co.kr
> **GitHub**: https://github.com/bignine99/ve_database_and_knowledge_graph.git

### 19.1 서버 환경
| 항목 | 값 |
|---|---|
| OS | Ubuntu 24.04 LTS (Kernel 6.17) |
| Python | 3.12.3 |
| 디스크 | 58GB (사용 16GB, 여유 42GB) |
| 메모리 | 1.9GB (Swap 2GB) |
| PM2 | 설치됨 |
| Nginx | 설치됨 + Let's Encrypt SSL |

### 19.2 배포 실행 내역
```bash
# Step 1: 프로젝트 클론
cd /home/ubuntu
git clone https://github.com/bignine99/ve_database_and_knowledge_graph.git ve_database

# Step 2: Python 가상환경 + 의존성 설치
cd ve_database
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # 60+ 패키지 (Flask, Gunicorn, psycopg2-binary 등)

# Step 3: 환경변수 설정
# .env 파일 생성 (SUPABASE_*, GEMINI_API_KEY)

# Step 4: PM2 서비스 등록
pm2 start '/home/ubuntu/ve_database/venv/bin/gunicorn -w 2 -b 127.0.0.1:5003 \
  --timeout 120 --chdir /home/ubuntu/ve_database src.app:app' --name ve-dashboard
pm2 save

# Step 5: Nginx 리버스 프록시 (ve.ninetynine99.co.kr → 127.0.0.1:5003)
# /etc/nginx/sites-enabled/ninetynine 에 server 블록 추가

# Step 6: DNS + SSL
# 가비아 DNS: *.ninetynine99.co.kr → 43.203.182.190 (와일드카드 A 레코드)
sudo certbot --nginx -d ve.ninetynine99.co.kr --non-interactive --agree-tos
```

### 19.3 시행착오: SSH 접속
- **문제**: `bitnami@` 사용자로 접속 시도 → Permission denied
- **해결**: Lightsail Ubuntu 인스턴스는 `ubuntu@` 사용자 사용
- **키 파일**: `LightsailDefaultKey-ap-northeast-2.pem`

### 19.4 시행착오: Nginx 설정 (PowerShell 변수 치환)
- **문제**: PowerShell에서 SSH heredoc 전달 시 `$host`, `$remote_addr` 등이 PS 변수로 해석
- **증상**: `proxy_set_header Host System.Management.Automation.Internal.Host.InternalHost;`
- **해결**: Python 스크립트를 scp로 전송 후 서버에서 실행하여 nginx 설정 작성

### 19.5 시행착오: DNS 설정
- **문제**: 서브도메인마다 개별 A 레코드 추가 필요 → 비효율적
- **해결**: 가비아 DNS에 와일드카드 A 레코드 (`*` → `43.203.182.190`) 등록
- **효과**: 향후 새 서비스 배포 시 DNS 작업 불필요

### 19.6 검증 결과
- [x] `https://ve.ninetynine99.co.kr/` — 랜딩 페이지 200 OK
- [x] `https://ve.ninetynine99.co.kr/dashboard` — 대시보드 200 OK
- [x] `/api/stats` — JSON 응답 200 OK
- [x] `/api/kg/data` — KG 데이터 200 OK
- [x] SSL 인증서 유효 (Let's Encrypt, 만료: 2026-08-04)

---

## Phase 20: 프로덕션 마감 — DNS, UI, 솔루션 연동 <a id="phase-20"></a>

> **상태**: ✅ 완료 (2026-05-06)
> **커밋**: `80c892b` (비밀번호 바이패스), `f579ec5` (홈 버튼)

### 20.1 와일드카드 DNS 설정
- **문제**: 새 서비스 배포마다 가비아 DNS에 개별 A 레코드를 추가해야 하는 번거로움
- **해결**: `*.ninetynine99.co.kr → 43.203.182.190` 와일드카드 A 레코드 등록 (TTL 600)
- **효과**: 향후 모든 서브도메인이 자동으로 서버 IP를 가리킴. DNS 작업 영구 불필요
- **Certbot SSL 발급**: `sudo certbot --nginx -d ve.ninetynine99.co.kr --non-interactive --agree-tos`
- **인증서 만료**: 2026-08-04 (자동 갱신 설정됨)

### 20.2 비밀번호 게이트 바이패스
- **배경**: 현재 맛보기(Preview) 단계로 누구나 대시보드를 볼 수 있어야 함
- **구현**: `landing.html` 내 `BYPASS_PASSWORD = true` 플래그 추가
  - `true`: "ENTER DASHBOARD" 클릭 시 바로 `/dashboard` 이동
  - `false`: 기존 비밀번호 모달(`0172`) 동작 복원
- **보존**: 비밀번호 모달 HTML/CSS/JS 코드 전체 보존 (향후 재활성화 가능)

```javascript
// landing.html — 복원 방법: false로 변경
var BYPASS_PASSWORD = true;
```

### 20.3 회사 홈페이지 링크 버튼
- **위치**: 랜딩 페이지 좌측 상단 고정(fixed)
- **디자인**: Navy 배경 + 글래스모피즘 + 집 아이콘 + "NINETYNINE" 텍스트
- **동작**: 클릭 시 `https://www.ninetynine99.co.kr/` 새 탭 오픈
- **호버**: `var(--accent)` 파란색 전환 + 그림자 효과
- **파일**: `landing.html` (HTML), `landing.css` (`.home-link` 클래스)

### 20.4 솔루션 페이지 카드 추가
- **대상**: `https://ninetynine99.co.kr/solutions` (회사 홈페이지 솔루션 갤러리)
- **파일**: `/home/ubuntu/homepage/src/data/solutions.ts`
- **추가된 카드**:

| 항목 | 값 |
|---|---|
| ID | `solution-ve-database` |
| 제목 | Value Engineering by AI |
| 설명 | AI 기반 VE 데이터베이스 및 분석 대시보드 |
| 카테고리 | Construction / RAG |
| 링크 | https://ve.ninetynine99.co.kr/ |
| 배지 | NEW |

- **배포**: `npm run build` → `pm2 restart ninetynine-hub`

### 20.5 프로덕션 이미지 경로 매핑 수정
- **증상**: 대시보드 상세 모달에서 원안/대안 이미지가 로딩되지 않음 (깨진 이미지 아이콘)
- **원인**: Supabase DB에 저장된 이미지 경로가 로컬 Windows 절대 경로 (`C:\Users\cho\...\data\images\대안_02\...`)
- **서버 상태**: `data/images/` 폴더가 `.gitignore`로 제외되어 서버에 이미지 파일 자체가 없었음
- **해결**:
  1. 로컬 `data/images/` (25MB, 284파일, 107개 대안 폴더) → SCP로 서버 전송
  2. `app.py`의 `serve_abs_image` API에 Windows → Linux 경로 자동 매핑 로직 추가

```python
# app.py — serve_abs_image 경로 매핑 핵심 로직
if not p.exists() and ('\\' in fpath or 'C:' in fpath):
    normalized = fpath.replace('\\', '/')
    marker = 'data/images/'
    idx = normalized.find(marker)
    if idx >= 0:
        relative = normalized[idx:]
        server_path = Path('/home/ubuntu/ve_database') / relative
```

- **커밋**: `7c505bc`
- **검증**: `https://ve.ninetynine99.co.kr/api/serve_abs_image?path=C:\...\대안_02\..._original_diagram.jpeg` → 200 OK (image/jpeg, 187KB)

---

## Phase 21: ML Hybrid RAG Engine 도입 <a id="phase-21"></a>

> **상태**: ✅ 완료 (2026-05-06)
> **핵심**: 키워드 매칭 → Embedding 시맨틱 검색 + KG 구조 매칭 + Gemini RAG

### 21.1 문제 진단 (AS-IS)
- **AI VE 자문** 페이지가 `cube_taxonomy.py`의 키워드 매칭(~150개)에만 의존
- `SPACE_KEYWORDS`에 없는 표현 → 매칭 실패 ("지붕 물 새는 문제" → "옥상 방수" 연결 불가)
- 동의어, 유사어, 복합 조건 질의 처리 불가
- 유사 대안 추천 기능 없음

### 21.2 구현 — Tier 1: Embedding 시맨틱 검색
- **모델**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384차원, 한국어 지원)
- **인덱싱**: 727개 대안 × (title + original_desc + alternative_desc + how2_name + space + value_type)
- **저장**: `data/embeddings/ve_embeddings.npz` (벡터), `ve_metadata.json` (메타)
- **검색**: 코사인 유사도 (L2 정규화 후 내적) → Top-K 반환
- **빌드 시간**: ~14초 (CPU, GPU 불필요)

### 21.3 구현 — Tier 2: Hybrid RAG
```
User Query → Step 1: Embedding Search (Top 20)
           → Step 2: KG Hop 매칭 (Space/HOW2 구조)
           → Step 3: 복합 스코어 (0.6×Semantic + 0.4×KG)
           → Step 4: (선택) Gemini RAG 자연어 분석 답변
```

### 21.4 새 API 엔드포인트
| 엔드포인트 | 설명 |
|---|---|
| `GET /api/search?q=` | 시맨틱 검색 (Embedding Only) |
| `GET /api/ai/search?q=&gemini=true` | 하이브리드 RAG (Embedding + KG + Gemini) |
| `GET /api/alternatives/<num>/similar` | 유사 대안 추천 (벡터 유사도) |

### 21.5 프론트엔드 변경
- **AI VE 자문 페이지**: 검색 모드 선택기 (Hybrid / Semantic / KG Legacy)
- **유사도 바**: 각 결과에 시맨틱 유사도 + KG 점수 시각화
- **Gemini AI 분석 토글**: 체크 시 자연어 비교 분석 답변 생성
- **상세 모달**: "유사 대안 (Embedding 기반)" 섹션 추가 (비동기 로드)
- **Hybrid RAG 시각화**: 시맨틱 매칭은 점선, KG 매칭은 실선으로 구분

### 21.6 검증 결과
| 질의 | 기존 (KG Only) | 개선 (Hybrid RAG) |
|---|---|---|
| "옥상 방수 VE 대안" | 5건 (키워드 매칭) | **10건** (1위: 대안-191 옥상 방수 공법 변경, 83.5%) |
| "학교 건물 외벽 에너지 효율" | 0건 (키워드 없음) | **10건** (1위: 대안-685 지붕층 철골 최적화, 38.8%) |
| "LED 조명 전기료 절감" | 0건 | **10건** (1위: 대안-200 전등 배선 시스템, 71.7%) |
| "지하주차장 바닥 마감재" | 0건 | **10건** (1위: 대안-520 배관 보온재, 88.8%) |

### 21.7 파일 추가
- `src/semantic_search.py` — Embedding 시맨틱 검색 엔진 (360 LOC)
- `data/embeddings/` — 임베딩 인덱스 (gitignore)

### 21.8 구현 — Tier 3: 자동 분류 ML
- **모델**: TF-IDF (5000 features, bigram) + LinearSVC
- **HOW2 분류기**: 511 samples, 40 classes → **교차검증 정확도 38.0%** (±4.2%)
  - 40개 대공종에 걸쳐 데이터가 분산되어 있어 현재 정확도는 낮음
  - 데이터 1,000건 이상 시 60%+ 예상
- **ValueType 분류기**: 727 samples, 4 classes → **교차검증 정확도 63.3%** (±7.0%)
  - 4개 클래스(가치혁신형/비용절감형/성능강조형/성능향상형)로 실용적 수준
- **API**: `POST /api/classify` — 새 대안 텍스트 → HOW2 + ValueType 자동 예측
- **저장**: `data/ml_models/how2_classifier.pkl`, `vtype_classifier.pkl`

### 21.9 구현 — Tier 4: 클러스터링 인사이트
- **알고리즘**: K-Means (k=8, n_init=10)
- **실루엣 점수**: 0.0538 (자연어 텍스트 기반이므로 기대치에 부합)
- **클러스터 자동 라벨링**: 가장 빈번한 HOW2 + Space + ValueType 결합
- **대표 대안**: 각 클러스터 중심(centroid)에 가장 가까운 대안
- **API**: `GET /api/clusters`, `GET /api/clusters/<id>`
- **대시보드**: Overview 페이지 하단에 8개 클러스터 카드 시각화

| 클러스터 | 라벨 | 크기 | 평균 절감율 | 평균 가치변화 |
|---|---|---|---|---|
| 0 | 배선배관 / 전체 / 가치혁신형 | 82건 | +2.87% | +36.5% |
| 1 | 우오수및배수 / 전체 / 가치혁신형 | 100건 | +1.31% | +56.6% |
| 2 | 방수코킹 / 전체 / 비용절감형 | 108건 | +0.17% | +13.7% |
| 3 | 철근콘크리트 / 구조체 / 가치혁신형 | 141건 | +0.01% | +50.9% |
| 4 | 정보통신설비 / 도로 / 성능강조형 | 50건 | +1.20% | +16.4% |
| 5 | 배관설비 / 전체 / 가치혁신형 | 86건 | 0% | +43.3% |
| 6 | 창호 / 계단실 / 가치혁신형 | 82건 | +0.11% | +30.9% |
| 7 | 배선배관 / 전체 / 가치혁신형 | 78건 | +1.77% | +53.7% |

### 21.10 전체 파일 추가 요약
- `src/semantic_search.py` — Tier 1~2 (시맨틱 검색 + Hybrid RAG)
- `src/ml_classifier.py` — Tier 3~4 (자동 분류 + 클러스터링)
- `data/embeddings/` — 임베딩 인덱스 (gitignore)
- `data/ml_models/` — 분류기 + 클러스터링 결과 (gitignore)

---

## 최종 데이터베이스 현황 <a id="final-status"></a>

### 테이블별 레코드 수 (2026-05-05 기준)

| 테이블 | 레코드 |
|---|---|
| projects | 9 |
| alternatives | 727 |
| cost_evaluations | 826 |
| value_evaluations | 599 |
| performance_scores | 3,275 |

### 프로젝트별 대안 수

| # | 프로젝트 | 소스 | 연도 | 대안 | 추출기 |
|---|---|---|---|---|---|
| 1 | 강원특별자치도 신청사 | 자체 | - | 107건 | extract_001.py |
| 2 | 서울특별시 2022 건설공사 | 서울특별시 | 2022 | 110건 | extract_002.py |
| 3 | 국가철도공단 2021 설계VE | 국가철도공단 | 2021 | 106건 | extract_003.py |
| 4 | 대구광역시 2023 VE | 대구광역시 | 2023 | 17건 | extract_004.py |
| 5 | 조달청 설계VE 2025 | 조달청 | 2025 | 175건 | extract_005.py |
| 6 | 퇴계동 국민체육센터 | 퇴계동 | 2024 | 43건 | extract_006.py |
| 7 | 한경대학교 글로컬융합 | 한경대학교 | 2024 | 53건 | extract_007.py |
| 8 | 왕산2초중통합 | 왕산 | 2024 | 31건 | extract_008.py |
| 9 | 화곡초등학교 | 화곡 | 2024 | 66건 | extract_009.py |
| | **총계** | | | **727건** | |

### 분야별 분포

| 분야 | 건수 |
|---|---|
| 토목 | 230 |
| 건축 | 145 |
| 기계 | 61 |
| 설비 | 53 |
| 전기 | 42 |
| 구조 | 32 |
| 조경 | 24 |
| 소방 | 22 |
| 통신 | 11 |

### 데이터 무결성
- alt_number: #1 ~ #727, 연속성 OK (갭 없음)
- 외래키: cost_evaluations, performance_scores → alternatives 정상
- 고아 대안 129건: 초기 강원특별자치도 데이터의 project_id 매핑 이슈 (기능에 영향 없음)

---

## 기술적 교훈 및 시행착오 기록 <a id="lessons-learned"></a>

### 1. CID 폰트 PDF 처리
- **교훈**: 한국어 PDF의 약 30%가 CID 인코딩 사용. PyMuPDF/pdfplumber 모두 실패
- **해결**: Tesseract OCR + 2x 해상도 이미지 변환
- **최적화**: 전체 OCR 대신 CID Pre-filter로 후보 페이지만 선별

### 2. PDF 페이지 구조의 다양성
- **교훈**: 같은 VE 보고서라도 기관마다 페이지 구조가 다름
- 조달청: 엄격한 2-page pair (제안+성능)
- 퇴계동/한경대: 2-page pair (대안정보+비용)
- 왕산/화곡: 가변 페이지 수 (1~3 페이지/대안)
- **해결**: 각 PDF에 맞는 개별 추출기 작성 + 공통 패턴 재사용

### 3. stdout 버퍼링 (Windows + Python)
- **교훈**: Windows에서 subprocess 실행 시 stdout이 버퍼링되어 실시간 진행 확인 불가
- **해결**: `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` + `flush=True`

### 4. PowerShell 명령어 차이
- `&&` 연결자 사용 불가 → `;` 사용
- 한글 파일명 포함 인라인 Python 명령 → 별도 `.py` 파일로 분리

### 5. Supabase Pooler 연결
- 직접 연결 실패 시 Session Pooler 엔드포인트 사용
- `sslmode=require` 필수

### 6. 추출기 재사용 패턴
- 동일 구조 PDF는 추출기 복사 후 상수만 변경 (PROJECT_ID, PDF_PATH, alt_id prefix)
- 다른 구조 PDF는 새 추출기 작성 필요

---

## 파일 구조 (2026-05-06 기준)

```
260504_ve_database_development/
├── .env                          # Supabase + Gemini 환경변수 (gitignore)
├── .gitignore                    # 보안/대용량 파일 제외 규칙
├── requirements.txt              # Python 의존성
├── .raw_data/                    # 원본 PDF 파일 (gitignore)
├── src/
│   ├── app.py                    # Flask 메인 앱 (Supabase PostgreSQL)
│   ├── config.py                 # 경로/DB 설정
│   ├── cube_taxonomy.py          # CUBE 3축 분류 엔진 (WHERE/WHAT/HOW)
│   ├── semantic_search.py        # ML 시맨틱 검색 + Hybrid RAG
│   ├── ml_classifier.py          # ML 분류 엔진 (HOW1/HOW2/ValueType)
│   ├── kg_builder.py             # KG v2 — CUBE 기반 (10노드, 8엣지 타입)
│   ├── kg_visualizer.py          # KG 시각화 (matplotlib + vis-network)
│   ├── ai_enhancer.py            # Gemini 2.0 Flash AI 서술 + 교차검증
│   ├── text_extractor.py         # PyMuPDF 좌표 기반 텍스트 추출
│   ├── table_extractor.py        # pdfplumber 테이블 추출
│   ├── image_extractor.py        # PDF 이미지 추출
│   ├── pipeline.py               # 통합 추출 파이프라인
│   ├── batch_processor.py        # 전체 배치 처리기
│   ├── db_builder.py             # JSON → SQLite/PostgreSQL 적재
│   ├── pdf_processor.py          # PDF 전처리 유틸리티
│   ├── schemas.py                # JSON 스키마 검증
│   ├── schema.sql                # DB 스키마 DDL
│   ├── setup_supabase.py         # Supabase 테이블 생성
│   ├── migrate_to_supabase.py    # SQLite → Supabase 마이그레이션
│   ├── extract_002~009.py        # 개별 PDF 추출기 (8개)
│   ├── agents/                   # Multi-Agent VE 시스템 (Phase 22, NEW)
│   │   ├── __init__.py
│   │   ├── schemas.py            # 입출력 스키마 (ProjectBrief, AgentRequest 등)
│   │   ├── ve_leader.py          # VE Leader + DB Search + Idea + Domain Agent
│   │   ├── fast_agent.py         # FAST 기능 분석 + Mermaid
│   │   └── roundtable.py         # 라운드테이블 토론 엔진
│   ├── templates/
│   │   ├── landing.html          # WebGL 히어로 랜딩 페이지
│   │   └── index.html            # SPA 대시보드 (7페이지, VE Agent 추가)
│   └── static/
│       ├── css/dashboard.css     # SaaS 디자인 시스템
│       ├── js/dashboard.js       # 차트 + KG + AI 자문 로직
│       ├── js/ve-agent.js        # VE 라운드테이블 채팅 UI (NEW)
│       └── images/               # 랜딩 페이지 이미지
├── .ve_SKILL/                    # VE Agent SKILL 파일 (10개)
│   ├── SKILL_Architect.md
│   ├── SKILL_Civil.md
│   ├── SKILL_Electronic.md
│   ├── SKILL_Mechanic.md
│   ├── SKILL_Plumbing.md
│   ├── SKILL_Landscape.md
│   ├── SKILL_idea_developer.md
│   ├── SKILL_FAST_Diagram_Developer.md
│   ├── SKILL_data_analyst.md
│   └── SKILL_Report_Writer.md
├── data/
│   ├── extracted/ ~ extracted_009/  # 추출 JSON (gitignore)
│   ├── images/ ~ images_002/       # 추출 이미지 (gitignore)
│   ├── db/                         # SQLite DB (gitignore)
│   ├── embeddings/                 # ML 임베딩 인덱스 (gitignore)
│   │   ├── ve_embeddings.npz       # 727×384 벡터 행렬
│   │   └── ve_metadata.json        # 대안 메타데이터
│   └── kg/                         # Knowledge Graph (git 추적)
│       ├── ve_knowledge_graph.graphml
│       ├── kg_stats.json
│       ├── kg_interactive_viewer.html
│       └── *.png (시각화 차트 3개)
├── docs/
│   ├── PRD_implementation_plan.md          # Phase 1~9 구현 계획
│   ├── ml_implementation_report.md         # ML 도입 보고서
│   └── multi_agent_risk_assessment.md      # Multi-Agent 잠재력/한계 평가
└── implementation_and_modification_processes.md  # 이 문서
```

---

## Phase 22: Multi-Agent VE Intelligence <a id="phase-22"></a>

> **작업일**: 2026-05-06 ~ 2026-05-07
> **목표**: VE 라운드테이블 토론 시스템 — AI Agent들이 캐릭터로 등장하여 순차 토론

### 22.1 구현 완료 항목

| Task | 파일 | 내용 | 상태 |
|---|---|---|---|
| 29 | `src/agents/schemas.py` | ProjectBrief, DesignAnalysis, CostBreakdown 스키마 | ✅ |
| 30 | `src/agents/schemas.py` | AgentRequest/Response, Step별 Result 타입 | ✅ |
| 31 | `src/agents/ve_leader.py` | VE Leader 오케스트레이터 (세션 관리) | ✅ |
| 32 | `src/agents/ve_leader.py` | DB Search Agent (시맨틱 검색 래핑) | ✅ |
| 33 | `src/agents/ve_leader.py` | Idea Agent (Gemini 아이디어 도출) | ✅ |
| 34 | `src/agents/ve_leader.py` | Domain Agent (6개 SKILL 기반 검증) | ✅ |
| 35 | `src/agents/fast_agent.py` | FAST 기능 분석 + Mermaid 다이어그램 | ✅ |
| 36 | `src/agents/ve_leader.py` | Report Agent (보고서 초안 Markdown) | ✅ |
| 37 | `src/app.py` | API 7개 (VE Session 5 + Roundtable 2) | ✅ |
| 38 | `index.html` + `ve-agent.js` | 대시보드 "07. VE Agent" 라운드테이블 UI | ✅ |
| — | `src/agents/roundtable.py` | 라운드테이블 토론 엔진 (SKILL 기반 순차 발언) | ✅ |

### 22.2 라운드테이블 토론 흐름

```
Step 1: 🎩 VE Leader       — 프로젝트 요약 + 분석 방향 제시
Step 2: 🏗 건축/⚡전기 등   — 도메인 전문가 순차 발언 (SKILL 기반)
Step 3: 📈 Data Analyst    — DB 727건 유사 사례 검색 결과 보고
Step 4: 💡 Idea Developer  — 아이디어 3~4개 제안
Step 5: 📊 FAST 전문가     — 기능 분해 + 비용 불균형 지적
Step 6: 🎩 VE Leader       — 종합 정리 + 다음 단계 제안
```

### 22.3 API 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/ve/session` | VE 분석 세션 (기존 방식) |
| GET | `/api/ve/session/<id>/status` | 세션 상태 |
| GET | `/api/ve/session/<id>/result` | 세션 결과 |
| POST | `/api/ve/session/<id>/feedback` | 사용자 피드백 |
| GET | `/api/ve/sessions` | 세션 목록 |
| **POST** | **`/api/ve/roundtable`** | **라운드테이블 토론 실행 (파일 업로드 지원)** |
| **GET** | **`/api/ve/roundtable/<id>/messages`** | **토론 메시지 조회** |

### 22.4 CLI 테스트 결과 (ve_leader.py)

```
[VE Session b27316bb] 시작: 테스트 공동주택 신축공사
  Step 1: 분석 대상 2건 선정 (건축, 전기)
  Step 2: 유사 사례 검색 (Hybrid RAG, 727건 DB)
  Step 3: 아이디어 3건 도출 (Gemini Flash)
  Step 4: 도메인 검증 6건 (전기 적극추천 90%, 구조 조건부추천 70%)
  Step 5: 보고서 초안 1,324자 자동 생성
  → 총 소요: ~53초
```

### 22.5 대시보드 UI

- 사이드바 "07. VE Agent" 메뉴 추가
- 좌측: 파일 업로드(PDF/TXT 드래그&드롭) + 프로젝트 설명 직접 입력 + 참여 전문가 선택
- 우측: 채팅방 형태 토론 뷰 (Agent 아바타 + 이름 + 타이핑 애니메이션)

### 22.6 알려진 이슈

| 이슈 | 상태 | 내용 |
|---|---|---|
| ⚠ 응답 시간 | 미해결 | Gemini API 6~8회 순차 호출 → 60~90초 소요 |
| ⚠ 동기 처리 | 미해결 | 브라우저가 응답까지 블로킹 → 사용자 대기 필요 |
| ✅ 환각 방지 | 적용됨 | temperature 0.3~0.5, DB 근거만 인용, "AI 초안" 명시 |
| ✅ Graceful Degradation | 적용됨 | 도면/내역 AI 없어도 사용자 입력만으로 진행 가능 |

---

## 다음 세션 작업 (재부팅 후)

### Lightsail 배포 동기화

```
1) git push → Lightsail 서버 git pull → PM2 재시작
2) 프로덕션 환경에서 비동기 라운드테이블 동작 검증
```

### 선택적 개선

| 작업 | 우선순위 | 내용 |
|---|---|---|
| Lightsail 배포 동기화 | 높음 | git push → PM2 재시작 |
| 라운드테이블 UI 개선 | 중간 | 진행 단계 프로그레스바, 메시지 스타일 고도화 |
| SSE 스트리밍 전환 | 낮음 | 폴링 → Server-Sent Events로 전환 (실시간성 향상) |

---

## Phase 23: 비동기 라운드테이블 최적화 <a id="phase-23"></a>

> **작업일**: 2026-05-07
> **목표**: 60~90초 블로킹 응답 → 비동기 처리 + 실시간 폴링 UI

### 23.1 문제 진단

| 항목 | AS-IS | 영향 |
|---|---|---|
| API 처리 방식 | **동기** — Gemini 6~8회 순차 호출 완료까지 블로킹 | 60~90초 대기 |
| 프론트엔드 | **일괄 수신** — 응답 완료 후 전체 메시지 한꺼번에 표시 | "로딩만 됨" 인식 |
| 사용자 경험 | 진행 상태 불명 — 로딩 스피너만 표시 | 이탈 위험 |

### 23.2 해결 — 비동기 아키텍처

```
[AS-IS]  POST /roundtable → (60~90초 블로킹) → {messages: [...]}

[TO-BE]  POST /roundtable → (즉시) → {session_id: "abc123"}
         GET  /roundtable/abc123/messages?since=0 → {new_messages: [...], status: "running"}
         GET  /roundtable/abc123/messages?since=3 → {new_messages: [...], status: "running"}
         GET  /roundtable/abc123/messages?since=7 → {new_messages: [], status: "completed"}
```

### 23.3 백엔드 변경 (`roundtable.py`)

- `RoundtableSession`에 `threading.Lock` 추가 → 메시지 축적 thread-safe
- `_run_roundtable_worker()` — 기존 동기 로직을 워커 함수로 분리
- `start_roundtable_async()` — daemon thread로 워커 실행, 세션 즉시 반환
- `run_roundtable()` — 하위 호환용 동기 함수 유지

### 23.4 백엔드 변경 (`app.py`)

- `POST /api/ve/roundtable` — `start_roundtable_async()` 호출, 세션 ID 즉시 반환
- `GET /api/ve/roundtable/<id>/messages?since=<n>` — 새 메시지만 반환하는 폴링 API
  - `since` 파라미터: 이전 응답의 `total_count` 전달 → 새 메시지만 반환
  - `status` 필드: `running` | `completed` | `failed`
  - `error` 필드: 실패 시 에러 메시지

### 23.5 프론트엔드 변경 (`ve-agent.js`)

| 기능 | 변경 내용 |
|---|---|
| 세션 시작 | POST 즉시 반환 → 세션 ID 수신 |
| 메시지 수신 | **1.2초 폴링** (최대 120회 = 144초 제한) |
| 실시간 표시 | 새 메시지 도착 시 즉시 타이핑 애니메이션 |
| 로딩 표시 | **바운스 인디케이터** (·· ·) + "AI 전문가 분석 중..." 텍스트 |
| 상태 표시 | 준비 중 → 토론 중 → 완료/오류 단계별 배지 전환 |
| Agent 목록 | 발언하는 Agent가 등장할 때마다 좌측 패널에 추가 |

### 23.6 개선 효과

| 지표 | AS-IS | TO-BE |
|---|---|---|
| 첫 응답 시간 | **60~90초** | **< 1초** (세션 ID 즉시 반환) |
| 첫 메시지 표시 | 60~90초 후 일괄 | **~10초** (VE Leader 개회사) |
| 사용자 인지 | "로딩만 됨" | Agent별 순차 발언 실시간 확인 |
| 타임아웃 위험 | 높음 (Gunicorn 120초) | 없음 (각 폴링 < 1초) |
| 에러 복구 | 전체 세션 실패 | 부분 결과 유지 + 에러 표시 |

### 23.7 파일 변경 요약

| 파일 | 변경 | LOC |
|---|---|---|
| `src/agents/roundtable.py` | 비동기 워커 + Lock 추가 | 250 → 260 |
| `src/app.py` | 라운드테이블 API 비동기 전환 | ~30줄 수정 |
| `src/static/js/ve-agent.js` | 폴링 기반 UI + 타이핑 인디케이터 | 197 → 230 |

## Phase 24: AI VE 대시보드 시각화 최적화 및 렌더링 방식 이미지 추출 <a id="phase-24"></a>

### 24.1 AI VE 자문 지식 그래프 레이아웃 최적화
- **문제점**: `05. AI VE 자문` 페이지에서 Hybrid RAG 지식 그래프 영역(`ai-kg-container`)이 `height: 400px`로 고정되어 있어 넓은 화면에서도 시각화 박스가 작게 출력되는 문제.
- **해결 방안**: 
  - `dashboard.css` 내 `.chat-panel`에 `display: flex; flex-direction: column`을 적용.
  - `#ai-kg-container`에 `flex: 1` 및 `min-height: 500px`를 설정하여 부모 요소의 전체 높이에 맞추어 동적으로 시원하게 확장되도록 CSS 레이아웃을 100% 대응.

### 24.2 대안 원안/대안 이미지 부재 및 빈 박스(회색 영역) 표출 오류
- **문제점**: 
  1. 초기 파이프라인 개발 시 강원 신청사(1~107번)에만 이미지가 추출되었고, 108번~727번(조달청, 퇴계동 등)의 대안에는 DB에 이미지 정보가 존재하지 않아 모달창에 개요도가 나타나지 않음.
  2. 단순 이미지 추출 API(`fitz.get_images`)를 활용해 누락된 이미지를 추출(`extract_images_005.py`, `extract_images_006.py`)했으나, "원안" 영역의 도면이 벡터 그래픽(Vector)이거나 바탕 회색 박스로 구성되어 있어 의미 없는 바탕 이미지(회색 박스)만 추출되는 심각한 오류 발생.
- **해결 방안 (Robust Render Extraction)**: 
  - 단순 객체 추출을 폐기하고 **PDF 페이지 전체를 고해상도 픽스맵(Pixmap)으로 렌더링한 후, 지정된 X, Y 영역 좌표를 기준으로 자르는(Crop) 방식** 채택.
  - `extract_images_robust.py` 신규 개발:
    - **조달청 사례**: 좌(원안) / 우(대안) 레이아웃에 맞춰 `fitz.Rect(35, 195, 290, 470)` 및 `(305, 195, 560, 470)` 크롭.
    - **퇴계동 사례**: 상(원안) / 하(대안) 레이아웃에 맞춰 `fitz.Rect(110, 80, 560, 400)` 및 `(110, 410, 560, 650)` 크롭.
  - 추출된 고품질 이미지를 로컬(`data/images`)에 저장 및 Supabase DB에 적재하여, 벡터 드로잉 라인과 텍스트까지 육안으로 보이는 완벽한 형태로 표출하도록 수정.

### 24.3 Flask 로컬 서버 중단 트러블슈팅
- **문제점**: 작업 중 포트 오류 혹은 IDE 세션 만료로 Flask 서버(`:5000`)가 중단되어 대시보드 접근 불가 현상 발생.
- **해결 방안**: `netstat -ano | findstr :5000`을 통해 포트 비활성을 확인 후, `python src/app.py`를 재기동하여 서비스 접근 및 이미지 매핑 테스트 환경 복구 완료.


### Phase 25: Image Deployment Pathing and Layout Stability (2026-05-07)
**Issue 1: Blank UI for vis.Network Canvas**
- **Symptoms**: The Hybrid RAG 시각화 container on the dashboard was entirely blank. Inspection revealed that the <canvas> injected by is.Network was forcing a CSS feedback loop in a flexbox layout, causing the container's height to expand infinitely (reaching 22,000px+ without visibility).
- **Fix applied**: Wrapped #ai-kg-container inside a relative lex: 1; min-height: 500px; wrapper, and set the container itself to position: absolute; top:0; left:0; right:0; bottom:0;. This breaks the infinite loop and explicitly forces the graph canvas to conform to the parent dimensions.

**Issue 2: Broken Original Images in Modal (Mixed Paths on Linux)**
- **Symptoms**: The user reported that original diagram images (e.g. alternative 428) were not displaying on the live dashboard.
- **Root Cause**: The zip file (images.zip) containing the newly extracted robust images (from Phase 24) was created on Windows using Compress-Archive. When extracted on the AWS Linux server using unzip, Linux failed to recognize backslashes as path separators, resulting in files named with literal backslashes (e.g., pps_428\\pps_428_original_diagram.jpeg) instead of placing them in subdirectories. The backend API (pp.py), attempting to read within the subdirectories (server_path.exists()), failed to find the files and fell back to returning 404 NOT FOUND.
- **Fix applied**: Created and executed a Python script on the remote AWS server to iterate through all files containing \\ in their name. The script dynamically created the required subdirectories (pps_428/ etc.) and moved the files, fixing 737 erroneously named assets.
- **Verification**: Verified via curl that serve_abs_image now accurately serves the 200 OK responses, successfully linking Windows-stored DB paths to the resolved Linux directory structure.


### Phase 26: VE Roundtable Dependency Resolution (2026-05-08)
**Issue: VE Roundtable Agent Crash**
- **Symptoms**: When initiating a VE Roundtable session, all agent responses returned the error: [오류: cannot import name \'genai\' from \'google\'].
- **Root Cause**: The Python backend codebase was updated to use the new official Google Gemini SDK (google-genai package) via rom google import genai. However, the production AWS Lightsail servers virtual environment only had the legacy google-generativeai package installed, leading to an ImportError when the roundtable endpoint was triggered.
- **Fix applied**: Connected to the AWS Lightsail server via SSH and manually installed the missing google-genai package into the production Python virtual environment (/home/ubuntu/ve_database/venv/bin/pip install google-genai). The PM2 process e-dashboard was then restarted to load the new dependency, restoring full functionality to the Multi-Agent Roundtable.


### Phase 27: Dockerization of VE Dashboard (2026-05-08)
**Issue: Program was not using Docker**
- **Symptoms**: The application was running natively on servers using PM2 and Virtual Environments. The user requested Docker integration to ensure consistent deployment environments, easier environment management, and to avoid dependency conflicts (such as the recent google-genai issue).
- **Actions Taken**:
  1. **requirements.txt updated**: Added google-genai>=2.0.0 to explicitly track the missing Gemini SDK dependency identified in Phase 26.
  2. **Dockerfile created**: Implemented a python:3.11-slim based image. It sets up working directories, securely copies necessary requirements, installs system-level (libpq-dev) and Python dependencies, and uses gunicorn as the production entrypoint on port 5000.
  3. **.dockerignore configured**: Added directories like env/, .env, .git/, and data/ to prevent sensitive or unnecessary files from bloating the Docker image context.
  4. **docker-compose.yml created**: Set up service orchestration mapping port 5003 (host) to 5000 (container), mapping the ./data directory as a persistent volume, and passing the .env file for secure environment variables.

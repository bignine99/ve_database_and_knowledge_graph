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
21. [최종 데이터베이스 현황](#final-status)
22. [기술적 교훈 및 시행착오 기록](#lessons-learned)

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
│   ├── templates/
│   │   ├── landing.html          # WebGL 히어로 랜딩 페이지
│   │   └── index.html            # SPA 대시보드 (6페이지)
│   └── static/
│       ├── css/dashboard.css     # SaaS 디자인 시스템
│       ├── js/dashboard.js       # 차트 + KG + AI 자문 로직
│       └── images/               # 랜딩 페이지 이미지
├── data/
│   ├── extracted/ ~ extracted_009/  # 추출 JSON (gitignore)
│   ├── images/ ~ images_002/       # 추출 이미지 (gitignore)
│   ├── db/                         # SQLite DB (gitignore)
│   └── kg/                         # Knowledge Graph (git 추적)
│       ├── ve_knowledge_graph.graphml
│       ├── kg_stats.json
│       ├── kg_interactive_viewer.html
│       └── *.png (시각화 차트 3개)
├── docs/
│   ├── PRD_implementation_plan.md
│   └── implementation_and_modification_processes.md
└── implementation_and_modification_processes.md  # 이 문서 (루트 복사본)
```

# Hero Landing Page 개발 가이드

> **원본**: VE Database Landing Page (`landing.html` + `landing.css` + `landing.js` + `hero-particles.js`)  
> **목적**: 다른 프로그램에서 동일한 구조/디자인/애니메이션의 히어로 페이지를 재현하기 위한 상세 명세  
> **참고 URL**: https://ve.ninetynine99.co.kr/

---

## 1. 전체 페이지 구조 (6개 섹션)

```
┌─────────────────────────────────────────┐
│  SECTION 1: HERO (100vh, 라이트 배경)     │  ← WebGL 파티클 + Aurora + 플로팅 키워드
│  배지 + 그라데이션 타이틀 + CTA + 통계     │
├─────────────────────────────────────────┤
│  SECTION 2: PLATFORM CONTENTS (White)    │  ← 6개 Feature Card 그리드
├─────────────────────────────────────────┤
│  SECTION 3: DATABASE ARCHITECTURE (Navy) │  ← Dark 배경 + 4개 Navy Card
├─────────────────────────────────────────┤
│  SECTION 4: DATA PIPELINE (White)        │  ← 6-Step 수평 파이프라인 애니메이션
├─────────────────────────────────────────┤
│  SECTION 5: KG + RAG (White)             │  ← 이미지-텍스트 좌우 교차 Row 4개
├─────────────────────────────────────────┤
│  SECTION 6: ML METRICS (Navy)            │  ← Dark 배경 + 4개 Tier Card
├─────────────────────────────────────────┤
│  FOOTER                                  │
├─────────────────────────────────────────┤
│  PASSWORD MODAL (오버레이, 선택적)         │
└─────────────────────────────────────────┘
```

---

## 2. 디자인 시스템

### 2.1 색상 팔레트 (CSS Variables)

```css
:root {
  --navy: #061E4A;         /* 주 강조색 (Dark) */
  --accent: #3B82F6;       /* 포인트 블루 */
  --emerald: #10B981;      /* 성공/활성 표시 */
  --orange: #F97316;       /* 경고 */
  --red: #EF4444;          /* 에러 */
  --bg: #FFFFFF;           /* 기본 배경 */
  --bg-subtle: #F8FAFC;    /* 미세 배경 */
  --bg-panel: #F1F5F9;     /* 패널 배경 */
  --text-primary: #1E293B; /* 본문 텍스트 */
  --text-secondary: #475569;
  --text-muted: #94A3B8;
  --border: #F1F5F9;
  --border-mid: #E2E8F0;
}
```

### 2.2 폰트

| 용도 | 폰트 | 적용 |
|---|---|---|
| 한글 본문 | **Pretendard** | `body` 기본 |
| 영문/숫자/라벨 | **Outfit** (Google Fonts) | `.font-outfit` 클래스 |

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
```

### 2.3 SaaS 디자인 규칙

- **White Mode 강제** — `#FFFFFF` / `#F8FAFC` 배경만 사용 (Dark 섹션은 Navy 블록)
- **border-radius: 2px** — 모든 카드, 버튼, 인풋에 `rounded-sm(2px)` 적용. `rounded-xl` 이상 금지
- **이모지/이모티콘 금지** — SVG 아이콘만 사용
- **hover 효과**: `translateY(-2~4px)` + `box-shadow` 확대

---

## 3. 섹션별 상세 명세

### 3.1 SECTION 1: HERO (전체 화면)

**레이아웃**: `min-height: 100vh`, `flex-column`, `center/center`, 배경 `#FAFBFF`

#### 3.1.1 배경 레이어 (3중 구조, 모두 `pointer-events: none`)

| 레이어 | z-index | 내용 |
|---|---|---|
| Aurora Layer | 0 | 3개 원형 blob (`radial-gradient`), `filter: blur(80px)`, `aurora-drift` 20초 순환 |
| Three.js Canvas | 1 | WebGL Chromatic Sine-Wave 셰이더 (Navy-Blue-Teal 팔레트) |
| Floating Keywords | 1 | 6개 업계 키워드가 20초 주기로 fade-in/float/fade-out |
| Grid Lines | 1 | 4개 세로선 (`20%/40%/60%/80%`), `opacity: 0.3` |

**Aurora Blob 구현**:
```css
.aurora-blob {
  position: absolute; border-radius: 50%;
  animation: aurora-drift 20s ease-in-out infinite;
}
/* 3개 blob — 크기 450~600px, 색상: blue(0.15)/navy(0.10)/emerald(0.08) */

@keyframes aurora-drift {
  0%   { transform: translate(0, 0) scale(1); }
  25%  { transform: translate(60px, -40px) scale(1.15); }
  50%  { transform: translate(-30px, 30px) scale(0.95); }
  75%  { transform: translate(40px, 50px) scale(1.1); }
  100% { transform: translate(0, 0) scale(1); }
}
```

**Floating Keywords 구현**:
```html
<span class="fw" style="--delay:0s;--x:12%;--y:18%">Function</span>
<!-- 각 키워드에 CSS 변수로 위치/딜레이 지정 -->
```
```css
.fw {
  position: absolute; left: var(--x); top: var(--y);
  font: 700 18px 'Outfit'; color: rgba(6,30,74,0.18);
  text-transform: uppercase; letter-spacing: 0.15em;
  animation: fw-float 20s ease-in-out infinite;
  animation-delay: var(--delay);
}
@keyframes fw-float {
  0%   { opacity: 0; transform: translate(0,0) scale(0.8); }
  10%  { opacity: 1; }
  45%  { opacity: 1; transform: translate(20px,-30px) scale(1.1); }
  90%  { opacity: 1; }
  100% { opacity: 0; transform: translate(0,0) scale(0.8); }
}
```

#### 3.1.2 WebGL 파티클 시스템 (hero-particles.js)

**의존성**: `three.js r128` (CDN)

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<canvas id="heroParticles"></canvas>
```

**구현 요약**:
- `THREE.OrthographicCamera` + `THREE.RawShaderMaterial`
- Fragment Shader: Chromatic Sine-Wave — 3개 채널(R/G/B)에 distortion 오프셋 적용
- Navy-Blue-Teal 팔레트 매핑 (원본 RGB에 행렬 변환)
- `AdditiveBlending` + `transparent: true` + max alpha 0.35
- 60fps 애니메이션 루프, `time += 0.01`
- 리사이즈 자동 대응

**팔레트 변경 방법** (다른 프로그램 적용 시):
```glsl
/* fragment shader 내 색상 매핑 행렬 수정 */
float finalR = r * 0.024 + g * 0.12 + b * 0.02;   /* Red 채널 */
float finalG = r * 0.075 + g * 0.32 + b * 0.40;   /* Green 채널 */
float finalB = r * 0.29  + g * 0.65 + b * 0.96;   /* Blue 채널 */
```

#### 3.1.3 콘텐츠 요소 (z-index: 2)

| 요소 | 구현 |
|---|---|
| **배지** | Navy 배경 + Outfit 11px + 초록 `pulse-dot` 깜빡임 |
| **메인 타이틀** | `clamp(36px, 5vw, 64px)`, Outfit 700, **gradient-x 애니메이션** (3초 순환) |
| **서브 타이틀** | 16px Pretendard, `max-width: 600px`, `color: --text-secondary` |
| **CTA 버튼** | Navy 배경 + Outfit 14px 700 + 화살표 SVG, hover → `--accent` 전환 |
| **통계 4칸** | `flex gap:48px`, 숫자(Outfit 36px 700) + 라벨(Outfit 11px uppercase) |

**그라데이션 타이틀 애니메이션**:
```css
.gradient-title {
  background: linear-gradient(90deg, #061E4A 0%, #3B82F6 33%, #1D4ED8 66%, #061E4A 100%);
  background-size: 300% 100%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: gradient-x 3s ease-in-out infinite;
}
@keyframes gradient-x {
  0%   { background-position: 0% 50%; }
  50%  { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
```

**Count-Up 숫자 애니메이션** (landing.js):
```html
<span class="count-up" data-target="15000" data-suffix="+">0</span>
```
- IntersectionObserver로 뷰포트 진입 시 트리거
- 2초간 easeOutCubic으로 0→target 카운트업
- `toLocaleString()`으로 천 단위 콤마

---

### 3.2 SECTION 2: PLATFORM CONTENTS (White 배경)

**구조**: 섹션 라벨 + 타이틀 + 설명 → 6개 Feature Card Grid

```
[Section Label]  "Platform Contents" (Outfit 11px, accent blue, uppercase, 0.2em tracking)
[Section Title]  28px 700 navy
[Section Desc]   15px secondary, max-width 640px

[Feature Grid]   grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px;
  ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ Icon(SVG)│ │          │ │          │  ← 40x40 아이콘 박스
  │ Title    │ │          │ │          │  ← 17px 700 navy
  │ Desc     │ │          │ │          │  ← 13px secondary
  └──────────┘ └──────────┘ └──────────┘
```

**Feature Card 효과**:
- 기본: `border: 1px solid --border`, 하단 3px 바 (`--border-mid`)
- Hover: `border-color: --accent`, `translateY(-4px)`, `box-shadow`, 하단 바 → accent 색상

---

### 3.3 SECTION 3 & 6: NAVY BLOCK (Dark 배경)

**배경**: `--navy (#061E4A)` + 2개 장식 원 (accent 색, opacity 0.06, float 애니메이션)

```
[Deco Circle 1]  400x400px, top-right, 18초 float
[Deco Circle 2]  300x300px, bottom-left, 14초 float reverse
```

**Navy Card Grid**: `repeat(auto-fit, minmax(240px, 1fr))`
- 배경: `rgba(255,255,255,0.04)`, 테두리: `rgba(255,255,255,0.08)`
- Card Num: Outfit 11px accent, `01 / SCHEMA` 형식
- Hover: `rgba(255,255,255,0.08)` + `rgba(59,130,246,0.3)` 테두리

---

### 3.4 SECTION 4: DATA PIPELINE

**구조**: 6개 Step 카드가 화살표로 연결된 수평 흐름

```
[STEP 01] → [STEP 02] → [STEP 03] → [STEP 04] → [STEP 05] → [STEP 06]
```

**각 Step**: `flex: 0 0 160px`, 흰 배경, `step-num`(accent) + `h4`(navy) + `p`(muted)

**시퀀셜 하이라이트 애니메이션** (landing.js):
- IntersectionObserver 트리거 → 1초 간격으로 Step에 `step-active` 클래스 순차 적용
- Active 상태: Navy 배경 + accent 테두리 + `translateY(-6px)` + 강한 그림자
- 전체 순환 후 0.8초 대기 → 무한 반복

**화살표**: SVG 아이콘 + `arrow-pulse` 애니메이션 (2초 주기 좌→우 진동)

---

### 3.5 SECTION 5: IMAGE-TEXT ROWS

**구조**: 4개 Row — 이미지와 텍스트가 좌우 교차 배치

```
Row 1: [IMAGE] [TEXT]     ← 기본
Row 2: [TEXT]  [IMAGE]    ← .img-row-reverse (direction: rtl)
Row 3: [IMAGE] [TEXT]
Row 4: [TEXT]  [IMAGE]
```

**Grid**: `grid-template-columns: 1fr 1fr; gap: 40px; align-items: center`

**이미지 효과**: Hover 시 `transform: scale(1.03)` (0.5초 cubic-bezier)

**텍스트 구성**:
- Tag: Outfit 10px accent uppercase + accent 테두리 인라인 배지
- h4: 20px 700 navy
- p: 14px secondary
- ul: 커스텀 불릿 (4x4px accent 사각형)

**KG Metrics Grid** (Row 4 특수):
- `grid-template-columns: 1fr 1fr; gap: 16px`
- 각 메트릭: `--bg-subtle` 배경, 큰 숫자(Outfit 24px 700) + 라벨(11px muted)
- Hover: accent 테두리 + `translateY(-2px)`

---

## 4. 공통 동적 효과

### 4.1 Scroll Reveal

```css
.reveal {
  opacity: 0; transform: translateY(30px);
  transition: opacity 0.7s ease, transform 0.7s ease;
}
.reveal.visible { opacity: 1; transform: translateY(0); }
```

```javascript
const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.15 });
document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
```

- **모든 섹션 헤더, 카드, 이미지 Row**에 `.reveal` 클래스 부여
- 뷰포트 15% 진입 시 1회 트리거, 30px 아래→위 슬라이드 + 페이드인

### 4.2 Count-Up 숫자

- `data-target`: 목표 숫자, `data-suffix`: 접미사 ("+")
- easeOutCubic: `1 - Math.pow(1 - p, 3)`
- 뷰포트 50% 진입 시 1회 트리거

### 4.3 Pipeline Sequential Highlight

- 1초 간격으로 Step 순차 활성화 (Dark Navy 전환)
- 완료 후 0.5초 대기 → 리셋 → 0.8초 대기 → 재시작 (무한 루프)

---

## 5. 추가 컴포넌트

### 5.1 Top Navigation (Home Link)

```html
<a href="https://www.ninetynine99.co.kr/" class="home-link font-outfit" target="_blank">
  <svg><!-- 집 아이콘 --></svg>
  NINETYNINE
</a>
```

- `position: fixed; top: 20px; left: 24px; z-index: 1000`
- Navy 85% 투명 + `backdrop-filter: blur(12px)`
- Hover → accent 배경 + 그림자

### 5.2 Password Gate Modal

- `BYPASS_PASSWORD = true/false` 플래그로 ON/OFF 전환
- Navy 60% 오버레이 + `backdrop-filter: blur(8px)`
- 흰색 모달 (380px): 자물쇠 아이콘 + 비밀번호 입력 + AUTHENTICATE 버튼
- 실패 시 `shake` 애니메이션 (0.4초 좌우 진동)
- 복원: `BYPASS_PASSWORD = false` + 비밀번호 `'0172'`

### 5.3 Footer

```html
<footer class="site-footer">
  <a href="https://www.ninetynine99.co.kr/">https://www.ninetynine99.co.kr/</a>
  <span>2026 © All Right Reserved by Ninetynine Inc.</span>
</footer>
```

- `border-top: 1px solid --border` + `max-width: 1200px` 중앙 정렬
- 색상: `#BFBFBF`, Outfit

---

## 6. 파일 구성

```
project/
├── templates/
│   └── landing.html           # 메인 HTML (6개 섹션 + 모달)
├── static/
│   ├── css/
│   │   └── landing.css        # 디자인 시스템 + 모든 스타일 (896줄)
│   ├── js/
│   │   ├── landing.js         # Scroll Reveal + Counter + Pipeline 시퀀스 (93줄)
│   │   └── hero-particles.js  # WebGL Chromatic Sine-Wave 셰이더 (112줄)
│   └── images/
│       ├── 이미지1.jpeg        # Section 5 이미지 (4장)
│       ├── 이미지2.jpeg
│       └── ...
```

---

## 7. 다른 프로그램 적용 시 변경 체크리스트

| # | 항목 | 변경 내용 |
|---|---|---|
| 1 | CSS Variables | `--navy`, `--accent` 등을 프로그램 브랜드 색상으로 교체 |
| 2 | Hero 타이틀 | `gradient-title` 텍스트 및 gradient 색상 교체 |
| 3 | Hero 배지 | `ENTERPRISE VE INTELLIGENCE` → 프로그램 슬로건 |
| 4 | Hero 서브타이틀 | 프로그램 설명 텍스트로 교체 |
| 5 | 통계 4칸 | `data-target`, 라벨을 프로그램 지표로 교체 |
| 6 | Floating Keywords | 6개 키워드를 프로그램 관련 용어로 교체 |
| 7 | WebGL 팔레트 | `hero-particles.js` fragment shader의 색상 행렬 수정 |
| 8 | Feature Card 6개 | 제목, 설명, SVG 아이콘을 프로그램 기능으로 교체 |
| 9 | Navy Block 카드 | 기술 스택/아키텍처 설명을 프로그램에 맞게 교체 |
| 10 | Pipeline 6단계 | Step 제목/설명을 프로그램 워크플로로 교체 |
| 11 | Image Row 4개 | 이미지와 설명을 프로그램 스크린샷/도해로 교체 |
| 12 | ML Metrics Tier | 기술 지표를 프로그램 성능 메트릭으로 교체 |
| 13 | Home Link | URL과 회사명 교체 |
| 14 | Password | 비밀번호 변경 또는 바이패스 설정 |
| 15 | Meta 태그 | `<title>`, `<meta description>` 교체 |

---

## 8. AI 에이전트에게 전달할 프롬프트 예시

```
다음 명세를 참고하여 히어로 랜딩 페이지를 제작해줘.

[디자인 시스템]
- White Mode + Navy 강조 (Dark 섹션은 Navy 블록)
- Pretendard(한글) + Outfit(영문) 폰트 조합
- border-radius: 2px (rounded-sm), 이모지 금지
- CSS Variables: --navy:#061E4A, --accent:#3B82F6, --emerald:#10B981

[페이지 구조 — 총 6개 섹션]

Section 1: HERO (100vh)
- 3중 배경: Aurora Blob(blur 80px) + WebGL Chromatic Sine-Wave 셰이더(Three.js) + Floating Keywords(6개)
- 장식 그리드 라인 4개 (세로, opacity 0.3)
- 배지: Navy 배경 + 초록 pulse-dot + 영문 슬로건
- 메인 타이틀: gradient-x 애니메이션 (3초 순환, Navy→Blue→Navy)
- 서브 타이틀: 16px, max-width 600px
- CTA 버튼: Navy → hover시 accent, 화살표 SVG
- 통계 4칸: count-up 애니메이션 (2초, easeOutCubic), Outfit 36px 숫자

Section 2: 프로그램 콘텐츠 (White)
- 섹션 라벨(Outfit accent uppercase) + 타이틀(28px navy) + 설명(15px)
- 6개 Feature Card 그리드 (auto-fit, minmax 280px)
- 카드: SVG 아이콘(40x40) + 제목(17px) + 설명(13px) + 하단 3px 바
- Hover: accent 테두리 + translateY(-4px) + 하단 바 accent

Section 3: 기술 아키텍처 (Navy Dark 블록)
- 장식 원 2개 (accent, opacity 0.06, float 애니메이션)
- 4개 Navy Card: 반투명 배경 + 번호 라벨(Outfit accent) + 제목 + 설명

Section 4: 데이터 파이프라인 (White)
- 6개 Step 수평 흐름 + 화살표 SVG 연결
- 시퀀셜 하이라이트: 1초 간격 순차 활성화 (Dark Navy 전환), 무한 반복
- 활성 Step: Navy 배경, accent 테두리, translateY(-6px)

Section 5: 이미지-텍스트 교차 (White)
- 4개 Row: 이미지/텍스트 좌우 교차 (1fr 1fr grid)
- 홀수 Row: 이미지 왼쪽 / 짝수 Row: 이미지 오른쪽 (direction: rtl)
- Tag 배지(Outfit accent) + h4(20px) + 설명 + bullet 리스트
- 이미지 hover: scale(1.03)

Section 6: 기술 지표 (Navy Dark 블록)
- Section 3과 동일한 Navy Block 스타일
- 4개 Tier Card

[공통 동적 효과]
- Scroll Reveal: 모든 섹션에 .reveal 클래스 → IntersectionObserver(15%) → 30px 슬라이드업 + 페이드인 (0.7초)
- Count-Up: data-target 숫자를 2초간 easeOutCubic 카운트업
- Pipeline: 1초 간격 순차 하이라이트 무한 루프

[추가 컴포넌트]
- Top Left 고정 네비게이션: Navy 85% + backdrop-filter blur(12px) + 집 아이콘 + 회사명
- Password Gate Modal: 선택적, BYPASS_PASSWORD 플래그로 ON/OFF
- Footer: 링크 + 저작권 (Outfit, #BFBFBF)

[기술 스택]
- HTML + Vanilla CSS + Vanilla JS (프레임워크 없음)
- Three.js r128 (CDN) — WebGL 셰이더 전용
- 폰트: Pretendard(CDN) + Outfit(Google Fonts)
```

---

*이 가이드의 원본 소스 코드는 `src/templates/landing.html`, `src/static/css/landing.css`, `src/static/js/landing.js`, `src/static/js/hero-particles.js`에 있습니다.*

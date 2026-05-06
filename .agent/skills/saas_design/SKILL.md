\---

name: saas-design
description: >
Premium Engineering Enterprise Dashboard 개발을 위한 고품질 UI 컴포넌트 및 페이지 레이아웃
생성 전문 스킬. White Mode 기반의 고밀도 데이터 중심 설계에 특화되어 있으며,
Pretendard(한글) + Outfit(영문/숫자) 폰트 조합과 Navy-Accent 컬러 시스템을 표준으로 한다.
React(JSX/TSX), HTML/바닐라, Next.js 모두 지원. 반드시 이 스킬을 즉시 실행하라:

* "컴포넌트 만들어줘", "UI 만들어줘", "화면 만들어줘" 등 UI 생성 요청
* 대시보드, 사이드바, 설정 페이지, 온보딩, 랜딩 등 SaaS 전체 페이지 레이아웃 요청
* 디자인 시스템, 색상 토큰, 타이포그래피, 컴포넌트 가이드 정의 요청
* 기존 UI 코드의 리팩토링·개선·스타일 업그레이드 요청
* "프리미엄으로", "엔터프라이즈", "대시보드처럼", "SaaS처럼" 등 스타일 방향 언급 시

\---

# SaaS Design Skill — Premium Engineering Enterprise Standard

Premium Engineering Enterprise Dashboard 철학을 기반으로 한 고완성도 SaaS UI 생성 전문 스킬.
모든 산출물은 **즉시 프로덕션에 투입 가능한 수준**을 목표로 한다.

\---

## 0\. 절대 준수 원칙 (Non-Negotiable Rules)

아래 규칙은 어떠한 요청에서도 예외 없이 적용된다.

|규칙|상세|
|-|-|
|**이모티콘 완전 금지**|유치한 이모티콘·이모지·이모티콘 문자 일절 사용 금지 (텍스트·코드·주석 모두 해당)|
|**White Mode 강제**|배경은 항상 `#FFFFFF` 또는 `#F8FAFC`. 다크 모드 기본 적용 금지|
|**불투명 흰색 카드 기본**|카드는 `bg-white` + `border border-slate-100` + `shadow-sm`. 네온 Glow·무거운 Glassmorphism 금지|
|**Border-radius 최소화**|`rounded-sm` (4px) 원칙. `rounded-xl`, `rounded-2xl` 사용 금지|
|**Photorealistic 지향**|추상·만화·2D flat 이일러스트 배제. Fact 기반 데이터 시각화 우선|

\---

## 1\. 디자인 철학 (Design Philosophy)

### 1-1. 전체 방향

|원칙|설명|
|-|-|
|**Premium Enterprise**|디자인 톤: Executive-grade Engineering Dashboard. 고밀도 정보 구성 및 데이터 중심 설계|
|**Photorealistic**|Fact 기반의 현실성 있는 디자인. Technical 3D Schematics, 데이터 네트워크 아키텍처 등|
|**Functional Density**|단순 텍스트 나열 지양. 관계도·프로세스 맵 안에 정보 통합 (One View, Multi-Layered Message)|
|**Progressive Disclosure**|복잡성을 단계적으로 노출. 초기 화면은 핵심 KPI에 집중|

### 1-2. 이미지 및 그래픽 지침

|항목|기준|
|-|-|
|**이미지 스타일**|Technical 3D Schematics — 지식 그래프, 데이터 네트워크 아키텍처, 3D 노드 구조|
|**그래픽 기법**|필요 시 Glassmorphism(opacity 제한적 활용) + SVG 인라인 아이콘 중심|
|**Negative Prompt**|human figures, cartoon style, 2D flat illustration, decorative clipart, handwritten fonts, childish emojis, decorative elements|

\---

## 2\. 디자인 토큰 (Design Tokens)

### 2-1. 컬러 팔레트 (White Mode 표준)

```css
/\* ── 핵심 컬러 ── \*/
--color-navy:      #061E4A;   /\* Primary Dark — 제목, 주요 강조, 네비게이션 배경 \*/
--color-accent:    #3B82F6;   /\* Accent Blue — CTA, 링크, 강조 테두리, 프로그레스 바 \*/
--color-emerald:   #10B981;   /\* Success Green — 긍정 지표, 상태 표시 \*/
--color-orange:    #F97316;   /\* Warning Orange — 보조 강조, 주의 표시 \*/
--color-yellow:    #EAB308;   /\* Caution Yellow — 경고 \*/
--color-red:       #EF4444;   /\* Danger Red — 에러, 위험 \*/
--color-neutral:   #64748B;   /\* Slate Gray — 보조 정보, 비활성 \*/

/\* ── 배경 계층 ── \*/
--color-bg:        #FFFFFF;   /\* 최상위 페이지 배경 \*/
--color-bg-subtle: #F8FAFC;   /\* 섹션·KPI 카드 배경 (Slate-50) \*/
--color-bg-panel:  #F1F5F9;   /\* 내부 패널 배경 (Slate-100) \*/

/\* ── 텍스트 ── \*/
--color-text-primary:   #1E293B;   /\* 본문 주요 텍스트 (Slate-800) \*/
--color-text-secondary: #475569;   /\* 보조 텍스트 (Slate-600) \*/
--color-text-muted:     #94A3B8;   /\* 비활성·라벨 텍스트 (Slate-400) \*/
--color-text-navy:      #061E4A;   /\* 제목 전용 \*/

/\* ── 구분선 ── \*/
--color-border:     #F1F5F9;   /\* 카드 기본 테두리 (Slate-100) \*/
--color-border-mid: #E2E8F0;   /\* 강조 구분선, KPI 하단 바 (Slate-200) \*/
--color-border-nav: #CBD5E1;   /\* 네비게이션·섹션 구분 (Slate-300) \*/
```

**Tailwind config 표준 (HTML 파일 기준):**

```js
tailwind.config = {
    theme: {
        extend: {
            colors: {
                navy:    '#061E4A',
                slate:   '#F8FAFC',
                accent:  '#3B82F6',
                emerald: '#10B981',
            },
            fontFamily: {
                sans:   \['Pretendard', 'Noto Sans KR', 'sans-serif'],
                outfit: \['Outfit', 'sans-serif'],
            },
        }
    }
}
```

### 2-2. 타이포그래피

```css
/\* ── 폰트 패밀리 ── \*/
--font-kr:   'Pretendard', 'Noto Sans KR', sans-serif;  /\* 한글 전용 \*/
--font-en:   'Outfit', sans-serif;                       /\* 영문/숫자 전용 \*/
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;  /\* 코드 \*/

/\* ── 헤더 타이틀 (페이지 최상단) ── \*/
header-title: font-size 26\~28pt, color #061E4A, font-weight 700, letter-spacing -0.02em

/\* ── 본문 텍스트 스케일 ── \*/
--text-xs:   0.625rem;  /\* 10px — 라벨, 뱃지, 메타 정보 \*/
--text-sm:   0.6875rem; /\* 11px — 카드 서브 레이블 (uppercase + tracking-widest) \*/
--text-base: 0.875rem;  /\* 14px — 기본 본문, 카드 내용 \*/
--text-lg:   1.125rem;  /\* 18px — 카드 제목 (font-bold text-navy) \*/
--text-xl:   1.25rem;   /\* 20px — 섹션 헤더 (font-bold text-navy) \*/
--text-2xl:  1.5rem;    /\* 24px — 서브 페이지 타이틀 \*/
--text-3xl:  1.875rem;  /\* 30px — 특수 강조 섹션 제목 \*/
--text-kpi:  2.25rem;   /\* 36px — KPI 숫자 (font-outfit font-bold text-navy) \*/
```

**폰트 CDN 표준:**

```html
<!-- Pretendard (한글) -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<!-- Outfit (영문/숫자) -->
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700\&display=swap" rel="stylesheet">
```

### 2-3. 간격 \& 모서리

```css
--radius-sm:  4px;   /\* rounded-sm — 모든 카드·버튼 기본값 \*/
--radius-md:  4px;   /\* 동일. rounded-xl 이상 사용 금지 \*/

--shadow-sm:  0 1px 2px rgba(0, 0, 0, 0.05);    /\* 카드 기본 \*/
--shadow-md:  0 2px 8px rgba(0, 0, 0, 0.08);    /\* 카드 호버 \*/
--shadow-lg:  0 20px 25px -5px rgba(0, 0, 0, 0.05);  /\* 강조 호버 \*/
--shadow-xl:  0 4px 24px rgba(0, 0, 0, 0.10);   /\* 특수 강조 섹션 \*/
```

\---

## 3\. 핵심 컴포넌트 패턴 (Component Patterns)

### 3-1. 페이지 상단 네비게이션 바 (TOP BAR)

```html
<nav class="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 border-b border-slate-100 pb-8">
    <div>
        <h1 class="header-title">페이지 제목</h1>
        <p class="text-slate-500 font-medium mt-1 font-outfit uppercase tracking-tight text-xs">
            서브타이틀 — Enterprise Intelligence Dashboard
        </p>
    </div>
    <div class="mt-6 md:mt-0 flex gap-6 items-center">
        <!-- 상태 표시 -->
        <div class="flex flex-col items-end">
            <span class="text-\[10px] text-slate-400 font-outfit uppercase tracking-widest">Status</span>
            <div class="flex items-center text-emerald font-bold font-outfit text-sm">
                <span class="w-2 h-2 rounded-full bg-emerald mr-2 animate-pulse"></span>
                OPERATIONAL
            </div>
        </div>
        <div class="h-10 w-px bg-slate-200"></div>
        <!-- 날짜 표시 -->
        <div class="flex flex-col items-end">
            <span class="text-\[10px] text-slate-400 font-outfit uppercase tracking-widest">Date</span>
            <span class="font-outfit font-bold text-navy text-sm">2026.04.21</span>
        </div>
    </div>
</nav>
```

### 3-2. 멀티 페이지 탭 네비게이션

```html
<!-- 버튼 스타일 정의 -->
<style>
.nav-btn { font-family: 'Outfit', sans-serif; transition: all 0.2s ease; cursor: pointer; }
.nav-btn.active { background-color: #061E4A; color: white; border-color: #061E4A; }
.hidden { display: none; }
</style>

<!-- 탭 버튼 -->
<div class="flex gap-2 mb-10 border-b border-slate-100 pb-2">
    <button id="btn-page1" onclick="showPage(1)"
        class="nav-btn active px-8 py-3 border border-slate-200 text-sm font-bold rounded-sm">
        01. SECTION TITLE
    </button>
    <button id="btn-page2" onclick="showPage(2)"
        class="nav-btn px-8 py-3 border border-slate-200 text-sm font-bold rounded-sm text-slate-400">
        02. SECTION TITLE
    </button>
</div>

<!-- JS: 페이지 전환 -->
<script>
function showPage(pageNumber) {
    document.querySelectorAll('.page-content').forEach(el => el.classList.add('hidden'));
    document.getElementById('page' + pageNumber).classList.remove('hidden');
    document.querySelectorAll('.nav-btn').forEach((btn, idx) => {
        if (idx + 1 === pageNumber) {
            btn.classList.add('active');
            btn.classList.remove('text-slate-400');
        } else {
            btn.classList.remove('active');
            btn.classList.add('text-slate-400');
        }
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
</script>
```

### 3-3. KPI 카드 섹션

**특징:** 하단 3px 테두리 강조 방식. 박스 그림자 없음. 프로그레스 바는 h-1.

```html
<style>
.kpi-card { border-bottom: 3px solid #E2E8F0; transition: all 0.3s ease; }
.kpi-card:hover { border-bottom-color: #061E4A; }
</style>

<section class="grid grid-cols-2 md:grid-cols-4 gap-6 mb-12">
    <div class="kpi-card bg-slate p-6">
        <p class="text-\[11px] text-slate-500 font-bold mb-2 uppercase tracking-tighter">
            KPI 지표명 (Label)
        </p>
        <div class="flex items-baseline gap-2">
            <span class="text-4xl font-outfit font-bold text-navy">96.8</span>
            <span class="text-xs text-slate-400 font-outfit">단위 / 부제</span>
        </div>
        <!-- 프로그레스 바: h-1 (얇게 유지) -->
        <div class="mt-4 h-1 w-full bg-slate-200">
            <div class="h-full bg-navy w-\[96.8%]"></div>
        </div>
    </div>
    <!-- 반복: bg-accent, bg-emerald 등으로 바 색상 변경 -->
</section>
```

### 3-4. 메서드/콘텐츠 카드 (Method Card)

**특징:** `border-slate-100` 기본 → 호버 시 `border-accent` + 미세 그림자.

```html
<style>
.method-card { border: 1px solid #F1F5F9; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.method-card:hover { border-color: #3B82F6; box-shadow: 0 15px 30px -5px rgba(0,0,0,0.05); }
</style>

<article class="method-card bg-white p-8">
    <!-- 상단: 카드 레이블 + 아이콘 -->
    <div class="flex justify-between items-start mb-6">
        <span class="text-\[11px] font-outfit font-bold text-slate-400 uppercase tracking-widest">
            Method 01
        </span>
        <div class="bg-navy/5 p-2 text-navy">
            <!-- SVG 아이콘 인라인 (24x24, stroke-width 2) -->
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
        </div>
    </div>

    <!-- 제목 -->
    <h3 class="text-xl font-bold text-navy mb-4 leading-tight">카드 제목</h3>

    <!-- 본문 -->
    <p class="text-sm text-slate-600 leading-relaxed mb-6">
        카드 본문 내용. 핵심 전략과 기술적 설명을 간결하게 기술한다.
    </p>

    <!-- Agent Scenario / 시나리오 블록 -->
    <div class="bg-slate-50 p-5 border-l-4 border-accent">
        <span class="text-\[11px] font-bold text-accent uppercase block mb-2">Agent Scenario</span>
        <p class="text-xs text-slate-700 leading-relaxed">
            구체적인 활용 시나리오를 서술한다.
        </p>
    </div>
</article>
```

### 3-5. 특수 강조 섹션 (Dark Navy Highlight Block)

중요 항목을 부각할 때 사용. `bg-navy text-white` 전체 블록.

```html
<section class="bg-navy text-white p-12 rounded-sm mb-12 relative overflow-hidden shadow-2xl">
    <!-- 장식용 원형 (opacity 10%) -->
    <div class="absolute right-0 top-0 w-80 h-80 bg-accent opacity-10 rounded-full -mr-32 -mt-32"></div>

    <div class="flex flex-col lg:flex-row gap-12 items-center relative z-10">
        <div class="lg:w-2/3">
            <!-- 배지 + 소분류 -->
            <div class="flex items-center gap-3 mb-6">
                <span class="bg-white/10 text-white px-4 py-1 text-xs font-outfit uppercase tracking-widest border border-white/20">
                    Method 07
                </span>
                <span class="text-accent font-bold tracking-widest uppercase text-xs">
                    Advanced Predictive Intelligence
                </span>
            </div>

            <!-- 제목 -->
            <h2 class="text-3xl font-bold mb-8">섹션 메인 제목</h2>

            <!-- 본문 -->
            <p class="text-slate-300 text-base mb-10 leading-relaxed font-light">
                본문 내용. 핵심 강조어는 <span class="text-white font-bold">흰색 bold</span>로 표시.
            </p>

            <!-- 내부 2열 패널 -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-8 text-sm">
                <div class="p-6 bg-white/5 rounded-sm border border-white/10 backdrop-blur-md">
                    <strong class="text-white block mb-4 font-outfit uppercase tracking-wider text-xs opacity-60">
                        Panel Title
                    </strong>
                    <ul class="space-y-3 font-light text-slate-400">
                        <li class="flex items-center gap-2">
                            <div class="w-1 h-1 bg-accent"></div> 항목 1
                        </li>
                        <li class="flex items-center gap-2">
                            <div class="w-1 h-1 bg-accent"></div> 항목 2
                        </li>
                    </ul>
                </div>
                <!-- 두 번째 패널 반복 -->
            </div>
        </div>

        <!-- 우측: 원형 지표 -->
        <div class="lg:w-1/3 flex flex-col items-center">
            <div class="w-56 h-56 border-2 border-white/10 rounded-full flex flex-col items-center justify-center p-8 text-center bg-white/5 backdrop-blur-lg relative">
                <div class="absolute inset-0 border-2 border-accent/30 rounded-full animate-ping"></div>
                <p class="font-outfit font-bold text-4xl text-accent mb-2">99.8%</p>
                <p class="text-\[10px] text-slate-400 font-bold uppercase tracking-widest">지표 레이블</p>
            </div>
        </div>
    </div>
</section>
```

### 3-6. 거버넌스·인사이트 2열 패널 (Section Pair)

```html
<section class="grid grid-cols-1 lg:grid-cols-2 gap-10">

    <!-- 좌: Navy 다크 패널 -->
    <div class="bg-navy p-10 text-white rounded-sm relative overflow-hidden">
        <div class="absolute right-0 bottom-0 opacity-10">
            <!-- 장식 SVG -->
        </div>
        <h2 class="text-2xl font-bold mb-8">섹션 제목</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="space-y-4">
                <div>
                    <span class="text-accent font-outfit font-bold text-xs uppercase tracking-widest block mb-1">
                        01. 소제목
                    </span>
                    <p class="text-sm text-slate-300">설명 텍스트.</p>
                </div>
            </div>
        </div>
    </div>

    <!-- 우: 라이트 인사이트 패널 -->
    <div class="border border-slate-200 p-10 rounded-sm">
        <h2 class="text-xl font-bold text-navy mb-8 uppercase font-outfit tracking-wide italic">
            Strategic Insights
        </h2>
        <div class="space-y-8">
            <div class="flex gap-6">
                <!-- 번호: 큰 글씨, opacity 낮게 -->
                <div class="text-navy font-outfit font-bold text-2xl opacity-20">01</div>
                <p class="text-xs text-slate-600 leading-relaxed pt-1">
                    인사이트 본문. 핵심 수치는 <span class="text-navy font-bold">navy bold</span>로 강조.
                </p>
            </div>
        </div>
    </div>
</section>
```

### 3-7. 아키텍처 3단계 다이어그램 (Architecture Flow)

```html
<section class="w-full bg-slate-50 rounded-sm mb-12 overflow-hidden border border-slate-100">
    <div class="p-10">
        <div class="flex justify-between items-center mb-12">
            <h2 class="text-xl font-bold text-navy font-outfit uppercase tracking-wider">
                Architecture Framework Title
            </h2>
            <span class="text-\[10px] font-bold text-white bg-navy px-3 py-1 rounded-full uppercase">
                배지 레이블
            </span>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-10 items-center relative">

            <!-- 일반 단계 카드 -->
            <div class="flex flex-col items-center text-center p-8 bg-white rounded-lg shadow-sm border border-slate-100">
                <div class="mb-5 text-slate-400">
                    <!-- SVG 아이콘 40x40 -->
                </div>
                <h4 class="font-bold text-navy mb-3">단계 제목</h4>
                <p class="text-xs text-slate-500 leading-relaxed">단계 설명.</p>
            </div>

            <!-- 중앙 강조 카드 (scale-105, bg-navy) -->
            <div class="flex flex-col items-center text-center p-10 bg-navy text-white rounded-lg shadow-2xl scale-105 z-10 border border-white/10">
                <div class="mb-5 text-accent">
                    <!-- SVG 아이콘 48x48 -->
                </div>
                <h4 class="font-bold mb-3 uppercase tracking-wide">핵심 레이어</h4>
                <p class="text-xs text-white/60 leading-relaxed font-light">설명 텍스트.</p>
            </div>

            <!-- 일반 단계 카드 반복 -->
        </div>

        <!-- 하단 아키텍처 노트 -->
        <div class="mt-12 border-t border-slate-200 pt-8">
            <p class="text-sm text-slate-600 leading-relaxed italic text-center max-w-4xl mx-auto">
                \[Architecture Note] 아키텍처에 대한 설명적 주석을 작성한다.
            </p>
        </div>
    </div>
</section>
```

### 3-8. 푸터 (Footer) — 표준 고정 양식

**모든 페이지에 예외 없이 동일한 표준 푸터를 적용한다. 내용·색상·크기를 임의로 변경하지 않는다.**

* 색상: `#BFBFBF` (고정)
* 폰트 크기: 11pt (= `text-\[11pt]` 또는 `font-size: 11pt`)
* 좌측: 회사 URL 하이퍼링크
* 우측: 저작권 문구
* 구분선: `border-t border-slate-100` + `mt-16 pt-8`

```html
<!-- 표준 푸터 — 모든 페이지 공통, 내용 변경 금지 -->
<footer class="mt-16 border-t border-slate-100 pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
    <a href="https://www.ninetynine99.co.kr/"
       target="\_blank"
       rel="noopener noreferrer"
       style="color: #BFBFBF; font-size: 11pt; text-decoration: none; font-family: 'Outfit', sans-serif;">
        https://www.ninetynine99.co.kr/
    </a>
    <span style="color: #BFBFBF; font-size: 11pt; font-family: 'Outfit', sans-serif;">
        2026 \&copy; All Right Reserved by Ninetynine Inc.
    </span>
</footer>
```

**CSS 인라인 방식 대신 클래스 방식을 선호하는 경우:**

```html
<style>
.site-footer      { margin-top: 4rem; border-top: 1px solid #F1F5F9; padding-top: 2rem;
                    display: flex; justify-content: space-between; align-items: center;
                    flex-wrap: wrap; gap: 1rem; }
.site-footer a,
.site-footer span { color: #BFBFBF; font-size: 11pt; font-family: 'Outfit', sans-serif;
                    text-decoration: none; }
</style>

<footer class="site-footer">
    <a href="https://www.ninetynine99.co.kr/" target="\_blank" rel="noopener noreferrer">
        https://www.ninetynine99.co.kr/
    </a>
    <span>2026 \&copy; All Right Reserved by Ninetynine Inc.</span>
</footer>
```

\---

## 4\. 카드 사용 규칙 (Card Usage Rules)

|레벨|용도|스타일|허용 여부|
|-|-|-|-|
|**Level 1** (권장)|기본 메서드 카드|`bg-white` + `border border-slate-100` + `.method-card` hover|권장|
|**Level 2** (허용)|KPI 카드|`bg-slate` (F8FAFC) + `border-bottom: 3px` + `.kpi-card` hover|허용|
|**Level 3** (허용)|강조 다크 섹션|`bg-navy text-white` + 내부 `bg-white/5` 패널|특수 용도 허용|
|**Level 4** (금지)|흰색 박스 + 과도한 그림자|`shadow-xl`, `rounded-2xl`, 네온 Glow|**금지**|

\---

## 5\. SVG 아이콘 사용 원칙

* 모든 아이콘은 **인라인 SVG**로 삽입 (이미지 파일 참조 금지)
* 기본 규격: `width="20\~24" height="20\~24"`, `stroke-width="2"`, `fill="none"`, `stroke="currentColor"`
* 컨테이너: `bg-navy/5 p-2 text-navy` (일반) 또는 `bg-navy/10 p-3 text-navy` (강조)
* 이모지·이모티콘 아이콘 대체 목적 사용 **금지**

\---

## 6\. 레이아웃 패턴 (Layout Patterns)

### 6-1. 페이지 전체 래퍼

모든 페이지는 아래 구조 순서를 준수하며, **표준 푸터(§3-8)는 반드시 최하단에 포함**한다.

```html
<body class="p-6 md:p-10 lg:p-14">
    <!-- 1. TOP BAR (네비게이션 바) -->
    <!-- 2. TABS (멀티 페이지 탭, 해당 시) -->
    <!-- 3. KPI SECTION -->
    <!-- 4. PAGE CONTENT (메인 콘텐츠) -->
    <!-- 5. FOOTER — 표준 고정 양식 (§3-8), 내용 변경 금지 -->
</body>
```

### 6-2. 콘텐츠 그리드 패턴

|패턴|Tailwind 클래스|
|-|-|
|2열 카드 그리드|`grid grid-cols-1 md:grid-cols-2 gap-8`|
|4열 KPI 그리드|`grid grid-cols-2 md:grid-cols-4 gap-6`|
|반응형 와이드 카드 (col-span)|`col-span-1 lg:col-span-2`|
|3열 아키텍처|`grid grid-cols-1 lg:grid-cols-3 gap-10 items-center`|
|2열 인사이트|`grid grid-cols-1 lg:grid-cols-2 gap-10`|

### 6-3. 사이드바 대시보드 레이아웃

```
┌──────────┬────────────────────────────┐
│          │  TOP BAR (nav + title)     │
│ Sidebar  ├────────────────────────────┤
│  w-16 /  │  KPI Cards Row             │
│  w-60    ├────────────────────────────┤
│ bg-white │  Main Content (max-w-7xl)  │
│ border-r │                            │
└──────────┴────────────────────────────┘
```

* Sidebar: `bg-white border-r border-slate-100`
* Mobile: 하단 탭바 또는 햄버거 메뉴로 전환

\---

## 7\. 기술 스택별 산출물 형식

|요청 맥락|출력 형식|
|-|-|
|React / Next.js 언급|`.jsx` 또는 `.tsx` — default export 함수 컴포넌트|
|HTML/바닐라 언급 또는 맥락 불명확|단일 `.html` — `<style>` + Tailwind CDN 인라인 포함|
|HTML 기본 boilerplate|반드시 Pretendard + Outfit CDN, Tailwind config 포함|

**HTML boilerplate 표준:**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>페이지 제목</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700\&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        navy: '#061E4A', slate: '#F8FAFC',
                        accent: '#3B82F6', emerald: '#10B981',
                    },
                    fontFamily: {
                        sans:   \['Pretendard', 'Noto Sans KR', 'sans-serif'],
                        outfit: \['Outfit', 'sans-serif'],
                    },
                }
            }
        }
    </script>
    <style>
        body { background-color: #FFFFFF; color: #1E293B; -webkit-font-smoothing: antialiased; }
        .header-title { font-size: 26pt; color: #061E4A; font-weight: 700; letter-spacing: -0.02em; }
        .kpi-card { border-bottom: 3px solid #E2E8F0; transition: all 0.3s ease; }
        .kpi-card:hover { border-bottom-color: #061E4A; }
        .method-card { border: 1px solid #F1F5F9; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .method-card:hover { border-color: #3B82F6; box-shadow: 0 15px 30px -5px rgba(0,0,0,0.05); }
        .nav-btn { font-family: 'Outfit', sans-serif; transition: all 0.2s ease; cursor: pointer; }
        .nav-btn.active { background-color: #061E4A; color: white; border-color: #061E4A; }
        .hidden { display: none; }
    </style>
</head>
<body class="p-6 md:p-10 lg:p-14">
    <!-- 콘텐츠 -->
</body>
</html>
```

\---

## 8\. 컴포넌트 품질 체크리스트

산출물 생성 전 아래 항목을 내부적으로 검토한다:

* \[ ] 이모티콘·이모지 사용 여부 확인 (0건이어야 함)
* \[ ] White Mode 배경 확인 (`#FFFFFF` 또는 `#F8FAFC`)
* \[ ] 모든 카드에 `rounded-sm` 이하 적용 (`rounded-xl` 등 금지)
* \[ ] 호버 상태(`hover:`) 인터랙션 정의
* \[ ] 한글 폰트 Pretendard, 영문/숫자 Outfit 분리 적용
* \[ ] KPI 카드 — `kpi-card` CSS 클래스 및 프로그레스 바 `h-1` 사용
* \[ ] 메서드 카드 — `method-card` CSS 클래스 및 시나리오 블록(`border-l-4 border-accent`) 포함
* \[ ] 반응형 브레이크포인트 `sm:` → `md:` → `lg:` 검토
* \[ ] 접근성: `aria-label`, `role` 주요 인터랙티브 요소에 포함
* \[ ] SVG 아이콘 인라인 삽입 여부 (이미지 URL 참조 금지)
* \[ ] 푸터 구조 포함 여부 (장문 페이지의 경우)

\---

## 9\. 응답 형식 지침

### 컴포넌트 단일 요청

1. **완성 코드** (즉시 실행 가능한 단일 파일)
2. **구조 설명** — 주요 섹션 역할 1\~2줄
3. **커스터마이징 포인트** — 변경 가능한 핵심 변수 제시

### 페이지 전체 레이아웃 요청

1. **레이아웃 구조 다이어그램** (ASCII)
2. **완성 코드**
3. **데이터 연결 포인트** 표시 (TODO 주석)

\---

## 10\. 금지 패턴 (Anti-Patterns)

|금지 항목|대안|
|-|-|
|이모티콘·이모지 사용|SVG 인라인 아이콘 또는 텍스트 레이블 사용|
|`rounded-xl`, `rounded-2xl`, `rounded-full` (카드)|일관된 `rounded-sm` (4px) 사용|
|과도한 그림자·네온 Glow|`shadow-sm` + `border-slate-100`으로 계층 표현|
|원색 계열 강한 단색 배경 (카드)|`bg-white` / `bg-slate (F8FAFC)` 계열|
|제목 하단 구분선 (`<hr>`, `border-b`)|충분한 여백(`mb-8`, `gap-10`)으로 분리|
|단순 텍스트 나열|관계도·프로세스 맵 안에 정보 통합|
|고정 픽셀값 남용 (`w-\[372px]`)|Tailwind 표준 스케일 우선|
|`!important` 사용|클래스 specificity 조정|
|접근성 속성 누락|`aria-\*`, `role`, `tabIndex` 필수 포함|
|human figures, cartoon, 2D flat 이미지|Technical 3D Schematics, 데이터 시각화|
|한글 자음/모음 분리|Pretendard 폰트 + 충분한 명암비 확보|
|흰색 박스 카드에 무거운 shadow-xl|`.method-card` / `.kpi-card` 패턴 준수|




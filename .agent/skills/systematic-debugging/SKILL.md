---
name: systematic-debugging
# 버그, 테스트 실패, 예상치 못한 동작 발생 시, 수정 제안 전에 반드시 사용
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
---

# Systematic Debugging
# (체계적 디버깅)

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.
<!-- 랜덤 수정은 시간 낭비이며 새로운 버그를 만듭니다. 빠른 패치는 근본 원인을 가립니다. -->

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
<!-- 핵심 원칙: 수정 전 반드시 근본 원인을 찾을 것. 증상만 고치는 것은 실패입니다. -->

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
(근본 원인 조사 없이 수정 금지)
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue:
- Test failures / 테스트 실패
- Bugs in production / 운영 환경 버그
- Unexpected behavior / 예상치 못한 동작
- Performance problems / 성능 문제
- Build failures / 빌드 실패
- Integration issues / 연동 문제

**Use this ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work

## The Four Phases
<!-- 4단계: 각 단계를 완료해야 다음으로 진행 -->

You MUST complete each phase before proceeding to the next.

### Phase 1: Root Cause Investigation
<!-- 1단계: 근본 원인 조사 — 수정 시도 전에 반드시 수행 -->

**BEFORE attempting ANY fix:**

1. **Read Error Messages Carefully**
   - Don't skip past errors or warnings
   - Read stack traces completely
   - Note line numbers, file paths, error codes
   <!-- 에러 메시지를 꼼꼼히 읽을 것. 스택 트레이스 전체를 읽을 것. -->

2. **Reproduce Consistently**
   - Can you trigger it reliably?
   - What are the exact steps?
   - If not reproducible → gather more data, don't guess
   <!-- 재현 가능한가? 정확한 단계는? 재현 불가하면 추측 말고 데이터 수집 -->

3. **Check Recent Changes**
   - What changed that could cause this?
   - Git diff, recent commits
   - New dependencies, config changes
   <!-- 원인이 될 수 있는 최근 변경사항 확인 -->

4. **Gather Evidence in Multi-Component Systems**
   <!-- 다중 컴포넌트 시스템에서는 진단 로그를 먼저 추가 -->

   **WHEN system has multiple components (API → service → database):**

   **BEFORE proposing fixes, add diagnostic instrumentation:**
   ```
   For EACH component boundary:
     - Log what data enters component
     - Log what data exits component
     - Verify environment/config propagation
     - Check state at each layer

   Run once to gather evidence showing WHERE it breaks
   THEN analyze evidence to identify failing component
   THEN investigate that specific component
   ```

5. **Trace Data Flow**
   <!-- 데이터 흐름 추적 — 잘못된 값의 원천을 역추적 -->

   **WHEN error is deep in call stack:**
   - Where does bad value originate?
   - What called this with bad value?
   - Keep tracing up until you find the source
   - Fix at source, not at symptom

   See `root-cause-tracing.md` and `defense-in-depth.md` in this directory for detailed techniques.

### Phase 2: Pattern Analysis
<!-- 2단계: 패턴 분석 — 수정 전에 패턴을 찾을 것 -->

**Find the pattern before fixing:**

1. **Find Working Examples** — Locate similar working code in same codebase
2. **Compare Against References** — Read reference implementation COMPLETELY, don't skim
3. **Identify Differences** — List every difference, however small
4. **Understand Dependencies** — What other components, settings, config does this need?

### Phase 3: Hypothesis and Testing
<!-- 3단계: 가설 및 테스트 — 과학적 방법 -->

**Scientific method:**

1. **Form Single Hypothesis**
   - State clearly: "I think X is the root cause because Y"
   - Be specific, not vague

2. **Test Minimally**
   - Make the SMALLEST possible change to test hypothesis
   - One variable at a time via `run_command`
   - Don't fix multiple things at once

3. **Verify Before Continuing**
   - Did it work? Yes → Phase 4
   - Didn't work? Form NEW hypothesis
   - DON'T add more fixes on top

### Phase 4: Implementation
<!-- 4단계: 구현 — 근본 원인을 수정, 증상이 아님 -->

**Fix the root cause, not the symptom:**

1. **Create Failing Test Case** (if applicable)
   - Simplest possible reproduction
   - Load `test-driven-development` skill if writing tests

2. **Implement Single Fix**
   - Address the root cause identified
   - ONE change at a time
   - No "while I'm here" improvements

3. **Verify Fix** via `run_command`
   - Test passes now?
   - No other tests broken?
   - Issue actually resolved?

4. **If Fix Doesn't Work**
   - STOP
   - Count: How many fixes have you tried?
   - If < 3: Return to Phase 1, re-analyze with new information
   - **If ≥ 3: STOP and question the architecture (step 5 below)**

5. **If 3+ Fixes Failed: Question Architecture**
   <!-- 3번 이상 수정 실패 시: 아키텍처 자체에 문제가 있는지 의심 -->

   **Pattern indicating architectural problem:**
   - Each fix reveals new shared state/coupling/problem in different place
   - Fixes require "massive refactoring" to implement
   - Each fix creates new symptoms elsewhere

   **STOP and question fundamentals. Discuss with user before attempting more fixes.**

## Red Flags — STOP and Follow Process
<!-- 🚨 아래 생각이 들면 멈추고 프로세스를 따를 것 -->

If you catch yourself thinking:

| Thought | Reality |
|---------|---------|
| "Quick fix for now, investigate later" | Return to Phase 1 |
| "Just try changing X and see if it works" | Return to Phase 1 |
| "Add multiple changes, run tests" | One change at a time |
| "Skip the test, I'll manually verify" | Run the verification |
| "It's probably X, let me fix that" | Prove it first |
| "I don't fully understand but this might work" | Understand first |
| "One more fix attempt" (when 2+ tried) | Question architecture |
| Each fix reveals new problem in different place | Architectural issue |

**ALL of these mean: STOP. Return to Phase 1.**

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare | Identify differences |
| **3. Hypothesis** | Form theory, test minimally | Confirmed or new hypothesis |
| **4. Implementation** | Create test, fix, verify | Bug resolved, tests pass |

## Supporting Techniques
<!-- 보조 기법: 같은 디렉토리의 참조 문서 -->

These techniques are available in this directory:
- **`root-cause-tracing.md`** — Trace bugs backward through call stack to find original trigger
  <!-- 콜 스택을 역추적하여 원래 트리거 찾기 -->
- **`defense-in-depth.md`** — Add validation at multiple layers after finding root cause
  <!-- 근본 원인 발견 후 다중 레이어에 검증 추가 -->

**Related skills (load via `view_file` when needed):**
- **test-driven-development** — For creating failing test case (Phase 4)
- **verification-before-completion** — Verify fix worked before claiming success

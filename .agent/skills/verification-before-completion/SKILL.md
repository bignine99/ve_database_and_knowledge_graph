---
name: verification-before-completion
# 작업 완료/수정 완료/테스트 통과를 주장하기 전에 반드시 사용.
# 코드 리뷰 핵심 원칙(requesting/receiving-code-review)이 통합되어 있음.
description: Use when about to claim work is complete, fixed, or passing - requires running verification commands and confirming output before making any success claims
---

# Verification Before Completion
# (완료 전 검증)

## Overview

Claiming work is complete without verification is dishonesty, not efficiency.
<!-- 검증 없이 작업 완료를 주장하는 것은 효율이 아니라 거짓입니다. -->

**Core principle:** Evidence before claims, always.
<!-- 핵심 원칙: 주장 전에 항상 증거를 확보합니다. -->

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
(새로운 검증 증거 없이 완료 주장 금지)
```

If you haven't run the verification command in this message, you cannot claim it passes.

## The Gate Function
<!-- 게이트 함수: 모든 상태 주장 전에 실행 -->

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
   (이 주장을 증명하는 명령어는 무엇인가?)
2. RUN: Execute the FULL command via run_command (fresh, complete)
   (run_command로 전체 명령어 실행)
3. READ: Full output, check exit code, count failures
   (전체 출력 확인, 종료 코드 확인, 실패 수 계산)
4. VERIFY: Does output confirm the claim?
   (출력이 주장을 확인하는가?)
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. ONLY THEN: Make the claim
   (그때서야 주장 가능)

Skip any step = lying, not verifying
```

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Requirements met | Line-by-line checklist | Tests passing |

## Red Flags — STOP
<!-- 🚨 아래 상황이면 멈출 것 -->

- Using "should", "probably", "seems to"
  <!-- "~일 것이다", "아마", "~인 것 같다" 사용 금지 -->
- Expressing satisfaction before verification ("Great!", "Perfect!", "Done!", etc.)
  <!-- 검증 전 만족 표현 금지 -->
- About to commit/push without verification
  <!-- 검증 전 커밋/푸시 금지 -->
- Relying on partial verification
  <!-- 부분적 검증에 의존 금지 -->
- **ANY wording implying success without having run verification**
  <!-- 검증 실행 없이 성공을 암시하는 모든 표현 금지 -->

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence ≠ evidence |
| "Just this once" | No exceptions |
| "Linter passed" | Linter ≠ compiler |
| "Partial check is enough" | Partial proves nothing |

## Key Patterns

**Tests:**
```
✅ [Run test command] [See: 34/34 pass] "All tests pass"
❌ "Should pass now" / "Looks correct"
```

**Build:**
```
✅ [Run build] [See: exit 0] "Build passes"
❌ "Linter passed" (linter doesn't check compilation)
```

**Requirements:**
```
✅ Re-read plan → Create checklist → Verify each → Report gaps or completion
❌ "Tests pass, phase complete"
```

---

## Self Code Review (Integrated)
<!-- 자체 코드 리뷰: requesting/receiving-code-review 핵심 원칙 통합 -->

Before claiming a task or feature is complete, perform a self-review:

### Pre-Completion Review Checklist
<!-- 완료 전 리뷰 체크리스트 -->

1. **Spec compliance** — Does the implementation match the original requirements?
   <!-- 구현이 원래 요구사항과 일치하는가? -->
   - Nothing missing (under-built)
   - Nothing extra (over-built / YAGNI violation)

2. **Code quality check:**
   - No magic numbers or hardcoded values
   - Error handling in place
   - Naming is clear and consistent
   - No dead code or commented-out blocks

3. **Test coverage:**
   - All new functions/methods tested
   - Edge cases covered
   - Tests actually verify behavior (not just run)

4. **Integration check:**
   - Changes don't break existing functionality
   - Dependencies are properly declared
   - Config/environment changes documented

### Responding to User Feedback
<!-- 사용자 피드백 대응 원칙 -->

When receiving feedback on your work:

- **Verify first, implement second** — Check feedback against codebase reality before acting
  <!-- 먼저 검증하고, 그다음 구현 -->
- **Technical correctness over comfort** — Push back with reasoning if feedback seems incorrect
  <!-- 피드백이 잘못된 것 같으면 근거를 들어 반론 -->
- **Clarify before partial implementation** — If some items are unclear, ask about ALL unclear items before starting
  <!-- 불명확한 항목이 있으면 구현 전에 전부 확인 -->
- **YAGNI check** — If suggested feature isn't used anywhere, question whether it's needed
  <!-- 제안된 기능이 어디에서도 사용되지 않으면 필요성에 의문 -->
- **One fix at a time, test each** — Don't batch multiple fixes without individual verification
  <!-- 한 번에 하나씩 수정하고 각각 검증 -->

## When To Apply

**ALWAYS before:**
- ANY variation of success/completion claims
  <!-- 성공/완료 주장의 모든 변형 -->
- ANY expression of satisfaction
  <!-- 모든 만족 표현 -->
- Committing, PR creation, task completion
  <!-- 커밋, PR 생성, 작업 완료 -->
- Moving to next task
  <!-- 다음 작업으로 이동 -->

## The Bottom Line

**No shortcuts for verification.**
<!-- 검증에는 지름길이 없습니다. -->

Run the command. Read the output. THEN claim the result.

This is non-negotiable.

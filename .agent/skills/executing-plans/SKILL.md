---
name: executing-plans
# 작성된 구현 계획을 실행할 때 사용. 검토 체크포인트 포함 단일 세션 실행.
description: Use when you have a written implementation plan to execute with review checkpoints
---

# Executing Plans
# (계획 실행)

## Overview

Load plan, review critically, execute all tasks, report when complete.
<!-- 계획을 로드하고, 비판적으로 검토하고, 모든 작업을 실행하고, 완료 시 보고합니다. -->

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

## The Process

### Step 1: Load and Review Plan
<!-- 1단계: 계획 로드 및 검토 -->

1. Read plan file via `view_file`
2. Review critically — identify any questions or concerns about the plan
3. If concerns: Raise them with the user before starting
4. If no concerns: Create an artifact checklist and proceed

### Step 2: Execute Tasks
<!-- 2단계: 작업 실행 (한 번에 하나씩) -->

For each task:
1. Mark as in_progress in checklist
2. Follow each step exactly (plan has bite-sized steps)
3. Run verifications as specified via `run_command`
4. Mark as completed

**Batch execution with checkpoints:**
<!-- 배치 실행: 3개 작업마다 사용자에게 진행 상황 보고 -->

- Execute tasks in batches of 3
- After each batch, report progress to user
- Get confirmation before continuing
- If any task fails, stop and discuss

### Step 3: Complete Development
<!-- 3단계: 개발 완료 -->

After all tasks complete and verified:
- Run full test suite / verification
- Present summary of all changes made
- Load `verification-before-completion` skill before claiming done
  <!-- 완료 주장 전 반드시 verification-before-completion 스킬 로드 -->

## When to Stop and Ask for Help
<!-- 멈추고 도움을 요청해야 할 때 -->

**STOP executing immediately when:**
- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- Verification fails repeatedly (3+ times)

**Ask for clarification rather than guessing.**
<!-- 추측하지 말고 확인하세요. -->

## When to Revisit Earlier Steps

**Return to Review (Step 1) when:**
- User updates the plan based on your feedback
- Fundamental approach needs rethinking

**Don't force through blockers** — stop and ask.

## Remember
- Review plan critically first
  <!-- 계획을 먼저 비판적으로 검토 -->
- Follow plan steps exactly
  <!-- 계획 단계를 정확히 따를 것 -->
- Don't skip verifications
  <!-- 검증을 건너뛰지 말 것 -->
- Load referenced skills when plan says to (via `view_file`)
  <!-- 계획에서 참조하는 스킬은 view_file로 로드 -->
- Stop when blocked, don't guess
  <!-- 막히면 멈추고, 추측하지 말 것 -->
- Never start implementation on main/master branch without explicit user consent
  <!-- 사용자 동의 없이 main 브랜치에서 구현 시작 금지 -->

## Integration

**Related skills (load via `view_file` when needed):**
- **writing-plans** — Creates the plan this skill executes
- **test-driven-development** — Follow TDD cycle for each task
- **verification-before-completion** — Verify before claiming done

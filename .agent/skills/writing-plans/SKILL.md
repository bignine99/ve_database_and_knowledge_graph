---
name: writing-plans
# 스펙 또는 요구사항이 있는 다단계 작업에서, 코드 작성 전에 사용
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans
# (구현 계획 작성)

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for the codebase. Document everything they need to know: which files to touch, code, testing, docs, how to verify. Give the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.
<!-- 코드베이스에 대한 컨텍스트가 없는 엔지니어를 가정하고 포괄적인 구현 계획을 작성합니다. -->

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Save plans to:** `docs/plans/YYYY-MM-DD-<feature-name>.md`
- (User preferences for plan location override this default)
<!-- 사용자가 지정한 위치가 우선 -->

## Scope Check
<!-- 범위 점검 -->

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure
<!-- 파일 구조 매핑 -->

Before defining tasks, map out which files will be created or modified and what each one is responsible for.

- Design units with clear boundaries and well-defined interfaces
- Prefer smaller, focused files over large ones that do too much
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Bite-Sized Task Granularity
<!-- 한입 크기 작업 단위 (2-5분) -->

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header
<!-- 계획 문서 헤더 (필수) -->

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For AI Agent:** Follow this plan task-by-task. Use the executing-plans skill.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## No Placeholders
<!-- 🚨 플레이스홀더 금지 -->

Every step must contain the actual content an engineer needs. These are **plan failures** — never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code — tasks may be read out of order)
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task

## Remember
- Exact file paths always
- Complete code in every step — if a step changes code, show the code
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Self-Review
<!-- 자체 검토: 계획 작성 완료 후 스펙 대비 점검 -->

After writing the complete plan, check the plan against the spec:

**1. Spec coverage:** Skim each section/requirement in the spec. Can you point to a task that implements it? List any gaps.

**2. Placeholder scan:** Search your plan for red flags — any of the patterns from the "No Placeholders" section above. Fix them.

**3. Type consistency:** Do the types, method signatures, and property names you used in later tasks match what you defined in earlier tasks?

If you find issues, fix them inline. If you find a spec requirement with no task, add the task.

## Execution Handoff
<!-- 실행 핸드오프: 계획 저장 후 사용자에게 실행 방식 안내 -->

After saving the plan:

**"Plan complete and saved to `docs/plans/<filename>.md`. Ready to execute.**

**I will load the `executing-plans` skill and begin implementation task-by-task with verification checkpoints."**

- Load `.agent/skills/executing-plans/SKILL.md` via `view_file`
- Execute tasks in the current session with batch execution and checkpoints

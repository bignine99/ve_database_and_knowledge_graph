# Defense-in-Depth Validation
# (다중 레이어 검증)

## Overview

When you fix a bug caused by invalid data, adding validation at one place feels sufficient. But that single check can be bypassed by different code paths, refactoring, or mocks.
<!-- 잘못된 데이터로 인한 버그를 수정할 때, 한 곳에만 검증을 추가하면 충분한 것 같지만, 다른 코드 경로나 리팩토링으로 우회될 수 있습니다. -->

**Core principle:** Validate at EVERY layer data passes through. Make the bug structurally impossible.
<!-- 핵심: 데이터가 통과하는 모든 레이어에서 검증합니다. 버그를 구조적으로 불가능하게 만드세요. -->

## Why Multiple Layers

Single validation: "We fixed the bug"
Multiple layers: "We made the bug impossible"

## The Four Layers

### Layer 1: Entry Point Validation
<!-- 1층: 진입점 검증 — API 경계에서 명백히 잘못된 입력 거부 -->
**Purpose:** Reject obviously invalid input at API boundary

```typescript
function createProject(name: string, workingDirectory: string) {
  if (!workingDirectory || workingDirectory.trim() === '') {
    throw new Error('workingDirectory cannot be empty');
  }
  if (!existsSync(workingDirectory)) {
    throw new Error(`workingDirectory does not exist: ${workingDirectory}`);
  }
  // ... proceed
}
```

### Layer 2: Business Logic Validation
<!-- 2층: 비즈니스 로직 검증 — 해당 작업에 맞는 데이터인지 확인 -->
**Purpose:** Ensure data makes sense for this operation

```typescript
function initializeWorkspace(projectDir: string, sessionId: string) {
  if (!projectDir) {
    throw new Error('projectDir required for workspace initialization');
  }
  // ... proceed
}
```

### Layer 3: Environment Guards
<!-- 3층: 환경 가드 — 특정 컨텍스트에서 위험한 작업 방지 -->
**Purpose:** Prevent dangerous operations in specific contexts

```typescript
async function gitInit(directory: string) {
  if (process.env.NODE_ENV === 'test') {
    const normalized = normalize(resolve(directory));
    const tmpDir = normalize(resolve(tmpdir()));
    if (!normalized.startsWith(tmpDir)) {
      throw new Error(
        `Refusing git init outside temp dir during tests: ${directory}`
      );
    }
  }
  // ... proceed
}
```

### Layer 4: Debug Instrumentation
<!-- 4층: 디버그 계측 — 포렌식을 위한 컨텍스트 기록 -->
**Purpose:** Capture context for forensics

```typescript
async function gitInit(directory: string) {
  const stack = new Error().stack;
  logger.debug('About to git init', {
    directory,
    cwd: process.cwd(),
    stack,
  });
  // ... proceed
}
```

## Applying the Pattern

When you find a bug:

1. **Trace the data flow** — Where does bad value originate? Where used?
2. **Map all checkpoints** — List every point data passes through
3. **Add validation at each layer** — Entry, business, environment, debug
4. **Test each layer** — Try to bypass layer 1, verify layer 2 catches it

## Key Insight

All four layers are often necessary. During testing, each layer catches bugs the others miss:
- Different code paths bypass entry validation
- Mocks bypass business logic checks
- Edge cases on different platforms need environment guards
- Debug logging identifies structural misuse

**Don't stop at one validation point.** Add checks at every layer.
<!-- 하나의 검증 지점에서 멈추지 마세요. 모든 레이어에 검증을 추가하세요. -->

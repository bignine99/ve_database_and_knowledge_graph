# Ninetynine Agent Skills Library
# (Adapted from Superpowers v5.0.7 for Antigravity Environment)

> 이 스킬 라이브러리는 [Superpowers](https://github.com/obra/superpowers) (MIT License, by Jesse Vincent)의
> 핵심 방법론을 Antigravity(Gemini Code Assist) 환경에 맞게 변환한 것입니다.

## 도구 매핑 (Tool Mapping)

스킬 내부에서 참조하는 도구명은 아래와 같이 Antigravity 도구로 매핑됩니다:

| Superpowers 원본 | Antigravity 도구 | 비고 |
|---|---|---|
| `Read` | `view_file` | 파일 읽기 |
| `Write` | `write_to_file` | 파일 생성 |
| `Edit` | `replace_file_content` / `multi_replace_file_content` | 파일 수정 |
| `Bash` | `run_command` | 명령어 실행 |
| `Grep` | `grep_search` | 패턴 검색 |
| `Glob` / `ls` | `list_dir` | 디렉토리 탐색 |
| `TodoWrite` | Artifact 체크리스트 (`.md`) | 작업 추적 |
| `Skill` (invoke) | `view_file` → `.agent/skills/*/SKILL.md` | 스킬 로드 |
| `Task` (subagent) | ❌ 미지원 | 코드 서브에이전트 없음 |
| `WebSearch` | `search_web` | 웹 검색 |
| `WebFetch` | `read_url_content` | URL 읽기 |

## 스킬 목록 (Skill Catalog)

| # | 스킬 | 트리거 조건 | 경로 |
|:---:|---|---|---|
| 1 | **Brainstorming** | 새 기능/프로젝트 착수 시 | `brainstorming/SKILL.md` |
| 2 | **Writing Plans** | 설계 승인 후 구현 계획 작성 시 | `writing-plans/SKILL.md` |
| 3 | **Executing Plans** | 계획 실행 단계 진입 시 | `executing-plans/SKILL.md` |
| 4 | **Systematic Debugging** | 버그/테스트 실패/예상치 못한 동작 시 | `systematic-debugging/SKILL.md` |
| 5 | **Test-Driven Development** | 테스트 코드 작성이 필요한 구현 시 | `test-driven-development/SKILL.md` |
| 6 | **Verification Before Completion** | 작업 완료 보고 직전 | `verification-before-completion/SKILL.md` |
| 7 | **SaaS Design** | UI/컴포넌트/대시보드/레이아웃 생성 및 디자인 요청 시 | `saas_design/SKILL.md` |

## 사용 방법

1. `.rule.md` 섹션 7.1의 트리거 테이블에 따라, AI 에이전트가 작업 유형에 맞는 스킬을 자동으로 `view_file`로 로드합니다.
2. 사용자가 직접 "systematic-debugging 스킬 읽어봐" 등으로 수동 트리거할 수도 있습니다.
3. 스킬 내용을 읽은 후, 해당 절차를 순서대로 따릅니다.

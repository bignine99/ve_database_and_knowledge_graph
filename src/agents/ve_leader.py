"""
VE Leader — Multi-Agent 오케스트레이터 (Task 31)

워크플로:
  Step 1: 입력 파싱 + 분석 대상 선정
  Step 2: DB 검색 Agent → 유사 사례 Top-K (기존 Tier 1~4)
  Step 3: Idea Agent → 아이디어 도출 (Gemini)
  Step 4: Domain Agent(s) → 기술 검증 (병렬)
  Step 5: Report Agent → 보고서 초안
"""

import os
import sys
import time
import uuid
import json
import logging
from typing import Optional
from dataclasses import asdict

# 프로젝트 루트를 sys.path에 추가
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.agents.schemas import (
    ProjectBrief, DesignAnalysis, CostBreakdown,
    AgentRequest, AgentResponse, AgentStatus,
    AnalysisTarget, SimilarCase, VEIdea, DomainReview, VESession,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════
#  Task 32: DB Search Agent (기존 ML 래핑)
# ═══════════════════════════════════════════════════

class DBSearchAgent:
    """기존 시맨틱 검색 + ML 분류기를 AgentResponse로 래핑"""

    def run(self, request: AgentRequest, targets: list[AnalysisTarget]) -> AgentResponse:
        t0 = time.time()
        all_cases: dict[str, list[SimilarCase]] = {}
        all_refs: list[int] = []

        try:
            from src.semantic_search import hybrid_search
            from src.ml_classifier import classify_alternative
        except ImportError as e:
            return AgentResponse(
                agent_name="DBSearchAgent", step_number=2,
                status=AgentStatus.FAILED,
                result={"error": f"ML 모듈 로드 실패: {e}"},
                elapsed_seconds=time.time() - t0,
            )

        for target in targets:
            query = target.search_query or f"{target.element_name} {target.current_spec}"
            try:
                results = hybrid_search(query, top_k=5, use_gemini=False)
                cases = []
                for r in results.get("results", [])[:5]:
                    sc = SimilarCase(
                        alt_number=r.get("alt_number", 0),
                        title=r.get("title", ""),
                        similarity=r.get("hybrid_score", r.get("semantic_score", 0)),
                        how2_code=r.get("how2_code", ""),
                        how2_name=r.get("how2_name", ""),
                        space=r.get("space", ""),
                        value_type=r.get("value_type", ""),
                        savings_rate=r.get("savings_rate", 0),
                        perf_change=r.get("perf_change", 0),
                        cost_change=r.get("cost_change", 0),
                        value_change=r.get("value_change", 0),
                    )
                    cases.append(sc)
                    all_refs.append(sc.alt_number)
                all_cases[target.element_name] = cases
            except Exception as e:
                logger.warning(f"검색 실패 [{target.element_name}]: {e}")
                all_cases[target.element_name] = []

        # ML 분류 결과 첨부
        classifications = {}
        for target in targets:
            try:
                cls = classify_alternative(f"{target.element_name} {target.current_spec}")
                classifications[target.element_name] = cls
            except Exception:
                pass

        return AgentResponse(
            agent_name="DBSearchAgent", step_number=2,
            status=AgentStatus.SUCCESS,
            confidence=0.8,
            result={
                "similar_cases": {k: [asdict(c) for c in v] for k, v in all_cases.items()},
                "classifications": classifications,
                "total_found": sum(len(v) for v in all_cases.values()),
            },
            references=list(set(all_refs)),
            elapsed_seconds=time.time() - t0,
        )


# ═══════════════════════════════════════════════════
#  Task 33: Idea Agent (Gemini 기반 아이디어 도출)
# ═══════════════════════════════════════════════════

class IdeaAgent:
    """유사 사례 + 비용 데이터 기반 VE 아이디어 도출"""

    def run(self, request: AgentRequest, targets: list[AnalysisTarget],
            similar_cases: dict) -> AgentResponse:
        t0 = time.time()
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return AgentResponse(
                agent_name="IdeaAgent", step_number=3,
                status=AgentStatus.FAILED,
                result={"error": "GEMINI_API_KEY 없음"},
                elapsed_seconds=time.time() - t0,
            )

        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
        except Exception as e:
            return AgentResponse(
                agent_name="IdeaAgent", step_number=3,
                status=AgentStatus.FAILED,
                result={"error": str(e)},
                elapsed_seconds=time.time() - t0,
            )

        # 프롬프트 구성
        targets_text = "\n".join(
            f"- {t.element_name}: {t.current_spec} (비용비중 {t.cost_ratio:.1f}%)"
            for t in targets
        )
        cases_text = ""
        for name, cases in similar_cases.items():
            if cases:
                top3 = cases[:3] if isinstance(cases[0], dict) else [asdict(c) for c in cases[:3]]
                for c in top3:
                    cases_text += (
                        f"  - #{c.get('alt_number', '?')} {c.get('title', '')} "
                        f"(절감율 {c.get('savings_rate', 0):.1f}%, "
                        f"가치변화 {c.get('value_change', 0):+.1f}%)\n"
                    )

        brief = request.project_brief
        prompt = f"""당신은 건설 VE(Value Engineering) 아이디어 도출 전문가입니다.

[시스템 제약]
1. 아래 제공된 유사 사례 데이터를 근거로 아이디어를 제시하세요.
2. 근거 없는 비용 수치를 만들지 마세요. "약 X% 절감 예상"처럼 범위로 표현하세요.
3. 각 아이디어에 근거가 된 대안 번호를 명시하세요.

[프로젝트 정보]
- 프로젝트: {brief.project_name} ({brief.project_type})
- 규모: {brief.total_area:,.0f}㎡, 공사비: {brief.total_cost:,.0f}백만원
- VE 목표: {brief.ve_target_rate}% 절감
- 관심 분야: {', '.join(brief.focus_disciplines) or '전체'}
- 제약: {', '.join(brief.constraints) or '없음'}

[분석 대상]
{targets_text}

[유사 사례 (DB 727건 기반)]
{cases_text or '검색 결과 없음'}

[요구사항]
각 분석 대상별로 2~3개 VE 아이디어를 JSON 배열로 제시하세요.
각 아이디어는 다음 필드를 포함:
- idea_name: 아이디어 제안명
- category: "재료대체" | "공법변경" | "규격최적화" | "기능통합" | "삭제축소" | "기술도입"
- current: 현재 방식
- proposed: 제안 대안
- expected_saving: 예상 절감 효과 (범위)
- reference_cases: 근거 대안 번호 배열
- risks: 위험 요소 배열
- domain_review_needed: 검증 필요 도메인 배열

JSON 배열만 출력하세요. 설명 텍스트 없이."""

        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    temperature=0.7, top_p=0.9, max_output_tokens=2000,
                ),
            )
            raw = response.text.strip()
            # JSON 파싱
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            ideas_data = json.loads(raw)
            if not isinstance(ideas_data, list):
                ideas_data = [ideas_data]

            ideas = []
            refs = []
            for d in ideas_data:
                idea = VEIdea(
                    idea_name=d.get("idea_name", ""),
                    category=d.get("category", "기타"),
                    current=d.get("current", ""),
                    proposed=d.get("proposed", ""),
                    expected_saving=d.get("expected_saving", ""),
                    confidence=0.6 if d.get("reference_cases") else 0.3,
                    reference_cases=d.get("reference_cases", []),
                    risks=d.get("risks", []),
                    domain_review_needed=d.get("domain_review_needed", []),
                )
                ideas.append(idea)
                refs.extend(idea.reference_cases)

            return AgentResponse(
                agent_name="IdeaAgent", step_number=3,
                status=AgentStatus.SUCCESS,
                confidence=0.7,
                result={"ideas": [asdict(i) for i in ideas], "count": len(ideas)},
                references=list(set(refs)),
                elapsed_seconds=time.time() - t0,
            )
        except json.JSONDecodeError:
            return AgentResponse(
                agent_name="IdeaAgent", step_number=3,
                status=AgentStatus.PARTIAL,
                result={"raw_response": raw[:1000], "parse_error": "JSON 파싱 실패"},
                warnings=["Gemini 출력을 JSON으로 파싱하지 못했습니다."],
                elapsed_seconds=time.time() - t0,
            )
        except Exception as e:
            return AgentResponse(
                agent_name="IdeaAgent", step_number=3,
                status=AgentStatus.FAILED,
                result={"error": str(e)},
                elapsed_seconds=time.time() - t0,
            )


# ═══════════════════════════════════════════════════
#  Task 34: Domain Agent (SKILL 기반 기술 검증)
# ═══════════════════════════════════════════════════

# 도메인 → SKILL 파일 매핑
DISCIPLINE_SKILL_MAP = {
    "건축": "SKILL_Architect.md",
    "토목": "SKILL_Civil.md",
    "전기": "SKILL_Electronic.md",
    "기계설비": "SKILL_Mechanic.md",
    "배관": "SKILL_Plumbing.md",
    "조경": "SKILL_Landscape.md",
}


class DomainAgent:
    """SKILL 파일을 동적 로드하여 도메인별 기술 검증 수행"""

    def __init__(self, discipline: str):
        self.discipline = discipline
        self.skill_prompt = self._load_skill()

    def _load_skill(self) -> str:
        skill_file = DISCIPLINE_SKILL_MAP.get(self.discipline)
        if not skill_file:
            return f"당신은 {self.discipline} 분야 전문가입니다."
        skill_path = os.path.join(_ROOT, ".ve_SKILL", skill_file)
        if os.path.exists(skill_path):
            with open(skill_path, "r", encoding="utf-8") as f:
                # 전체 SKILL은 너무 길므로 핵심 역량 + 패턴만 추출 (상위 2000자)
                content = f.read()
                return content[:2000]
        return f"당신은 {self.discipline} 분야 전문가입니다."

    def review(self, idea: dict, brief: ProjectBrief) -> DomainReview:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return DomainReview(
                discipline=self.discipline, idea_name=idea.get("idea_name", ""),
                recommendation="보류", concerns=["GEMINI_API_KEY 없음"]
            )

        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
        except Exception as e:
            return DomainReview(
                discipline=self.discipline, idea_name=idea.get("idea_name", ""),
                recommendation="보류", concerns=[str(e)]
            )

        prompt = f"""{self.skill_prompt}

위 전문성을 바탕으로 아래 VE 아이디어를 기술적으로 검증하세요.

[프로젝트] {brief.project_name} ({brief.project_type})
[아이디어] {idea.get('idea_name', '')}
- 현재: {idea.get('current', '')}
- 제안: {idea.get('proposed', '')}
- 예상 효과: {idea.get('expected_saving', '')}
- 위험: {', '.join(idea.get('risks', []))}

JSON으로만 답변하세요:
{{"recommendation": "적극추천|조건부추천|보류|부적합", "feasibility": 0.0~1.0, "code_compliance": "적합|재검토|부적합", "performance_impact": "개선|유지|저하", "concerns": ["우려1"], "conditions": ["조건1"]}}"""

        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash", contents=[prompt],
                config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=500),
            )
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            return DomainReview(
                discipline=self.discipline,
                idea_name=idea.get("idea_name", ""),
                recommendation=data.get("recommendation", "보류"),
                feasibility=float(data.get("feasibility", 0.5)),
                code_compliance=data.get("code_compliance", "재검토"),
                performance_impact=data.get("performance_impact", "유지"),
                concerns=data.get("concerns", []),
                conditions=data.get("conditions", []),
            )
        except Exception as e:
            return DomainReview(
                discipline=self.discipline, idea_name=idea.get("idea_name", ""),
                recommendation="보류", concerns=[f"검증 실패: {e}"]
            )


# ═══════════════════════════════════════════════════
#  Task 31: VE Leader 오케스트레이터
# ═══════════════════════════════════════════════════

class VELeader:
    """VE Multi-Agent 세션을 관리하고 워크플로를 제어하는 오케스트레이터"""

    def __init__(self):
        self.sessions: dict[str, VESession] = {}

    def run_session(self,
                    brief: ProjectBrief,
                    design: Optional[DesignAnalysis] = None,
                    cost: Optional[CostBreakdown] = None) -> VESession:
        """전체 VE 워크플로 실행"""
        session_id = str(uuid.uuid4())[:8]
        session = VESession(session_id=session_id, project_brief=brief)
        session.status = "running"
        self.sessions[session_id] = session

        logger.info(f"[VE Session {session_id}] 시작: {brief.project_name}")

        # ── Step 1: 분석 대상 선정 ──
        session.current_step = 1
        targets = self._select_targets(brief, design, cost)
        session.targets = targets
        logger.info(f"  Step 1: 분석 대상 {len(targets)}건 선정")

        # ── Step 2: 유사 사례 검색 ──
        session.current_step = 2
        request = AgentRequest.create(brief, design, cost, step=2, session_id=session_id)
        db_response = DBSearchAgent().run(request, targets)
        session.step_results[2] = db_response
        similar = db_response.result.get("similar_cases", {})
        logger.info(f"  Step 2: 유사 사례 {db_response.result.get('total_found', 0)}건 검색")

        # ── Step 3: 아이디어 도출 ──
        session.current_step = 3
        idea_response = IdeaAgent().run(request, targets, similar)
        session.step_results[3] = idea_response
        ideas_data = idea_response.result.get("ideas", [])
        session.ideas = [
            VEIdea(**{k: v for k, v in d.items() if k in VEIdea.__dataclass_fields__})
            for d in ideas_data
        ]
        logger.info(f"  Step 3: 아이디어 {len(session.ideas)}건 도출")

        # ── Step 4: 도메인 검증 ──
        session.current_step = 4
        reviews = []
        for idea_d in ideas_data[:5]:  # 상위 5개만 검증 (API 비용 절약)
            for disc in idea_d.get("domain_review_needed", [])[:2]:
                agent = DomainAgent(disc)
                review = agent.review(idea_d, brief)
                reviews.append(review)
        session.domain_reviews = reviews
        logger.info(f"  Step 4: 도메인 검증 {len(reviews)}건 완료")

        # ── Step 5: 보고서 초안 생성 ──
        session.current_step = 5
        report = self._generate_report(session, similar)
        session.report_markdown = report
        logger.info(f"  Step 5: 보고서 초안 생성 완료 ({len(report)}자)")

        session.current_step = 6
        session.status = "completed"
        logger.info(f"[VE Session {session_id}] 완료")
        return session

    def _select_targets(self,
                        brief: ProjectBrief,
                        design: Optional[DesignAnalysis],
                        cost: Optional[CostBreakdown]) -> list[AnalysisTarget]:
        """Step 1: 분석 대상 자동 선정"""
        targets = []

        # 1) 도면 AI 플래그 항목 우선
        if design:
            for elem in design.flagged_elements:
                if brief.focus_disciplines and elem.discipline not in brief.focus_disciplines:
                    continue
                cost_ratio = 0.0
                if cost:
                    disc_items = cost.items_by_discipline(elem.discipline)
                    cost_ratio = sum(i.cost_ratio for i in disc_items) / max(len(disc_items), 1)
                targets.append(AnalysisTarget(
                    discipline=elem.discipline,
                    element_name=elem.element_name,
                    current_spec=elem.current_spec,
                    cost_ratio=cost_ratio,
                    flags=elem.flags,
                    search_query=f"{elem.element_name} {elem.current_spec}",
                ))

        # 2) 비용 상위 항목
        if cost and len(targets) < 5:
            for item in cost.top_cost_items[:10]:
                if brief.focus_disciplines and item.discipline not in brief.focus_disciplines:
                    continue
                if any(t.element_name == item.item_name for t in targets):
                    continue
                targets.append(AnalysisTarget(
                    discipline=item.discipline,
                    element_name=item.item_name,
                    current_spec=item.work_type,
                    cost_ratio=item.cost_ratio,
                    search_query=f"{item.work_type} {item.item_name}",
                ))
                if len(targets) >= 5:
                    break

        # 3) 외부 데이터 없으면 사용자 입력 기반
        if not targets:
            for disc in (brief.focus_disciplines or ["건축"]):
                targets.append(AnalysisTarget(
                    discipline=disc,
                    element_name=f"{disc} VE 대상",
                    search_query=f"{brief.project_type} {disc} VE",
                ))

        return targets[:8]  # 최대 8개

    def _generate_report(self, session: VESession, similar_cases: dict) -> str:
        """Step 5: 보고서 초안 생성 (Markdown)"""
        b = session.project_brief
        lines = [
            f"# VE 대안 보고서 (AI 초안)",
            f"",
            f"> ⚠ **이 보고서는 AI가 생성한 초안입니다. 엔지니어의 검토/수정 후 확정하세요.**",
            f"",
            f"## 프로젝트 개요",
            f"| 항목 | 내용 |",
            f"|---|---|",
            f"| 프로젝트명 | {b.project_name} |",
            f"| 유형 | {b.project_type} |",
            f"| 규모 | {b.total_area:,.0f}㎡ |",
            f"| 공사비 | {b.total_cost:,.0f}백만원 |",
            f"| VE 목표 | {b.ve_target_rate}% 절감 |",
            f"",
            f"## 분석 대상 ({len(session.targets)}건)",
            f"| # | 분야 | 대상 | 현재 사양 | 비용비중 |",
            f"|---|---|---|---|---|",
        ]
        for i, t in enumerate(session.targets, 1):
            flags = " ".join(f"🚩{f}" for f in t.flags) if t.flags else ""
            lines.append(f"| {i} | {t.discipline} | {t.element_name} | {t.current_spec} | {t.cost_ratio:.1f}% {flags} |")

        lines.extend(["", f"## VE 아이디어 ({len(session.ideas)}건)", ""])

        for i, idea in enumerate(session.ideas, 1):
            refs = ", ".join(f"#{r}" for r in idea.reference_cases) if idea.reference_cases else "없음"
            conf_mark = "✅" if idea.confidence >= 0.5 else "⚠"

            # 해당 아이디어의 도메인 검증 결과 찾기
            reviews_for_idea = [r for r in session.domain_reviews if r.idea_name == idea.idea_name]
            review_text = ""
            if reviews_for_idea:
                for r in reviews_for_idea:
                    review_text += f"  - [{r.discipline}] {r.recommendation} (실현성 {r.feasibility:.0%})\n"

            lines.extend([
                f"### 아이디어 {i}: {idea.idea_name} {conf_mark}",
                f"- **분류**: {idea.category}",
                f"- **현재**: {idea.current}",
                f"- **제안**: {idea.proposed}",
                f"- **예상 효과**: {idea.expected_saving}",
                f"- **근거 사례**: {refs}",
                f"- **위험**: {', '.join(idea.risks) or '없음'}",
            ])
            if review_text:
                lines.extend([f"- **도메인 검증**:", review_text])
            lines.append("")

        lines.extend([
            "---",
            f"*생성일: {time.strftime('%Y-%m-%d %H:%M')} | 세션: {session.session_id}*",
            f"*⚠ AI 초안 — 반드시 전문 엔지니어의 검토를 거친 후 사용하세요.*",
        ])

        return "\n".join(lines)


# ═══════════════════════════════════════════════════
#  CLI 테스트
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 60)
    print("  VE Multi-Agent System — Test Run")
    print("=" * 60)

    # 테스트용 프로젝트
    brief = ProjectBrief(
        project_name="테스트 공동주택 신축공사",
        project_type="공동주택",
        total_area=45000,
        total_cost=85000,
        ve_target_rate=5.0,
        focus_disciplines=["건축", "전기"],
        constraints=["공기 변경 불가"],
    )

    # 도면/내역 AI 없이 실행 (graceful degradation)
    leader = VELeader()
    session = leader.run_session(brief)

    print(f"\n{'=' * 60}")
    print(f"  세션 결과: {session.status}")
    print(f"  아이디어: {len(session.ideas)}건")
    print(f"  도메인 검증: {len(session.domain_reviews)}건")
    print(f"  보고서: {len(session.report_markdown)}자")
    print(f"{'=' * 60}")
    print(f"\n{session.report_markdown[:2000]}")

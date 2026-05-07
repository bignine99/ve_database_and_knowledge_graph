"""
VE Multi-Agent 시스템 — 입출력 스키마 정의

Task 29: 외부 인터페이스 (ProjectBrief, DesignAnalysis, CostBreakdown)
Task 30: Agent 간 내부 인터페이스 (AgentRequest, AgentResponse, Step별 Result)
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import uuid
import time


# ═══════════════════════════════════════════════════
#  Task 29: 외부 입력 스키마
# ═══════════════════════════════════════════════════

@dataclass
class ProjectBrief:
    """사용자가 입력하는 프로젝트 기본 정보"""
    project_name: str
    project_type: str = ""                       # "공동주택" | "학교" | "청사" | ...
    total_area: float = 0.0                      # 연면적 (㎡)
    total_cost: float = 0.0                      # 총 공사비 (백만원)
    ve_target_rate: float = 5.0                  # VE 목표 절감율 (%)
    focus_disciplines: list[str] = field(default_factory=list)   # ["건축", "전기"]
    constraints: list[str] = field(default_factory=list)         # ["공기 변경 불가"]
    description: str = ""                        # 프로젝트 추가 설명

    def validate(self) -> list[str]:
        """필수 필드 검증, 에러 메시지 리스트 반환"""
        errors = []
        if not self.project_name or not self.project_name.strip():
            errors.append("project_name은 필수입니다.")
        return errors


@dataclass
class DesignElement:
    """도면 AI가 분석한 개별 설계 요소"""
    discipline: str           # "건축" | "토목" | "전기" | "기계설비" | "배관" | "조경"
    element_name: str         # "옥상 방수층"
    current_spec: str = ""    # "우레탄 도막방수 T=3mm"
    quantity: str = ""        # "2,500㎡"
    flags: list[str] = field(default_factory=list)    # ["과잉설계", "고비용"]
    notes: str = ""


@dataclass
class DesignAnalysis:
    """도면 분석 AI의 출력 (외부 시스템에서 제공)"""
    source: str = "design_ai"
    version: str = "1.0"
    elements: list[DesignElement] = field(default_factory=list)

    @property
    def flagged_elements(self) -> list[DesignElement]:
        """과잉설계/고비용 등 플래그가 있는 요소만 필터"""
        return [e for e in self.elements if e.flags]


@dataclass
class CostItem:
    """내역 AI가 분석한 개별 비용 항목"""
    discipline: str           # "건축"
    work_type: str            # "방수코킹공사"
    item_name: str            # "우레탄 도막방수"
    unit_cost: float = 0.0
    quantity: float = 0.0
    total_cost: float = 0.0
    cost_ratio: float = 0.0   # 전체 대비 비중 (%)


@dataclass
class CostBreakdown:
    """내역/비용 분석 AI의 출력 (외부 시스템에서 제공)"""
    source: str = "cost_ai"
    version: str = "1.0"
    items: list[CostItem] = field(default_factory=list)

    @property
    def top_cost_items(self) -> list[CostItem]:
        """비용 비중 상위 20개 항목"""
        return sorted(self.items, key=lambda x: -x.cost_ratio)[:20]

    def items_by_discipline(self, discipline: str) -> list[CostItem]:
        """특정 분야의 비용 항목"""
        return [i for i in self.items if i.discipline == discipline]


# ═══════════════════════════════════════════════════
#  Task 30: Agent 간 내부 인터페이스
# ═══════════════════════════════════════════════════

class AgentStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class AgentRequest:
    """모든 Agent 호출의 공통 입력"""
    session_id: str
    step_number: int
    project_brief: ProjectBrief
    previous_results: dict = field(default_factory=dict)
    design_analysis: Optional[DesignAnalysis] = None
    cost_breakdown: Optional[CostBreakdown] = None

    @staticmethod
    def create(brief: ProjectBrief,
               design: Optional[DesignAnalysis] = None,
               cost: Optional[CostBreakdown] = None,
               step: int = 1,
               session_id: str = "") -> "AgentRequest":
        return AgentRequest(
            session_id=session_id or str(uuid.uuid4())[:8],
            step_number=step,
            project_brief=brief,
            design_analysis=design,
            cost_breakdown=cost,
        )


@dataclass
class AgentResponse:
    """모든 Agent 출력의 공통 형식"""
    agent_name: str
    step_number: int
    status: AgentStatus = AgentStatus.SUCCESS
    confidence: float = 0.0                       # 0.0 ~ 1.0
    result: dict = field(default_factory=dict)     # Agent별 상세 결과
    references: list[int] = field(default_factory=list)  # 근거 대안 번호
    warnings: list[str] = field(default_factory=list)
    next_agents: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "step_number": self.step_number,
            "status": self.status.value,
            "confidence": round(self.confidence, 3),
            "result": self.result,
            "references": self.references,
            "warnings": self.warnings,
            "next_agents": self.next_agents,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
        }


# ── Step별 결과 타입 힌트 ──

@dataclass
class AnalysisTarget:
    """VE Leader가 선정한 분석 대상"""
    discipline: str
    element_name: str
    current_spec: str = ""
    cost_ratio: float = 0.0
    flags: list[str] = field(default_factory=list)
    search_query: str = ""   # 시맨틱 검색용 질의


@dataclass
class SimilarCase:
    """DB에서 검색된 유사 사례"""
    alt_number: int
    title: str
    similarity: float           # 0.0 ~ 1.0
    how1: str = ""
    how2_code: str = ""
    how2_name: str = ""
    space: str = ""
    value_type: str = ""
    savings_rate: float = 0.0
    perf_change: float = 0.0
    cost_change: float = 0.0
    value_change: float = 0.0
    cluster_id: int = -1


@dataclass
class VEIdea:
    """도출된 VE 아이디어"""
    idea_name: str
    category: str               # "재료대체" | "공법변경" | "규격최적화" | ...
    current: str                # 현재 방식
    proposed: str               # 제안 대안
    expected_saving: str = ""   # "약 5~10% 절감"
    confidence: float = 0.5
    reference_cases: list[int] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    domain_review_needed: list[str] = field(default_factory=list)
    priority_score: float = 0.0


@dataclass
class DomainReview:
    """도메인 전문가 검증 결과"""
    discipline: str
    idea_name: str
    recommendation: str = "보류"    # "적극추천" | "조건부추천" | "보류" | "부적합"
    feasibility: float = 0.5       # 0.0 ~ 1.0
    code_compliance: str = "재검토"  # "적합" | "재검토" | "부적합"
    performance_impact: str = "유지"  # "개선" | "유지" | "저하"
    concerns: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)


@dataclass
class VESession:
    """VE 세션 전체 상태"""
    session_id: str
    project_brief: ProjectBrief
    created_at: float = field(default_factory=time.time)
    status: str = "initialized"   # initialized → running → completed → failed
    current_step: int = 0
    total_steps: int = 6
    targets: list[AnalysisTarget] = field(default_factory=list)
    similar_cases: dict[str, list[SimilarCase]] = field(default_factory=dict)
    ideas: list[VEIdea] = field(default_factory=list)
    domain_reviews: list[DomainReview] = field(default_factory=list)
    report_markdown: str = ""
    step_results: dict[int, AgentResponse] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        return self.current_step / self.total_steps if self.total_steps > 0 else 0.0

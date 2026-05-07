"""
FAST Agent — 기능 분석 + Mermaid 다이어그램 자동 생성 (Task 35)

SKILL_FAST_Diagram_Developer.md 기반으로:
  - 프로젝트 기능을 계층적으로 분해
  - 기능-비용 불균형 영역 자동 식별
  - Mermaid 다이어그램 자동 생성
"""

import os, sys, json, time, logging
from dataclasses import dataclass, field, asdict
from typing import Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.agents.schemas import (
    AgentRequest, AgentResponse, AgentStatus,
    AnalysisTarget, ProjectBrief,
)

logger = logging.getLogger(__name__)


@dataclass
class FunctionNode:
    """기능 분해 트리의 노드"""
    name: str
    level: int = 0
    func_type: str = "primary"      # primary | secondary | tertiary
    cost_ratio: float = 0.0
    value_ratio: float = 0.0        # 비용 대비 가치
    children: list = field(default_factory=list)
    flag: str = ""                   # "고비용저가치" | "과잉설계" | ""


class FastAgent:
    """FAST 기능 분석 + Mermaid 다이어그램 자동 생성"""

    def __init__(self):
        self.skill_prompt = self._load_skill()

    def _load_skill(self) -> str:
        path = os.path.join(_ROOT, ".ve_SKILL", "SKILL_FAST_Diagram_Developer.md")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()[:2500]
        return "당신은 FAST Diagram 기능 분석 전문가입니다."

    def run(self, request: AgentRequest,
            targets: list[AnalysisTarget]) -> AgentResponse:
        t0 = time.time()
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return AgentResponse(
                agent_name="FastAgent", step_number=2,
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
                agent_name="FastAgent", step_number=2,
                status=AgentStatus.FAILED,
                result={"error": str(e)},
                elapsed_seconds=time.time() - t0,
            )

        brief = request.project_brief
        targets_text = "\n".join(
            f"- [{t.discipline}] {t.element_name}: {t.current_spec} (비용비중 {t.cost_ratio:.1f}%)"
            for t in targets
        )

        prompt = f"""{self.skill_prompt[:1500]}

위 전문성을 바탕으로, 아래 프로젝트의 기능을 분석하세요.

[프로젝트]
- 이름: {brief.project_name}
- 유형: {brief.project_type}
- 규모: {brief.total_area:,.0f}m2, 공사비: {brief.total_cost:,.0f}백만원

[분석 대상 공종]
{targets_text}

[요구사항]
다음 JSON 형식으로만 답변하세요:
{{
  "project_goal": "프로젝트 최상위 목표 (동사+명사)",
  "functions": [
    {{
      "name": "기능명 (동사+명사)",
      "level": 0,
      "type": "primary|secondary|tertiary",
      "cost_ratio": 0.0,
      "children": [
        {{"name": "하위기능", "level": 1, "type": "secondary", "cost_ratio": 0.0, "children": []}}
      ]
    }}
  ],
  "high_cost_low_value": ["고비용 저가치 기능 목록"],
  "optimization_opportunities": ["기능 통합/삭제/대체 기회"]
}}

JSON만 출력하세요."""

        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash", contents=[prompt],
                config=types.GenerateContentConfig(temperature=0.4, max_output_tokens=2000),
            )
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)

            # Mermaid 다이어그램 생성
            mermaid = self._generate_mermaid(data)

            return AgentResponse(
                agent_name="FastAgent", step_number=2,
                status=AgentStatus.SUCCESS,
                confidence=0.7,
                result={
                    "fast_analysis": data,
                    "mermaid_diagram": mermaid,
                    "high_cost_low_value": data.get("high_cost_low_value", []),
                    "optimization_opportunities": data.get("optimization_opportunities", []),
                },
                elapsed_seconds=time.time() - t0,
            )
        except json.JSONDecodeError:
            return AgentResponse(
                agent_name="FastAgent", step_number=2,
                status=AgentStatus.PARTIAL,
                result={"raw_response": raw[:1000], "mermaid_diagram": ""},
                warnings=["FAST 분석 JSON 파싱 실패"],
                elapsed_seconds=time.time() - t0,
            )
        except Exception as e:
            return AgentResponse(
                agent_name="FastAgent", step_number=2,
                status=AgentStatus.FAILED,
                result={"error": str(e)},
                elapsed_seconds=time.time() - t0,
            )

    def _generate_mermaid(self, data: dict) -> str:
        """FAST 분석 결과를 Mermaid 다이어그램으로 변환"""
        lines = ["graph TD"]
        goal = data.get("project_goal", "프로젝트 목표")
        lines.append(f'  ROOT["{goal}"]')

        node_id = 0
        functions = data.get("functions", [])

        for func in functions:
            node_id += 1
            fid = f"F{node_id}"
            name = func.get("name", "")
            ftype = func.get("type", "primary")

            # 스타일 결정
            if ftype == "primary":
                lines.append(f'  ROOT --> {fid}["{name}"]')
                lines.append(f"  style {fid} fill:#1e40af,color:#fff,stroke:#1e3a8a")
            else:
                lines.append(f'  ROOT --> {fid}["{name}"]')
                lines.append(f"  style {fid} fill:#3b82f6,color:#fff,stroke:#2563eb")

            # 하위 기능
            for child in func.get("children", []):
                node_id += 1
                cid = f"F{node_id}"
                cname = child.get("name", "")
                lines.append(f'  {fid} --> {cid}["{cname}"]')
                lines.append(f"  style {cid} fill:#93c5fd,color:#1e3a5f,stroke:#60a5fa")

                for sub in child.get("children", []):
                    node_id += 1
                    sid = f"F{node_id}"
                    sname = sub.get("name", "")
                    lines.append(f'  {cid} --> {sid}["{sname}"]')
                    lines.append(f"  style {sid} fill:#dbeafe,color:#1e3a5f,stroke:#93c5fd")

        lines.append(f"  style ROOT fill:#0f172a,color:#fff,stroke:#1e293b,stroke-width:2px")
        return "\n".join(lines)

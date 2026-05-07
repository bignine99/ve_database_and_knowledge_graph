"""
VE Roundtable — Multi-Agent 토론 시스템 (Async v2)

VE Leader가 회의를 진행하고, 각 도메인 전문가가 순차적으로 발언하며,
Idea Developer가 아이디어를 제안하고, FAST 전문가가 도식화하는 토론 세션.

v2: threading 기반 비동기 실행 — 세션 생성 즉시 반환, 백그라운드 실행,
    각 Agent 발언 완료 시 메시지 즉시 축적 → 프론트엔드 폴링으로 실시간 수신.
"""

import os, sys, json, time, uuid, logging, threading
from dataclasses import dataclass, field, asdict
from typing import Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logger = logging.getLogger(__name__)

# ── Agent 캐릭터 정의 ──

AGENTS = {
    "leader": {"name": "VE Leader", "role": "VE 총괄 리더", "emoji": "\U0001f3a9", "color": "#1e40af"},
    "architect": {"name": "건축 전문가", "role": "건축 도메인", "emoji": "\U0001f3d7", "color": "#b45309"},
    "civil": {"name": "토목 전문가", "role": "토목 도메인", "emoji": "\U0001f6e4", "color": "#065f46"},
    "electronic": {"name": "전기 전문가", "role": "전기 도메인", "emoji": "\u26a1", "color": "#7c3aed"},
    "mechanic": {"name": "기계설비 전문가", "role": "기계설비 도메인", "emoji": "\u2699", "color": "#0369a1"},
    "plumbing": {"name": "배관 전문가", "role": "배관 도메인", "emoji": "\U0001f6b0", "color": "#0e7490"},
    "landscape": {"name": "조경 전문가", "role": "조경 도메인", "emoji": "\U0001f33f", "color": "#15803d"},
    "idea": {"name": "Idea Developer", "role": "아이디어 도출", "emoji": "\U0001f4a1", "color": "#d97706"},
    "fast": {"name": "FAST 전문가", "role": "기능 분석", "emoji": "\U0001f4ca", "color": "#dc2626"},
    "data": {"name": "Data Analyst", "role": "데이터 분석", "emoji": "\U0001f4c8", "color": "#6366f1"},
}

DISCIPLINE_TO_AGENT = {
    "건축": "architect", "토목": "civil", "전기": "electronic",
    "기계설비": "mechanic", "배관": "plumbing", "조경": "landscape",
}

SKILL_FILES = {
    "architect": "SKILL_Architect.md",
    "civil": "SKILL_Civil.md",
    "electronic": "SKILL_Electronic.md",
    "mechanic": "SKILL_Mechanic.md",
    "plumbing": "SKILL_Plumbing.md",
    "landscape": "SKILL_Landscape.md",
    "idea": "SKILL_idea_developer.md",
    "fast": "SKILL_FAST_Diagram_Developer.md",
    "data": "SKILL_data_analyst.md",
}


@dataclass
class ChatMessage:
    agent_id: str
    agent_name: str
    agent_emoji: str
    agent_color: str
    content: str
    step: int = 0
    timestamp: float = field(default_factory=time.time)
    msg_type: str = "text"  # text | mermaid | ideas | summary

    def to_dict(self):
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_emoji": self.agent_emoji,
            "agent_color": self.agent_color,
            "content": self.content,
            "step": self.step,
            "timestamp": self.timestamp,
            "msg_type": self.msg_type,
        }


@dataclass
class RoundtableSession:
    session_id: str
    project_text: str = ""
    project_name: str = ""
    messages: list[ChatMessage] = field(default_factory=list)
    status: str = "initialized"
    created_at: float = field(default_factory=time.time)
    error: str = ""
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add_msg(self, agent_id: str, content: str, step: int = 0, msg_type: str = "text"):
        info = AGENTS.get(agent_id, AGENTS["leader"])
        msg = ChatMessage(
            agent_id=agent_id,
            agent_name=info["name"],
            agent_emoji=info["emoji"],
            agent_color=info["color"],
            content=content,
            step=step,
            msg_type=msg_type,
        )
        with self._lock:
            self.messages.append(msg)
        return msg


def _load_skill(agent_id: str) -> str:
    fname = SKILL_FILES.get(agent_id)
    if not fname:
        return ""
    path = os.path.join(_ROOT, ".ve_SKILL", fname)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()[:1500]
    return ""


def _call_gemini(prompt: str, temperature: float = 0.5) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return "(API 키 없음)"
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(temperature=temperature, max_output_tokens=800),
        )
        return resp.text.strip()
    except Exception as e:
        return f"(오류: {e})"


def _run_roundtable_worker(session: RoundtableSession, disciplines: list[str]):
    """백그라운드 스레드에서 실행되는 라운드테이블 토론 워커

    10-Step 구조 — 모든 Agent가 최소 2회 이상 발언:
      Step 1:  VE Leader 개회
      Step 2:  도메인 전문가 1차 검토
      Step 3:  Data Analyst — DB 유사 사례 검색
      Step 4:  Idea Developer — 초기 아이디어 제안
      Step 5:  FAST 전문가 — 기능 분석
      Step 6:  도메인 전문가 2차 — 아이디어/FAST 피드백
      Step 7:  Data Analyst 2차 — 검증/추가 분석
      Step 8:  Idea Developer 2차 — 최종 아이디어 정리
      Step 9:  FAST 전문가 2차 — 기능-비용 최종 평가
      Step 10: VE Leader 종합
    """
    try:
        session.status = "running"
        brief = session.project_text[:2000]

        # ═══ Step 1: VE Leader 개회 ═══
        leader_prompt = f"""당신은 VE(Value Engineering) 회의의 리더입니다.
아래 프로젝트 정보를 읽고, VE 회의를 시작하세요.

[프로젝트 정보]
{brief}

[요구사항]
1. 프로젝트를 간결히 요약 (3~4문장)
2. VE 분석 방향을 제시
3. 어떤 분야를 중점적으로 검토할지 언급
4. 참여 전문가들에게 검토를 요청하는 말로 마무리

존댓말로, 회의 리더의 톤으로 작성하세요. 300자 이내."""

        msg = _call_gemini(leader_prompt, 0.4)
        session.add_msg("leader", msg, step=1)

        # ═══ Step 2: 도메인 전문가 1차 발언 ═══
        active_agents = []  # (agent_id, discipline) 쌍 저장
        for disc in disciplines[:3]:
            agent_id = DISCIPLINE_TO_AGENT.get(disc, "architect")
            skill = _load_skill(agent_id)
            agent_info = AGENTS[agent_id]
            active_agents.append((agent_id, disc))

            domain_prompt = f"""{skill[:800]}

위 전문성을 바탕으로, VE 회의에서 발언하세요.

[프로젝트 정보]
{brief[:1000]}

[요구사항]
당신은 {agent_info['name']}({agent_info['role']})입니다.
1. 이 프로젝트에서 {disc} 분야의 핵심 검토 포인트를 2~3가지 제시
2. 비용 절감 가능성이 있는 영역을 지적
3. 주의해야 할 기준/법규가 있으면 언급
4. 다른 전문가에게 협의가 필요한 부분이 있으면 제안

회의 참여자의 톤으로, 존댓말로, 250자 이내로 작성하세요."""

            msg = _call_gemini(domain_prompt, 0.5)
            session.add_msg(agent_id, msg, step=2)

        # ═══ Step 3: Data Analyst — DB 유사 사례 검색 ═══
        cases_text_for_context = ""
        try:
            from src.semantic_search import hybrid_search
            search_query = f"{session.project_name} VE"
            results = hybrid_search(search_query, top_k=5, use_gemini=False)
            cases = results.get("results", [])[:5]

            if cases:
                cases_text = "DB에서 유사 사례를 검색한 결과, 다음과 같은 관련 대안을 찾았습니다:\n\n"
                for i, c in enumerate(cases, 1):
                    cases_text += (f"{i}. **대안 #{c.get('alt_number', '?')}** — {c.get('title', '')}\n"
                                  f"   (유사도 {c.get('hybrid_score', c.get('semantic_score', 0)):.1%}, "
                                  f"절감율 {c.get('savings_rate', 0):.1f}%)\n")
                cases_text += "\n이 사례들을 참고하여 아이디어를 도출해보겠습니다."
                cases_text_for_context = cases_text
            else:
                cases_text = "DB에서 직접적으로 유사한 사례를 찾지 못했습니다. 일반적인 VE 패턴을 기반으로 진행하겠습니다."
            session.add_msg("data", cases_text, step=3)
        except Exception as e:
            session.add_msg("data", f"데이터 검색 중 오류가 발생했습니다: {e}", step=3)

        # ═══ Step 4: Idea Developer — 초기 아이디어 제안 ═══
        idea_skill = _load_skill("idea")
        disc_text = ", ".join(disciplines)

        idea_prompt = f"""{idea_skill[:600]}

위 전문성을 바탕으로, VE 회의에서 아이디어를 제안하세요.

[프로젝트]
{brief[:800]}

[관심 분야]
{disc_text}

[요구사항]
당신은 VE Idea Developer입니다.
1. 3~4개의 구체적인 VE 아이디어를 제안
2. 각 아이디어: 제안명, 현재 방식 → 대안, 예상 효과
3. 패턴 기반: 재료대체, 공법변경, 규격최적화 등에서 선택
4. 실현 가능하고 구체적인 아이디어만 제시

회의 참여자 톤으로, 300자 이내로 작성하세요."""

        idea_msg = _call_gemini(idea_prompt, 0.7)
        session.add_msg("idea", idea_msg, step=4)

        # ═══ Step 5: FAST 전문가 — 기능 분석 ═══
        fast_skill = _load_skill("fast")
        fast_prompt = f"""{fast_skill[:600]}

위 전문성을 바탕으로 VE 회의에서 발언하세요.

[프로젝트]
{brief[:600]}

[요구사항]
당신은 FAST Diagram 전문가입니다.
1. 이 프로젝트의 핵심 기능을 3~4가지로 분해
2. 기능-비용 불균형이 예상되는 영역을 지적
3. 기능 통합/삭제 기회를 제안

회의 참여자 톤으로, 200자 이내로 작성하세요."""

        fast_msg = _call_gemini(fast_prompt, 0.5)
        session.add_msg("fast", fast_msg, step=5)

        # ═══ Step 6: 도메인 전문가 2차 — 아이디어/FAST 결과에 대한 피드백 ═══
        for agent_id, disc in active_agents:
            agent_info = AGENTS[agent_id]

            feedback_prompt = f"""당신은 {agent_info['name']}({agent_info['role']})입니다.
VE 회의에서 Idea Developer와 FAST 전문가가 다음과 같은 제안을 했습니다:

[Idea Developer 제안 요약]
{idea_msg[:500]}

[FAST 전문가 분석 요약]
{fast_msg[:300]}

[요구사항]
위 제안에 대해 {disc} 분야 전문가로서 피드백하세요.
1. 제안된 아이디어 중 {disc} 관점에서 실현 가능한 것과 주의할 점을 지적
2. 추가로 검토해야 할 기술적 사항이 있으면 제시
3. 보완이 필요한 아이디어가 있으면 개선 방향을 제안

회의 참여자의 톤으로, 존댓말로, 200자 이내로 작성하세요."""

            msg = _call_gemini(feedback_prompt, 0.5)
            session.add_msg(agent_id, msg, step=6)

        # ═══ Step 7: Data Analyst 2차 — 검증/추가 분석 ═══
        with session._lock:
            recent_msgs = "\n".join([f"[{m.agent_name}] {m.content[:150]}" for m in session.messages[-6:]])

        data2_prompt = f"""당신은 VE 회의의 Data Analyst입니다.

[최근 회의 논의 내용]
{recent_msgs[:1200]}

[요구사항]
지금까지의 논의를 데이터 관점에서 분석하세요.
1. 제안된 아이디어들의 비용 절감 효과를 정량적으로 추정 (가능한 범위에서)
2. 유사 프로젝트의 일반적인 VE 절감율과 비교
3. 우선순위가 높은 아이디어를 데이터 기반으로 추천
4. 리스크가 있는 아이디어에 대해 주의 사항 제시

회의 참여자 톤으로, 250자 이내로 작성하세요."""

        msg = _call_gemini(data2_prompt, 0.5)
        session.add_msg("data", msg, step=7)

        # ═══ Step 8: Idea Developer 2차 — 피드백 반영 최종 아이디어 ═══
        with session._lock:
            feedback_msgs = "\n".join([f"[{m.agent_name}] {m.content[:150]}"
                                       for m in session.messages if m.step in (6, 7)])

        idea2_prompt = f"""당신은 VE Idea Developer입니다.
앞서 제안한 아이디어에 대해 도메인 전문가와 Data Analyst의 피드백을 받았습니다:

[전문가 피드백]
{feedback_msgs[:1000]}

[요구사항]
1. 피드백을 반영하여 최종 아이디어를 2~3개로 압축 정리
2. 각 아이디어의 예상 절감 효과와 실행 난이도를 명시
3. 즉시 추진 가능한 아이디어와 추가 검토가 필요한 아이디어를 구분

회의 참여자 톤으로, 250자 이내로 작성하세요."""

        msg = _call_gemini(idea2_prompt, 0.6)
        session.add_msg("idea", msg, step=8)

        # ═══ Step 9: FAST 전문가 2차 — 최종 기능-비용 평가 ═══
        with session._lock:
            all_ideas = "\n".join([f"[{m.agent_name}] {m.content[:150]}"
                                   for m in session.messages if m.step in (4, 8)])

        fast2_prompt = f"""당신은 FAST Diagram 전문가입니다.
최종 정리된 VE 아이디어에 대해 기능-비용 관점의 최종 평가를 해주세요.

[최종 아이디어]
{all_ideas[:800]}

[요구사항]
1. 각 아이디어가 프로젝트의 핵심 기능에 미치는 영향을 평가
2. 기능 저하 없이 비용 절감이 가능한 아이디어를 강조
3. 기능-비용 균형 관점에서 최종 우선순위를 제시

회의 참여자 톤으로, 200자 이내로 작성하세요."""

        msg = _call_gemini(fast2_prompt, 0.5)
        session.add_msg("fast", msg, step=9)

        # ═══ Step 10: VE Leader 종합 ═══
        with session._lock:
            all_msgs = "\n".join([f"[{m.agent_name}] {m.content[:200]}" for m in session.messages])

        closing_prompt = f"""당신은 VE 회의 리더입니다.
아래는 지금까지의 VE 회의 논의 내용입니다:

{all_msgs[:2500]}

[요구사항]
1. 논의된 주요 포인트를 3~4가지로 정리
2. 우선적으로 추진할 아이디어를 선정하고 그 이유를 설명
3. 각 아이디어의 담당 분야와 다음 단계(상세 검토, 비용 산출 등)를 제안
4. 회의를 마무리하는 감사 인사

회의 리더 톤으로, 존댓말로, 350자 이내로 작성하세요."""

        msg = _call_gemini(closing_prompt, 0.4)
        session.add_msg("leader", msg, step=10, msg_type="summary")

        session.status = "completed"
        logger.info(f"[Roundtable {session.session_id}] 완료 — {len(session.messages)}개 메시지")

    except Exception as e:
        session.status = "failed"
        session.error = str(e)
        session.add_msg("leader", f"회의 진행 중 오류가 발생했습니다: {e}", step=0, msg_type="text")
        logger.error(f"[Roundtable {session.session_id}] 오류: {e}")


def start_roundtable_async(project_text: str, project_name: str = "",
                           disciplines: list[str] = None) -> RoundtableSession:
    """비동기 라운드테이블 토론 시작 — 세션 즉시 반환, 백그라운드 실행"""
    session = RoundtableSession(
        session_id=str(uuid.uuid4())[:8],
        project_text=project_text[:3000],
        project_name=project_name or "VE 분석 프로젝트",
    )
    if not disciplines:
        disciplines = ["건축", "전기"]

    thread = threading.Thread(
        target=_run_roundtable_worker,
        args=(session, disciplines),
        daemon=True,
    )
    thread.start()
    return session


# 하위 호환성: 동기 실행 함수 유지
def run_roundtable(project_text: str, project_name: str = "",
                   disciplines: list[str] = None) -> RoundtableSession:
    """VE 라운드테이블 토론 실행 (동기 — 하위 호환용)"""
    session = RoundtableSession(
        session_id=str(uuid.uuid4())[:8],
        project_text=project_text[:3000],
        project_name=project_name or "VE 분석 프로젝트",
    )
    if not disciplines:
        disciplines = ["건축", "전기"]
    _run_roundtable_worker(session, disciplines)
    return session

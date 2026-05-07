"""
VE Database Development - Semantic Search Engine
==================================================
Embedding 기반 시맨틱 검색 + KG 구조 매칭 하이브리드 검색.

Tier 1: sentence-transformers 임베딩 → 코사인 유사도 검색
Tier 2: Hybrid = Embedding + KG Hop + Gemini RAG

모델: paraphrase-multilingual-MiniLM-L12-v2 (한국어 지원, 384차원)
"""

import json
import os
import time
import numpy as np
from pathlib import Path
from typing import Optional

# ── 환경변수 ──
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ── 경로 설정 ──
EMBEDDINGS_DIR = BASE_DIR / "data" / "embeddings"
EMBEDDINGS_PATH = EMBEDDINGS_DIR / "ve_embeddings.npz"
METADATA_PATH = EMBEDDINGS_DIR / "ve_metadata.json"

# ── 모델 설정 ──
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384

# 싱글톤 모델 캐시
_model = None
_embeddings = None
_metadata = None


def _get_model():
    """sentence-transformers 모델을 로드합니다 (싱글톤)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print(f"  [SemanticSearch] Loading model: {MODEL_NAME}", flush=True)
        _model = SentenceTransformer(MODEL_NAME)
        print(f"  [SemanticSearch] Model loaded (dim={EMBEDDING_DIM})", flush=True)
    return _model


def build_embedding_index(db_conn=None) -> dict:
    """
    DB에서 727개 대안 텍스트를 읽어 임베딩 인덱스를 구축합니다.

    구축 결과:
      - data/embeddings/ve_embeddings.npz (벡터 행렬)
      - data/embeddings/ve_metadata.json  (대안 메타데이터)

    Returns:
        {"total": int, "dim": int, "build_time": float}
    """
    import psycopg2
    import psycopg2.extras

    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    model = _get_model()

    # DB 연결
    if db_conn is None:
        conn = psycopg2.connect(
            host=os.getenv("SUPABASE_DB_HOST"),
            port=int(os.getenv("SUPABASE_DB_PORT", 5432)),
            dbname=os.getenv("SUPABASE_DB_NAME", "postgres"),
            user=os.getenv("SUPABASE_DB_USER", "postgres"),
            password=os.getenv("SUPABASE_DB_PASS"),
            sslmode="require",
        )
        own_conn = True
    else:
        conn = db_conn
        own_conn = False

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 대안 텍스트 + 메타데이터 조회
    cur.execute("""
        SELECT a.alt_id, a.alt_number, a.proposal_title,
               a.original_description, a.alternative_description,
               a.location, a.how2_code, a.how2_name, a.space,
               a.value_type_corrected, a.field_category,
               v.performance_change_rate, v.cost_change_rate,
               v.value_change_rate,
               c.savings_amount, c.savings_rate
        FROM alternatives a
        LEFT JOIN value_evaluations v ON a.alt_id = v.alt_id
        LEFT JOIN cost_evaluations c ON a.alt_id = c.alt_id
              AND c.cost_type = 'project_lifecycle'
        ORDER BY a.alt_number
    """)
    rows = cur.fetchall()
    cur.close()
    if own_conn:
        conn.close()

    # 텍스트 결합 (임베딩 대상)
    texts = []
    metadata = []
    for r in rows:
        # 풍부한 컨텍스트: 제목 + 원안 + 대안 + 분류 정보
        parts = [
            r["proposal_title"] or "",
            r["original_description"] or "",
            r["alternative_description"] or "",
            r["how2_name"] or "",
            r["space"] or "",
            r["value_type_corrected"] or "",
        ]
        text = " ".join(p for p in parts if p).strip()
        texts.append(text)

        metadata.append({
            "alt_id": r["alt_id"],
            "alt_number": r["alt_number"],
            "title": r["proposal_title"] or "",
            "location": r["location"] or "",
            "how2_code": r["how2_code"] or "",
            "how2_name": r["how2_name"] or "",
            "space": r["space"] or "",
            "value_type": r["value_type_corrected"] or "",
            "field_category": r["field_category"] or "",
            "perf_change": float(r["performance_change_rate"] or 0),
            "cost_change": float(r["cost_change_rate"] or 0),
            "value_change": float(r["value_change_rate"] or 0),
            "savings": float(r["savings_amount"] or 0),
            "savings_rate": float(r["savings_rate"] or 0),
        })

    print(f"  [SemanticSearch] Encoding {len(texts)} alternatives...", flush=True)
    t0 = time.time()

    # 배치 인코딩 (GPU 없어도 727건은 ~10초)
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,  # L2 정규화 → 코사인 유사도 = 내적
    )

    build_time = time.time() - t0
    print(f"  [SemanticSearch] Encoding done in {build_time:.1f}s", flush=True)

    # 저장
    np.savez_compressed(str(EMBEDDINGS_PATH), embeddings=embeddings)
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # 글로벌 캐시 갱신
    global _embeddings, _metadata
    _embeddings = embeddings
    _metadata = metadata

    return {
        "total": len(texts),
        "dim": embeddings.shape[1],
        "build_time": round(build_time, 2),
    }


def _load_index():
    """임베딩 인덱스를 로드합니다 (싱글톤)."""
    global _embeddings, _metadata
    if _embeddings is not None and _metadata is not None:
        return

    if not EMBEDDINGS_PATH.exists() or not METADATA_PATH.exists():
        raise FileNotFoundError(
            "임베딩 인덱스가 없습니다. build_embedding_index()를 먼저 실행하세요."
        )

    data = np.load(str(EMBEDDINGS_PATH))
    _embeddings = data["embeddings"]
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        _metadata = json.load(f)

    print(f"  [SemanticSearch] Index loaded: {_embeddings.shape[0]} vectors, dim={_embeddings.shape[1]}", flush=True)


def semantic_search(query: str, top_k: int = 15) -> list[dict]:
    """
    시맨틱 검색: 질의 텍스트와 가장 유사한 VE 대안을 반환합니다.

    Args:
        query: 자연어 질의
        top_k: 반환할 최대 결과 수

    Returns:
        [{"alt_id", "alt_number", "title", "score", ...}, ...]
    """
    _load_index()
    model = _get_model()

    # 질의 임베딩
    q_emb = model.encode(
        [query],
        normalize_embeddings=True,
    )[0]  # (384,)

    # 코사인 유사도 = 내적 (L2 정규화 되어있으므로)
    scores = _embeddings @ q_emb  # (N,)

    # Top-K 인덱스
    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        meta = _metadata[idx].copy()
        meta["similarity"] = round(float(scores[idx]), 4)
        results.append(meta)

    return results


def hybrid_search(
    query: str,
    kg_graph=None,
    top_k: int = 10,
    use_gemini: bool = False,
) -> dict:
    """
    하이브리드 검색: Embedding + KG Hop + (선택) Gemini RAG.

    Step 1: 시맨틱 검색 → Top 15 후보
    Step 2: KG Hop 매칭 → 구조적 관련성 점수 추가
    Step 3: 복합 스코어로 재정렬
    Step 4: (use_gemini=True) Gemini가 자연어 분석 답변 생성

    Args:
        query: 자연어 질의
        kg_graph: NetworkX DiGraph (KG). None이면 파일에서 로드
        top_k: 최종 반환 결과 수
        use_gemini: Gemini RAG 답변 생성 여부

    Returns:
        {"query", "semantic_results", "kg_matches", "combined", "gemini_answer"}
    """
    from src.cube_taxonomy import classify_space, classify_how2, get_how_full_code

    # ── Step 1: 시맨틱 검색 ──
    sem_results = semantic_search(query, top_k=20)

    # ── Step 2: KG Hop 매칭 ──
    query_spaces = classify_space(query)
    query_how2 = classify_how2(query)

    # KG 그래프 로드
    if kg_graph is None:
        import networkx as nx
        kg_path = BASE_DIR / "data" / "kg" / "ve_knowledge_graph.graphml"
        if kg_path.exists():
            kg_graph = nx.read_graphml(str(kg_path))
        else:
            kg_graph = None

    # KG에서 각 대안의 구조적 점수 계산
    kg_scores = {}  # alt_id → kg_score
    kg_paths = {}   # alt_id → [path_strings]
    if kg_graph is not None:
        for node, data in kg_graph.nodes(data=True):
            if data.get("node_type") != "Alternative":
                continue

            score = 0
            paths = []

            # Space 매칭
            for neighbor in kg_graph.successors(node):
                nd = kg_graph.nodes[neighbor]
                if nd.get("node_type") == "Space" and nd.get("label") in query_spaces:
                    score += 2
                    paths.append(f"{data.get('label','')} →[LOCATED_IN]→ {nd['label']}")

            # HOW2 매칭
            for neighbor in kg_graph.successors(node):
                nd = kg_graph.nodes[neighbor]
                if nd.get("node_type") == "SubWorkType":
                    for h1, h2, h2name in query_how2:
                        if nd.get("how2_code") == f"{h1}-{h2}" or nd.get("label") == h2name:
                            score += 2
                            paths.append(f"{data.get('label','')} →[SUB_WORK_TYPE]→ {nd['label']}")

            if score > 0:
                kg_scores[node] = score
                kg_paths[node] = paths

    # ── Step 3: 복합 스코어 계산 ──
    # semantic_weight=0.6, kg_weight=0.4
    combined = []
    seen_ids = set()

    for r in sem_results:
        alt_id = r["alt_id"]
        sem_score = r["similarity"]
        kg_score = kg_scores.get(alt_id, 0)
        paths = kg_paths.get(alt_id, [])

        # 정규화: KG score를 0~1 범위로
        kg_norm = min(kg_score / 4.0, 1.0) if kg_score > 0 else 0.0

        # 복합 점수
        final_score = 0.6 * sem_score + 0.4 * kg_norm

        combined.append({
            **r,
            "semantic_score": sem_score,
            "kg_score": kg_score,
            "kg_paths": paths,
            "final_score": round(final_score, 4),
        })
        seen_ids.add(alt_id)

    # KG에서만 발견된 대안 추가 (시맨틱 검색에 없었던 것)
    for alt_id, kg_score in kg_scores.items():
        if alt_id not in seen_ids:
            # 메타데이터에서 찾기
            meta = next((m for m in _metadata if m["alt_id"] == alt_id), None)
            if meta:
                kg_norm = min(kg_score / 4.0, 1.0)
                combined.append({
                    **meta,
                    "similarity": 0.0,
                    "semantic_score": 0.0,
                    "kg_score": kg_score,
                    "kg_paths": kg_paths.get(alt_id, []),
                    "final_score": round(0.4 * kg_norm, 4),
                })

    # 최종 스코어 정렬
    combined.sort(key=lambda x: -x["final_score"])
    combined = combined[:top_k]

    result = {
        "query": query,
        "query_spaces": query_spaces,
        "query_how2": [(get_how_full_code(h1, h2), n) for h1, h2, n in query_how2],
        "semantic_count": len(sem_results),
        "kg_match_count": len(kg_scores),
        "combined_count": len(combined),
        "alternatives": combined,
        "gemini_answer": None,
    }

    # ── Step 4: Gemini RAG 답변 생성 ──
    if use_gemini and combined:
        result["gemini_answer"] = _generate_gemini_answer(query, combined[:5])

    return result


def _generate_gemini_answer(query: str, candidates: list[dict]) -> str:
    """
    Gemini를 사용하여 검색 결과를 기반으로 자연어 분석 답변을 생성합니다.

    개선사항:
      - 환각(Hallucination) 방지 시스템 제약
      - temperature 0.3 (사실 기반 응답 강화)
      - CUBE 분류체계 도메인 지식 주입
      - 불확실성 명시 요구

    Args:
        query: 사용자 질의
        candidates: 상위 5개 검색 결과

    Returns:
        Gemini 생성 자연어 답변
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return "⚠ GEMINI_API_KEY 환경변수가 설정되지 않았습니다."

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return f"⚠ Gemini 클라이언트 초기화 실패: {e}"

    # 후보 대안 정보를 프롬프트에 주입
    context_parts = []
    for i, c in enumerate(candidates, 1):
        savings_text = f"절감액: {c.get('savings', 0):.0f}백만원" if c.get('savings') else "절감액: 정보 없음"
        context_parts.append(
            f"### 대안 {i}: [{c['alt_number']}번] {c['title']}\n"
            f"- 분류: {c.get('how2_name', '-')} ({c.get('how2_code', '-')})\n"
            f"- 공간: {c.get('space', '-')}\n"
            f"- 가치유형: {c.get('value_type', '-')}\n"
            f"- 성능변화: {c.get('perf_change', 0):+.2f}% | 비용변화: {c.get('cost_change', 0):+.2f}% | 가치변화: {c.get('value_change', 0):+.2f}%\n"
            f"- {savings_text} | 절감율: {c.get('savings_rate', 0):.2f}%\n"
            f"- 매칭 경로: {', '.join(c.get('kg_paths', [])) or '시맨틱 매칭'}\n"
        )

    # KG 컨텍스트 수집 (Space, HOW2)
    spaces = list(set(c.get('space', '') for c in candidates if c.get('space')))
    how2s = list(set(c.get('how2_name', '') for c in candidates if c.get('how2_name')))

    prompt = f"""당신은 건설 VE(Value Engineering) 전문 자문 AI입니다.

[시스템 제약 — 반드시 준수]
1. 아래 제공된 VE 대안 데이터만 근거로 답변하세요. 데이터에 없는 방법, 기법, 제품을 제안하지 마세요.
2. 비용/성능 수치는 제공된 데이터 값만 인용하세요. 추정치를 만들지 마세요.
3. 불확실한 정보는 "데이터에서 확인되지 않음"으로 명시하세요.
4. 대안 번호를 반드시 명시하여 원본 데이터를 추적할 수 있게 하세요.

## 사용자 질의
{query}

## 건설 VE 분류체계 (CUBE 온톨로지)
- 관련 공간(WHERE): {', '.join(spaces) or '전체'}
- 관련 공종(HOW): {', '.join(how2s) or '복합'}
- 가치유형: 가치혁신형(성능↑비용↓), 비용절감형(성능=비용↓), 성능강조형(성능↑비용=), 성능향상형(성능↑비용↑)

## 검색된 VE 대안 (상위 {len(candidates)}건)
{chr(10).join(context_parts)}

## 답변 요구사항
1. 질의에 가장 적합한 대안 2~3개를 추천하고 선정 이유를 설명하세요.
2. 각 대안의 성능/비용/가치 변화를 비교 분석하세요 (데이터 기반만).
3. 실무 적용 시 고려사항이나 위험 요인을 경고하세요.
4. 추가로 검토할 항목이 있다면 제시하세요.
5. 한국어로 작성하되, 전문적이고 간결하게 3~5 단락으로 작성하세요."""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0.3,
                top_p=0.8,
                max_output_tokens=1200,
            ),
        )
        return response.text.strip()
    except Exception as e:
        return f"⚠ Gemini API 호출 실패: {e}"



def find_similar_alternatives(alt_number: int, top_k: int = 5) -> list[dict]:
    """
    특정 대안과 가장 유사한 다른 대안들을 찾습니다.

    Args:
        alt_number: 기준 대안 번호
        top_k: 반환할 결과 수

    Returns:
        유사 대안 목록 (자기 자신 제외)
    """
    _load_index()

    # alt_number → 인덱스 찾기
    target_idx = None
    for i, m in enumerate(_metadata):
        if m["alt_number"] == alt_number:
            target_idx = i
            break

    if target_idx is None:
        return []

    # 코사인 유사도
    target_emb = _embeddings[target_idx]
    scores = _embeddings @ target_emb

    # 자기 자신 제외 Top-K
    top_indices = np.argsort(scores)[::-1]
    results = []
    for idx in top_indices:
        if idx == target_idx:
            continue
        meta = _metadata[idx].copy()
        meta["similarity"] = round(float(scores[idx]), 4)
        results.append(meta)
        if len(results) >= top_k:
            break

    return results


# ══════════════════════════════════════════
# CLI 실행: 인덱스 구축 + 테스트
# ══════════════════════════════════════════

if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 60)
    print("  VE Semantic Search — Index Builder")
    print("=" * 60)

    # 1. 인덱스 구축
    result = build_embedding_index()
    print(f"\n  Index built: {result['total']} vectors, dim={result['dim']}, time={result['build_time']}s")

    # 2. 시맨틱 검색 테스트
    test_queries = [
        "옥상 방수공사에 적용 가능한 VE 대안은?",
        "지붕 물 새는 문제 해결 방법",
        "학교 건물 외벽 에너지 효율 개선",
        "LED 조명으로 전기료 절감",
        "지하주차장 바닥 마감재 변경",
        "엘리베이터 설치 비용 절감",
    ]

    for q in test_queries:
        print(f"\n{'─' * 50}")
        print(f"  질의: '{q}'")
        results = semantic_search(q, top_k=5)
        for i, r in enumerate(results, 1):
            print(f"    {i}. [{r['alt_number']:03d}] {r['title'][:45]}  "
                  f"(sim={r['similarity']:.3f}, {r.get('how2_name','')}, {r.get('value_type','')})")

    # 3. 유사 대안 테스트
    print(f"\n{'═' * 60}")
    print(f"  Similar to #001:")
    similar = find_similar_alternatives(1, top_k=5)
    for s in similar:
        print(f"    [{s['alt_number']:03d}] {s['title'][:45]}  (sim={s['similarity']:.3f})")

    # 4. 하이브리드 검색 테스트
    print(f"\n{'═' * 60}")
    print(f"  Hybrid Search: '옥상 방수 VE 대안'")
    hybrid = hybrid_search("옥상 방수 VE 대안", top_k=5)
    print(f"  Semantic hits: {hybrid['semantic_count']}, KG hits: {hybrid['kg_match_count']}")
    for a in hybrid["alternatives"]:
        print(f"    [{a['alt_number']:03d}] {a['title'][:40]}  "
              f"(final={a['final_score']:.3f}, sem={a['semantic_score']:.3f}, kg={a['kg_score']})")
        if a["kg_paths"]:
            for p in a["kg_paths"]:
                print(f"      KG: {p}")

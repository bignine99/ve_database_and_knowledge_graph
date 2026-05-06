"""
VE Database Development - Knowledge Graph Builder v2
======================================================
CUBE 표준분류체계(WHERE/WHAT/HOW) 기반 Knowledge Graph 구축.

노드 타입 (10종):
  - Project, Alternative, Location, Space,
    WorkType(HOW1), SubWorkType(HOW2), Material,
    PerformanceCategory, ValueType

엣지 타입 (8종):
  - BELONGS_TO, LOCATED_AT, LOCATED_IN, WORK_TYPE, SUB_WORK_TYPE,
    USES_MATERIAL, CLASSIFIED_AS, REPLACES_MATERIAL
"""

import re
import sqlite3
import json
import networkx as nx
from pathlib import Path
from typing import Optional

from src.config import DB_PATH, KG_DIR, ensure_directories
from src.cube_taxonomy import (
    classify_how2, classify_space, get_how_full_code, get_how2_name,
    HOW_TAXONOMY,
)


# ── 노드 타입 색상 ──
NODE_TYPES = {
    "Project": "#FF6B6B",          # 빨강
    "Alternative": "#4ECDC4",      # 청록
    "Location": "#45B7D1",         # 하늘
    "Space": "#87CEEB",            # 연하늘 (NEW)
    "WorkType": "#96CEB4",         # 민트 (HOW1)
    "SubWorkType": "#2ECC71",      # 초록 (HOW2 - NEW)
    "Material": "#FFEAA7",         # 노랑
    "PerformanceCategory": "#DDA0DD",  # 보라
    "ValueType": "#F39C12",        # 주황
}

# ── HOW1 공사 분류 (기존 WorkType 호환) ──
HOW1_MAP = {
    "A": "건축공사", "B": "토목공사", "C": "조경공사",
    "D": "전기공사", "E": "기계설비공사", "F": "소방공사",
}

# ── 자재 추출 패턴 (정제 버전) ──
MATERIAL_PATTERNS = [
    r'(?<![가-힣])(?:THK\d+[\.\d]*(?:[가-힣]+)*)',  # THK28.5접합복층유리
    r'[가-힣]{2,}유리',           # 복층유리, 접합유리
    r'[가-힣]{2,}방수',           # 우레탄방수, 액체방수
    r'에폭시[가-힣]*',            # 에폭시라이닝
    r'콘크리트[가-힣]*',          # 콘크리트폴리싱
    r'[가-힣]{2,}몰탈',           # 시멘트몰탈
    r'LED',
    r'STS',
]

# 자재명 정제: 조사 제거
MATERIAL_SUFFIXES_TO_STRIP = ['에서', '으로', '를', '을', '의', '와', '과', '로']


def clean_material_name(name: str) -> str:
    """자재명에서 조사를 제거합니다."""
    for suffix in MATERIAL_SUFFIXES_TO_STRIP:
        if name.endswith(suffix) and len(name) > len(suffix) + 1:
            name = name[:-len(suffix)]
    return name


def extract_materials_from_text(text: str) -> set:
    """텍스트에서 자재명을 추출합니다."""
    materials = set()
    for pattern in MATERIAL_PATTERNS:
        matches = re.findall(pattern, text)
        for m in matches:
            cleaned = clean_material_name(m)
            if len(cleaned) >= 2:
                materials.add(cleaned)
    return materials


def build_knowledge_graph(
    db_path: Path = None,
    output_dir: Path = None,
) -> nx.DiGraph:
    """
    CUBE 표준분류체계 기반 Knowledge Graph를 구축합니다.

    Args:
        db_path: SQLite DB 경로
        output_dir: GraphML 출력 디렉토리

    Returns:
        NetworkX DiGraph
    """
    if db_path is None:
        db_path = DB_PATH
    if output_dir is None:
        output_dir = KG_DIR

    ensure_directories()
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    G = nx.DiGraph()

    # ── 1. 프로젝트 노드 ──
    projects = conn.execute("SELECT * FROM projects").fetchall()
    for p in projects:
        G.add_node(
            p["project_id"],
            node_type="Project",
            label=p["project_name"],
            total_alternatives=p["total_alternatives"],
            color=NODE_TYPES["Project"],
        )

    # ── 2. 대안 노드 + 관계 ──
    alternatives = conn.execute("""
        SELECT a.*, v.performance_change_rate, v.cost_change_rate,
               v.value_change_rate, v.relative_lcc,
               v.performance_original, v.performance_alternative
        FROM alternatives a
        LEFT JOIN value_evaluations v ON a.alt_id = v.alt_id
    """).fetchall()

    # 비용 데이터를 별도 조회 (cost_type별 행)
    cost_data = {}
    for row in conn.execute("""
        SELECT alt_id, cost_type, original_cost, alternative_cost, savings_amount
        FROM cost_evaluations WHERE cost_type = 'project_lifecycle'
    """).fetchall():
        cost_data[row["alt_id"]] = {
            "orig": row["original_cost"] or 0,
            "alt": row["alternative_cost"] or 0,
            "savings": row["savings_amount"] or 0,
        }

    locations_seen = set()
    spaces_seen = set()
    how1_seen = set()
    how2_seen = set()
    materials_seen = set()
    value_types_seen = set()
    perf_categories_seen = set()

    for alt in alternatives:
        alt_id = alt["alt_id"]
        alt_num = alt["alt_number"]
        proposal_title = alt["proposal_title"] or ""
        orig_desc = alt["original_description"] or ""
        alt_desc = alt["alternative_description"] or ""
        full_text = f"{proposal_title} {orig_desc} {alt_desc}"

        # 비용 절감액
        cost_info = cost_data.get(alt_id, {})
        savings = cost_info.get("savings", 0.0)

        # ── 대안 노드 ──
        G.add_node(
            alt_id,
            node_type="Alternative",
            label=f"대안-{alt_num:02d}",
            alt_number=alt_num,
            proposal_title=proposal_title,
            color=NODE_TYPES["Alternative"],
            performance_change=alt["performance_change_rate"] or 0.0,
            cost_change=alt["cost_change_rate"] or 0.0,
            value_change=alt["value_change_rate"] or 0.0,
            savings_million=savings,
        )

        # ── BELONGS_TO → Project ──
        G.add_edge(alt_id, alt["project_id"], edge_type="BELONGS_TO")

        # ── LOCATED_AT → Location (건물/동 수준) ──
        location = alt["location"]
        if location and location.strip():
            loc_id = f"loc_{location}"
            if location not in locations_seen:
                G.add_node(loc_id, node_type="Location", label=location,
                          color=NODE_TYPES["Location"])
                locations_seen.add(location)
            G.add_edge(alt_id, loc_id, edge_type="LOCATED_AT")

        # ── LOCATED_IN → Space (공간/실 수준) — NEW ──
        space_field = alt["space"] if "space" in alt.keys() else ""
        if space_field:
            for sp in space_field.split(","):
                sp = sp.strip()
                if sp and sp != "전체":
                    sp_id = f"space_{sp}"
                    if sp not in spaces_seen:
                        G.add_node(sp_id, node_type="Space", label=sp,
                                  color=NODE_TYPES["Space"])
                        spaces_seen.add(sp)
                    G.add_edge(alt_id, sp_id, edge_type="LOCATED_IN")

        # ── WORK_TYPE → WorkType (HOW1) ──
        how2_code = alt["how2_code"] if "how2_code" in alt.keys() else ""
        if how2_code:
            how1_code = how2_code.split("-")[0]
            how1_name = HOW1_MAP.get(how1_code, "기타")
            how1_id = f"how1_{how1_code}"
            if how1_code not in how1_seen:
                G.add_node(how1_id, node_type="WorkType", label=how1_name,
                          how1_code=how1_code, color=NODE_TYPES["WorkType"])
                how1_seen.add(how1_code)
            G.add_edge(alt_id, how1_id, edge_type="WORK_TYPE")

            # ── SUB_WORK_TYPE → SubWorkType (HOW2) — NEW ──
            how2_name = alt["how2_name"] if "how2_name" in alt.keys() else ""
            how2_id = f"how2_{how2_code}"
            if how2_code not in how2_seen:
                G.add_node(how2_id, node_type="SubWorkType", label=how2_name,
                          how2_code=how2_code, how1_code=how1_code,
                          color=NODE_TYPES["SubWorkType"])
                how2_seen.add(how2_code)
                # HOW2 → HOW1 계층 관계
                G.add_edge(how2_id, how1_id, edge_type="BELONGS_TO")
            G.add_edge(alt_id, how2_id, edge_type="SUB_WORK_TYPE")

        # ── USES_MATERIAL → Material (정제 버전) ──
        orig_materials = extract_materials_from_text(orig_desc)
        alt_materials = extract_materials_from_text(alt_desc)
        all_materials = orig_materials | alt_materials

        for material in all_materials:
            mat_id = f"mat_{material}"
            if material not in materials_seen:
                G.add_node(mat_id, node_type="Material", label=material,
                          color=NODE_TYPES["Material"])
                materials_seen.add(material)
            is_original = material in orig_materials
            is_alternative = material in alt_materials
            G.add_edge(alt_id, mat_id, edge_type="USES_MATERIAL",
                      source="original" if is_original and not is_alternative else
                             "alternative" if is_alternative and not is_original else "both")

        # ── REPLACES_MATERIAL 엣지 — NEW ──
        # 원안에만 있는 자재 → 대안에만 있는 자재 = 교체 관계
        orig_only = orig_materials - alt_materials
        alt_only = alt_materials - orig_materials
        if orig_only and alt_only:
            for om in orig_only:
                for am in alt_only:
                    om_id = f"mat_{om}"
                    am_id = f"mat_{am}"
                    G.add_edge(om_id, am_id, edge_type="REPLACES_MATERIAL",
                              alt_id=alt_id, alt_number=alt_num)

        # ── CLASSIFIED_AS → ValueType (수정된 버전) ──
        try:
            vtype = alt["value_type_corrected"]
        except (IndexError, KeyError):
            vtype = ""
        if not vtype:
            vtype = alt["value_type"] or ""
        if vtype and vtype.strip() and vtype != "0 0.00" and vtype != "미분류":
            vtype_id = f"vtype_{vtype}"
            if vtype not in value_types_seen:
                G.add_node(vtype_id, node_type="ValueType", label=vtype,
                          color=NODE_TYPES["ValueType"])
                value_types_seen.add(vtype)
            G.add_edge(alt_id, vtype_id, edge_type="CLASSIFIED_AS")

    # ── 3. 성능 카테고리 노드 ──
    categories = conn.execute("""
        SELECT DISTINCT category FROM performance_scores
        WHERE category != '' AND category != '대분류'
    """).fetchall()
    for cat in categories:
        cat_name = cat["category"]
        cat_id = f"perf_{cat_name}"
        G.add_node(cat_id, node_type="PerformanceCategory", label=cat_name,
                  color=NODE_TYPES["PerformanceCategory"])
        perf_categories_seen.add(cat_name)

    # EVALUATED_BY 엣지
    perf_changes = conn.execute("""
        SELECT alt_id, category, SUM(score_delta) as total_delta
        FROM performance_scores
        WHERE score_delta IS NOT NULL AND score_delta != 0
        GROUP BY alt_id, category
    """).fetchall()
    for pc in perf_changes:
        cat_id = f"perf_{pc['category']}"
        if pc["category"] in perf_categories_seen:
            G.add_edge(pc["alt_id"], cat_id,
                      edge_type="EVALUATED_BY",
                      delta=pc["total_delta"] or 0.0)

    conn.close()

    # ── 4. GraphML 저장 ──
    graphml_path = output_dir / "ve_knowledge_graph.graphml"
    nx.write_graphml(G, str(graphml_path))

    # ── 5. JSON 메타데이터 저장 ──
    stats = get_graph_stats(G)
    stats_path = output_dir / "kg_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    return G


def get_graph_stats(G: nx.DiGraph) -> dict:
    """Knowledge Graph 통계를 반환합니다."""
    # 노드 타입별 카운트
    node_types = {}
    for node, data in G.nodes(data=True):
        ntype = data.get("node_type", "Unknown")
        node_types[ntype] = node_types.get(ntype, 0) + 1

    # 엣지 타입별 카운트
    edge_types = {}
    for u, v, data in G.edges(data=True):
        etype = data.get("edge_type", "Unknown")
        edge_types[etype] = edge_types.get(etype, 0) + 1

    # 중심성 분석 (degree centrality)
    degree_centrality = nx.degree_centrality(G)
    top_nodes = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "node_types": node_types,
        "edge_types": edge_types,
        "components": nx.number_weakly_connected_components(G),
        "density": round(nx.density(G), 6),
        "top_10_central_nodes": [
            {"node": n, "label": G.nodes[n].get("label", n),
             "type": G.nodes[n].get("node_type", ""), "centrality": round(c, 4)}
            for n, c in top_nodes
        ],
    }


def query_kg_hop(G: nx.DiGraph, query_text: str, max_hops: int = 2) -> dict:
    """
    자연어 질의에서 KG hop 탐색을 수행합니다.
    예: "옥상 방수공사에 적용 가능한 VE item은?"

    Args:
        G: Knowledge Graph
        query_text: 질의 텍스트
        max_hops: 최대 hop 수

    Returns:
        매칭된 대안 목록 및 경로 정보
    """
    # 질의에서 Space/HOW2 키워드 추출
    query_spaces = classify_space(query_text)
    query_how2 = classify_how2(query_text)

    matched_alternatives = []

    for node, data in G.nodes(data=True):
        if data.get("node_type") != "Alternative":
            continue

        score = 0
        paths = []

        # Space 매칭
        for neighbor in G.successors(node):
            nd = G.nodes[neighbor]
            if nd.get("node_type") == "Space" and nd.get("label") in query_spaces:
                score += 2
                paths.append(f"{data['label']} →[LOCATED_IN]→ {nd['label']}")

        # HOW2 매칭
        for neighbor in G.successors(node):
            nd = G.nodes[neighbor]
            if nd.get("node_type") == "SubWorkType":
                for _, h2, h2name in query_how2:
                    if nd.get("how2_code") == f"{_}-{h2}" or nd.get("label") == h2name:
                        score += 2
                        paths.append(f"{data['label']} →[SUB_WORK_TYPE]→ {nd['label']}")

        if score > 0:
            # 관련 자재 수집
            materials = []
            for neighbor in G.successors(node):
                nd = G.nodes[neighbor]
                if nd.get("node_type") == "Material":
                    edge_data = G.edges[node, neighbor]
                    materials.append({
                        "name": nd["label"],
                        "source": edge_data.get("source", ""),
                    })

            # 가치유형 수집
            value_type = ""
            for neighbor in G.successors(node):
                nd = G.nodes[neighbor]
                if nd.get("node_type") == "ValueType":
                    value_type = nd["label"]

            matched_alternatives.append({
                "alt_id": node,
                "label": data["label"],
                "title": data.get("proposal_title", ""),
                "score": score,
                "paths": paths,
                "materials": materials,
                "value_type": value_type,
                "savings": data.get("savings_million", 0),
                "value_change": data.get("value_change", 0),
            })

    # 점수순 정렬
    matched_alternatives.sort(key=lambda x: -x["score"])
    return {
        "query": query_text,
        "query_spaces": query_spaces,
        "query_how2": [(get_how_full_code(h1, h2), n) for h1, h2, n in query_how2],
        "matched_count": len(matched_alternatives),
        "alternatives": matched_alternatives,
    }


if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("Building Knowledge Graph v2 (CUBE 표준분류체계)...")
    G = build_knowledge_graph()

    stats = get_graph_stats(G)
    print(f"\n=== Knowledge Graph v2 Statistics ===")
    print(f"  Total Nodes: {stats['total_nodes']}")
    print(f"  Total Edges: {stats['total_edges']}")
    print(f"  Components: {stats['components']}")

    print(f"\n  Node Types:")
    for ntype, count in sorted(stats['node_types'].items()):
        print(f"    {ntype}: {count}")

    print(f"\n  Edge Types:")
    for etype, count in sorted(stats['edge_types'].items()):
        print(f"    {etype}: {count}")

    # ── 핵심 검증: "옥상 방수 VE item" 질의 ──
    print(f"\n{'='*60}")
    print(f"  QUERY TEST: '옥상 방수공사에 적용 가능한 VE item은?'")
    print(f"{'='*60}")
    result = query_kg_hop(G, "옥상 방수공사에 적용 가능한 VE item은?")
    print(f"  Matched: {result['matched_count']}개 대안")
    print(f"  Query Spaces: {result['query_spaces']}")
    print(f"  Query HOW2: {result['query_how2']}")
    for alt in result['alternatives']:
        print(f"\n  [{alt['label']}] {alt['title'][:50]}")
        print(f"    Score: {alt['score']} | Value: {alt['value_type']} | Savings: {alt['savings']}백만원")
        for p in alt['paths']:
            print(f"      {p}")
        if alt['materials']:
            mat_names = [m['name'] for m in alt['materials']]
            print(f"      Materials: {', '.join(mat_names)}")

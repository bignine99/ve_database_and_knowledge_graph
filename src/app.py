"""
VE Database Development - Flask Dashboard Application
=======================================================
Construction VE 종합 대시보드 — CUBE 표준분류체계 기반.
DB: Supabase PostgreSQL (Session Pooler)
"""

import sys
import io
import json
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from flask import Flask, render_template, jsonify, request, send_from_directory
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

# ── 경로 설정 ──
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# sys.path에 프로젝트 루트 추가 — 'from src.xxx' import 지원
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

KG_DIR = BASE_DIR / "data" / "kg"
EXTRACTED_DIR = BASE_DIR / "data" / "extracted"
IMAGES_DIR = BASE_DIR / "data" / "images"

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "src" / "templates"),
    static_folder=str(BASE_DIR / "src" / "static"),
)
app.config["JSON_AS_ASCII"] = False

# Decimal → float JSON 변환
from decimal import Decimal as _Decimal
import json as _json

class DecimalEncoder(_json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, _Decimal):
            return float(obj)
        return super().default(obj)

from flask.json.provider import DefaultJSONProvider
class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, _Decimal):
            return float(obj)
        return super().default(obj)

app.json_provider_class = CustomJSONProvider
app.json = CustomJSONProvider(app)

def get_db():
    """Supabase PostgreSQL 연결 (RealDictCursor)."""
    conn = psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        port=int(os.getenv("SUPABASE_DB_PORT", 5432)),
        dbname=os.getenv("SUPABASE_DB_NAME", "postgres"),
        user=os.getenv("SUPABASE_DB_USER", "postgres"),
        password=os.getenv("SUPABASE_DB_PASS"),
        sslmode="require",
    )
    return conn


def query(conn, sql, params=None):
    """Execute query and return list of dicts."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return rows


def query_one(conn, sql, params=None):
    """Execute query and return single dict."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params)
    row = cur.fetchone()
    cur.close()
    return row


# ══════════════════════════════════════════
# 페이지 라우트
# ══════════════════════════════════════════

@app.route("/")
def landing():
    """히어로 랜딩 페이지."""
    return render_template("landing.html")


@app.route("/dashboard")
def index():
    """01. OVERVIEW 페이지."""
    return render_template("index.html")


@app.route("/alternatives")
def alternatives_page():
    """02. ALTERNATIVES 페이지."""
    return render_template("index.html")


@app.route("/cost")
def cost_page():
    """03. COST ANALYSIS 페이지."""
    return render_template("index.html")


@app.route("/kg")
def kg_page():
    """04. KNOWLEDGE GRAPH 페이지."""
    return render_template("index.html")


@app.route("/ai")
def ai_page():
    """05. AI VE 자문 페이지."""
    return render_template("index.html")


# ══════════════════════════════════════════
# REST API
# ══════════════════════════════════════════

@app.route("/api/stats")
def api_stats():
    """전체 통계 KPI."""
    conn = get_db()

    total = query_one(conn, "SELECT COUNT(*) as cnt FROM alternatives")["cnt"]

    # HOW2 분포
    how2_dist = query(conn, """
        SELECT how2_code, how2_name, COUNT(*) as cnt
        FROM alternatives WHERE how2_code != ''
        GROUP BY how2_code, how2_name ORDER BY cnt DESC
    """)

    # ValueType 분포
    vtype_dist = query(conn, """
        SELECT value_type_corrected as vtype, COUNT(*) as cnt
        FROM alternatives WHERE value_type_corrected != ''
        GROUP BY value_type_corrected ORDER BY cnt DESC
    """)

    # HOW1 분포
    how1_dist = {}
    for row in how2_dist:
        code = row["how2_code"].split("-")[0] if row["how2_code"] else ""
        how1_names = {"A": "건축공사", "B": "토목공사", "C": "조경공사",
                      "D": "전기공사", "E": "기계설비공사", "F": "소방공사"}
        name = how1_names.get(code, "기타")
        how1_dist[name] = how1_dist.get(name, 0) + row["cnt"]

    # 비용 절감 통계
    cost_stats = query_one(conn, """
        SELECT
            SUM(original_cost - alternative_cost) as total_savings,
            AVG(savings_rate) as avg_savings_rate,
            COUNT(*) as cost_count
        FROM cost_evaluations
        WHERE cost_type = 'project_lifecycle'
    """)

    # KG 통계
    kg_stats = {}
    kg_stats_path = KG_DIR / "kg_stats.json"
    if kg_stats_path.exists():
        kg_stats = json.loads(kg_stats_path.read_text(encoding='utf-8'))

    # AI 서술 커버리지
    ai_count = 0
    for jp in EXTRACTED_DIR.glob("alt_*.json"):
        d = json.loads(jp.read_text(encoding='utf-8'))
        if d.get("ai_descriptions"):
            ai_count += 1

    conn.close()

    return jsonify({
        "total_alternatives": total,
        "avg_savings_rate": round(cost_stats["avg_savings_rate"] or 0, 2),
        "total_savings": round(cost_stats["total_savings"] or 0, 2),
        "ai_coverage": round(ai_count / total * 100, 1) if total > 0 else 0,
        "value_innovation_rate": round(
            sum(r["cnt"] for r in vtype_dist if r["vtype"] == "가치혁신형") / total * 100, 1
        ) if total > 0 else 0,
        "how1_distribution": how1_dist,
        "how2_distribution": [
            {"code": r["how2_code"], "name": r["how2_name"], "count": r["cnt"]}
            for r in how2_dist
        ],
        "vtype_distribution": [
            {"type": r["vtype"], "count": r["cnt"]}
            for r in vtype_dist
        ],
        "kg_nodes": kg_stats.get("total_nodes", 0),
        "kg_edges": kg_stats.get("total_edges", 0),
    })


@app.route("/api/alternatives")
def api_alternatives():
    """대안 목록 (필터/검색 지원)."""
    conn = get_db()

    search = request.args.get("q", "").strip()
    how1 = request.args.get("how1", "").strip()
    how2 = request.args.get("how2", "").strip()
    vtype = request.args.get("vtype", "").strip()

    q = """
        SELECT a.alt_number, a.proposal_title, a.location, a.how2_code, a.how2_name,
               a.space, a.value_type_corrected as value_type,
               COALESCE(a.field_category, '') as field_category,
               COALESCE(a.project_name, '') as project_name,
               v.performance_change_rate, v.cost_change_rate, v.value_change_rate,
               (c.original_cost - c.alternative_cost) as savings_calc, c.savings_rate
        FROM alternatives a
        LEFT JOIN value_evaluations v ON a.alt_id = v.alt_id
        LEFT JOIN cost_evaluations c ON a.alt_id = c.alt_id AND c.cost_type = 'project_lifecycle'
        WHERE 1=1
    """
    params = []

    if search:
        q += " AND (a.proposal_title LIKE %s OR a.how2_name LIKE %s)"
        params.extend([f"%{search}%", f"%{search}%"])
    if how1:
        q += " AND a.how2_code LIKE %s"
        params.append(f"{how1}-%")
    if how2:
        q += " AND a.how2_code = %s"
        params.append(how2)
    if vtype:
        q += " AND a.value_type_corrected = %s"
        params.append(vtype)

    q += " ORDER BY a.alt_number"

    rows = query(conn, q, params)
    conn.close()

    return jsonify([{
        "alt_number": r["alt_number"],
        "title": r["proposal_title"],
        "location": r["location"] or "",
        "how2_code": r["how2_code"] or "",
        "how2_name": r["how2_name"] or "",
        "space": r["space"] or "",
        "value_type": r["value_type"] or "",
        "field": r["field_category"] or "",
        "pname": r["project_name"] or "",
        "perf_change": round(r["performance_change_rate"] or 0, 2),
        "cost_change": round(r["cost_change_rate"] or 0, 2),
        "value_change": round(r["value_change_rate"] or 0, 2),
        "savings": round((r["savings_calc"] or 0) / 10000, 2),
        "savings_rate": round(r["savings_rate"] or 0, 2),
    } for r in rows])


@app.route("/api/alternatives/<int:alt_num>")
def api_alternative_detail(alt_num):
    """대안 상세 정보."""
    conn = get_db()

    alt = query_one(conn, """
        SELECT a.*, v.performance_change_rate, v.cost_change_rate,
               v.value_change_rate, v.relative_lcc,
               v.performance_original, v.performance_alternative
        FROM alternatives a
        LEFT JOIN value_evaluations v ON a.alt_id = v.alt_id
        WHERE a.alt_number = %s
    """, (alt_num,))

    if not alt:
        conn.close()
        return jsonify({"error": "Not found"}), 404

    # 비용 데이터
    costs = query(conn, """
        SELECT cost_type, original_cost, alternative_cost, savings_amount, savings_rate
        FROM cost_evaluations WHERE alt_id = %s
    """, (alt["alt_id"],))

    # 성능 데이터
    perfs = query(conn, """
        SELECT category, subcategory, original_score, alternative_score, score_delta
        FROM performance_scores WHERE alt_id = %s
    """, (alt["alt_id"],))

    # 이미지 데이터
    images = query(conn, """
        SELECT image_type, file_path, ai_description FROM images WHERE alt_id = %s
    """, (alt["alt_id"],))

    conn.close()

    # AI 서술 데이터 (JSON에서)
    ai_descs = []
    json_path = EXTRACTED_DIR / f"alt_{alt_num:03d}.json"
    if json_path.exists():
        jdata = json.loads(json_path.read_text(encoding='utf-8'))
        ai_descs = jdata.get("ai_descriptions", [])

    return jsonify({
        "alt_number": alt["alt_number"],
        "title": alt["proposal_title"],
        "location": alt.get("location") or "",
        "how2_code": alt.get("how2_code") or "",
        "how2_name": alt.get("how2_name") or "",
        "space": alt.get("space") or "",
        "value_type": alt.get("value_type_corrected") or "",
        "original_desc": alt.get("original_description") or "",
        "alternative_desc": alt.get("alternative_description") or "",
        "analysis_summary": alt.get("analysis_summary") or "",
        "perf_change": round(alt.get("performance_change_rate") or 0, 2),
        "cost_change": round(alt.get("cost_change_rate") or 0, 2),
        "value_change": round(alt.get("value_change_rate") or 0, 2),
        "costs": [{"type": c["cost_type"],
                   "original": c["original_cost"],
                   "alternative": c["alternative_cost"],
                   "savings": c["savings_amount"],
                   "rate": c["savings_rate"]} for c in costs],
        "performances": [{"category": p["category"],
                          "subcategory": p["subcategory"],
                          "original": p["original_score"],
                          "alternative": p["alternative_score"],
                          "delta": p["score_delta"]} for p in perfs],
        "images": [{"type": i["image_type"], "path": i["file_path"],
                    "ai_desc": i["ai_description"] or ""} for i in images],
        "ai_descriptions": ai_descs,
    })


@app.route("/api/kg/data")
def api_kg_data():
    """KG 데이터를 vis-network용 JSON으로 반환."""
    kg_stats_path = KG_DIR / "kg_stats.json"
    if not kg_stats_path.exists():
        return jsonify({"nodes": [], "edges": []})

    import networkx as nx
    graphml_path = KG_DIR / "ve_knowledge_graph.graphml"
    G = nx.read_graphml(str(graphml_path))

    nodes = []
    for n, d in G.nodes(data=True):
        nodes.append({
            "id": n,
            "label": d.get("label", n)[:30],
            "group": d.get("node_type", "Unknown"),
            "title": f"{d.get('node_type','')}: {d.get('label',n)}",
            "color": d.get("color", "#ccc"),
        })

    edges = []
    for u, v, d in G.edges(data=True):
        edges.append({
            "from": u,
            "to": v,
            "label": d.get("edge_type", ""),
            "arrows": "to",
        })

    return jsonify({"nodes": nodes, "edges": edges})


@app.route("/api/kg/query")
def api_kg_query():
    """KG hop 질의."""
    query_text = request.args.get("q", "").strip()
    if not query_text:
        return jsonify({"error": "Query required"}), 400

    import networkx as nx
    from src.kg_builder import query_kg_hop

    graphml_path = KG_DIR / "ve_knowledge_graph.graphml"
    G = nx.read_graphml(str(graphml_path))

    # GraphML에서 읽으면 속성이 문자열 — node_type 등 복원
    result = query_kg_hop(G, query_text)
    return jsonify(result)


@app.route("/api/search")
def api_semantic_search():
    """시맨틱 검색 API — Embedding 기반 의미 검색."""
    query_text = request.args.get("q", "").strip()
    if not query_text:
        return jsonify({"error": "Query required"}), 400

    top_k = request.args.get("top_k", 10, type=int)

    try:
        from src.semantic_search import semantic_search
        results = semantic_search(query_text, top_k=top_k)
        return jsonify({
            "query": query_text,
            "count": len(results),
            "alternatives": results,
        })
    except FileNotFoundError:
        return jsonify({"error": "임베딩 인덱스가 아직 생성되지 않았습니다."}), 503
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/ai/search")
def api_hybrid_search():
    """하이브리드 RAG 검색 API — Embedding + KG + Gemini."""
    query_text = request.args.get("q", "").strip()
    if not query_text:
        return jsonify({"error": "Query required"}), 400

    top_k = request.args.get("top_k", 10, type=int)
    use_gemini = request.args.get("gemini", "false").lower() == "true"

    try:
        from src.semantic_search import hybrid_search
        result = hybrid_search(query_text, top_k=top_k, use_gemini=use_gemini)
        return jsonify(result)
    except FileNotFoundError:
        return jsonify({"error": "임베딩 인덱스가 아직 생성되지 않았습니다."}), 503
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/alternatives/<int:alt_num>/similar")
def api_similar_alternatives(alt_num):
    """유사 대안 검색 API — 특정 대안과 가장 유사한 대안들."""
    top_k = request.args.get("top_k", 5, type=int)

    try:
        from src.semantic_search import find_similar_alternatives
        results = find_similar_alternatives(alt_num, top_k=top_k)
        return jsonify({
            "base_alt_number": alt_num,
            "count": len(results),
            "similar": results,
        })
    except FileNotFoundError:
        return jsonify({"error": "임베딩 인덱스가 아직 생성되지 않았습니다."}), 503
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/classify", methods=["POST"])
def api_classify():
    """자동 분류 API — 텍스트에서 HOW2 대공종 + ValueType 예측."""
    data = request.get_json()
    text = (data or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "text required"}), 400

    try:
        from src.ml_classifier import classify_alternative
        result = classify_alternative(text)
        return jsonify(result)
    except FileNotFoundError:
        return jsonify({"error": "분류기가 아직 학습되지 않았습니다."}), 503
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/clusters")
def api_clusters():
    """클러스터 목록 API — 전체 클러스터 요약 정보."""
    try:
        cluster_path = BASE_DIR / "data" / "ml_models" / "cluster_result.json"
        if not cluster_path.exists():
            return jsonify({"error": "클러스터링 결과가 없습니다."}), 503

        with open(cluster_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 멤버 목록은 제외하고 요약만 반환
        summary = {
            "n_clusters": data["n_clusters"],
            "silhouette_score": data["silhouette_score"],
            "total_alternatives": data["total_alternatives"],
            "clusters": [{
                "cluster_id": c["cluster_id"],
                "label": c["label"],
                "size": c["size"],
                "representative": c["representative"],
                "how2_distribution": c["how2_distribution"],
                "vtype_distribution": c["vtype_distribution"],
                "avg_savings_rate": c["avg_savings_rate"],
                "avg_value_change": c["avg_value_change"],
                "avg_perf_change": c["avg_perf_change"],
                "avg_cost_change": c["avg_cost_change"],
            } for c in data["clusters"]],
        }
        return jsonify(summary)
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/clusters/<int:cluster_id>")
def api_cluster_detail(cluster_id):
    """클러스터 상세 API — 특정 클러스터의 멤버 목록 포함."""
    try:
        cluster_path = BASE_DIR / "data" / "ml_models" / "cluster_result.json"
        if not cluster_path.exists():
            return jsonify({"error": "클러스터링 결과가 없습니다."}), 503

        with open(cluster_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cluster = next((c for c in data["clusters"] if c["cluster_id"] == cluster_id), None)
        if not cluster:
            return jsonify({"error": "Cluster not found"}), 404
        return jsonify(cluster)
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/images/<path:filename>")
def serve_image(filename):
    """이미지 파일 서빙 (절대 경로 지원)."""
    # DB에 절대경로가 저장되어 있으므로 직접 서빙
    file_path = Path(filename)
    if file_path.exists():
        return send_from_directory(str(file_path.parent), file_path.name)
    # 상대경로 시도
    rel_path = IMAGES_DIR / filename
    if rel_path.exists():
        return send_from_directory(str(rel_path.parent), rel_path.name)
    return "Not found", 404


@app.route("/api/serve_abs_image")
def serve_abs_image():
    """절대 경로 이미지 서빙 — Windows 개발 경로를 서버 경로로 자동 매핑."""
    fpath = request.args.get("path", "")
    p = Path(fpath)

    # DB에 저장된 Windows 절대 경로를 Linux 서버 경로로 매핑
    if not p.exists() and ('\\' in fpath or 'C:' in fpath):
        # Windows 경로에서 'data/images/' 이후 부분 추출
        normalized = fpath.replace('\\', '/')
        marker = 'data/images/'
        idx = normalized.find(marker)
        if idx >= 0:
            relative = normalized[idx:]  # e.g. "data/images/대안_02/대안_02_original_diagram.jpeg"
            server_path = Path('/home/ubuntu/ve_database') / relative
            if server_path.exists():
                return send_from_directory(str(server_path.parent), server_path.name)

    if p.exists():
        return send_from_directory(str(p.parent), p.name)
    return "Not found", 404


@app.route("/api/stats/extended")
def api_stats_extended():
    """확장 통계 — 추가 차트용 데이터."""
    import traceback, sys
    try:
        return _stats_extended_impl()
    except Exception as e:
        tb = traceback.format_exc()
        print(f"EXTENDED API ERROR: {tb}", flush=True)
        return jsonify({"error": str(e), "traceback": tb}), 500

def _stats_extended_impl():
    conn = get_db()

    # 프로젝트별 대안 수
    proj_dist = query(conn, """
        SELECT p.project_name, COUNT(a.alt_id) as cnt
        FROM projects p LEFT JOIN alternatives a ON p.project_id = a.project_id
        GROUP BY p.project_name ORDER BY cnt DESC
    """)

    # 분야별 분포
    field_dist = query(conn, """
        SELECT COALESCE(NULLIF(field_category,''), '미분류') as field, COUNT(*) as cnt
        FROM alternatives GROUP BY field ORDER BY cnt DESC
    """)

    # 공간별 분포 Top 12
    space_dist = query(conn, """
        SELECT space, COUNT(*) as cnt FROM alternatives
        WHERE space != '' AND space IS NOT NULL
        GROUP BY space ORDER BY cnt DESC LIMIT 12
    """)

    # 가치 향상 Top 10
    value_top = query(conn, """
        SELECT a.alt_number, a.proposal_title, v.value_change_rate, v.performance_change_rate, v.cost_change_rate
        FROM alternatives a JOIN value_evaluations v ON a.alt_id = v.alt_id
        WHERE v.value_change_rate IS NOT NULL
        ORDER BY v.value_change_rate DESC LIMIT 10
    """)

    # HOW2별 평균 절감률
    how2_savings = query(conn, """
        SELECT a.how2_name, ROUND(AVG(c.savings_rate)::numeric, 2) as avg_rate, COUNT(*) as cnt
        FROM alternatives a JOIN cost_evaluations c ON a.alt_id = c.alt_id
        WHERE c.cost_type = 'project_lifecycle' AND a.how2_name != ''
        GROUP BY a.how2_name HAVING COUNT(*) >= 2
        ORDER BY avg_rate DESC LIMIT 12
    """)

    # 절감률 분포 (히스토그램 구간)
    savings_hist = query(conn, """
        SELECT
            CASE
                WHEN savings_rate <= 0 THEN '0% 이하'
                WHEN savings_rate <= 1 THEN '0~1%'
                WHEN savings_rate <= 5 THEN '1~5%'
                WHEN savings_rate <= 10 THEN '5~10%'
                WHEN savings_rate <= 20 THEN '10~20%'
                WHEN savings_rate <= 50 THEN '20~50%'
                ELSE '50%+'
            END as bucket,
            COUNT(*) as cnt
        FROM cost_evaluations WHERE cost_type = 'project_lifecycle'
        GROUP BY bucket ORDER BY MIN(savings_rate)
    """)

    # 성능평가 5대 카테고리 평균
    perf_categories = query(conn, """
        SELECT category,
            ROUND(AVG(original_score)::numeric, 1) as avg_original,
            ROUND(AVG(alternative_score)::numeric, 1) as avg_alternative,
            ROUND(AVG(alternative_score - original_score)::numeric, 2) as avg_delta,
            COUNT(*) as cnt
        FROM performance_scores
        WHERE category != '대분류'
        GROUP BY category ORDER BY cnt DESC
    """)

    # 성능-비용 4사분면 데이터
    quadrant = query(conn, """
        SELECT a.alt_number, a.proposal_title,
            v.performance_change_rate as perf, v.cost_change_rate as cost,
            a.value_type_corrected as vtype
        FROM alternatives a JOIN value_evaluations v ON a.alt_id = v.alt_id
        WHERE v.performance_change_rate IS NOT NULL AND v.cost_change_rate IS NOT NULL
    """)

    # HOW1 × 가치유형 히트맵
    heatmap = query(conn, """
        SELECT
            CASE SPLIT_PART(how2_code, '-', 1)
                WHEN 'A' THEN '건축' WHEN 'B' THEN '토목' WHEN 'C' THEN '조경'
                WHEN 'D' THEN '전기' WHEN 'E' THEN '기계설비' WHEN 'F' THEN '소방'
                ELSE '기타'
            END as how1,
            value_type_corrected as vtype, COUNT(*) as cnt
        FROM alternatives WHERE how2_code != '' AND value_type_corrected != ''
        GROUP BY how1, vtype
    """)

    conn.close()
    return jsonify({
        "project_distribution": [{"name": (r["project_name"] or "미분류")[:25], "count": r["cnt"]} for r in proj_dist],
        "field_distribution": [{"field": r["field"] or "미분류", "count": r["cnt"]} for r in field_dist],
        "space_distribution": [{"space": r["space"] or "", "count": r["cnt"]} for r in space_dist],
        "value_top10": [{"num": r["alt_number"], "title": (r["proposal_title"] or "")[:30],
                         "value": float(r["value_change_rate"] or 0),
                         "perf": float(r["performance_change_rate"] or 0),
                         "cost": float(r["cost_change_rate"] or 0)} for r in value_top],
        "how2_avg_savings": [{"name": (r["how2_name"] or "기타")[:12], "rate": float(r["avg_rate"] or 0), "cnt": r["cnt"]} for r in how2_savings],
        "savings_histogram": [{"range": r["bucket"] or "", "count": r["cnt"]} for r in savings_hist],
        "perf_categories": [{"category": r["category"] or "", "original": float(r["avg_original"] or 0),
                             "alternative": float(r["avg_alternative"] or 0), "delta": float(r["avg_delta"] or 0),
                             "count": r["cnt"]} for r in perf_categories],
        "quadrant_data": [{"num": r["alt_number"], "title": (r["proposal_title"] or "")[:25],
                           "perf": float(r["perf"] or 0), "cost": float(r["cost"] or 0),
                           "vtype": r["vtype"] or ""} for r in quadrant],
        "heatmap": [{"how1": r["how1"] or "기타", "vtype": r["vtype"] or "기타", "count": r["cnt"]} for r in heatmap],
    })


@app.route("/performance")
def performance_page():
    """06. 성능 분석 페이지."""
    return render_template("index.html")


# ═══════════════════════════════════════════════════════════
#  Task 37: VE Multi-Agent API
# ═══════════════════════════════════════════════════════════

# VE Leader 인스턴스 (애플리케이션 수명 동안 유지)
_ve_leader = None

def _get_ve_leader():
    global _ve_leader
    if _ve_leader is None:
        from src.agents.ve_leader import VELeader
        _ve_leader = VELeader()
    return _ve_leader


@app.route("/api/ve/session", methods=["POST"])
def ve_create_session():
    """새 VE 세션 생성 및 분석 실행."""
    import threading
    from src.agents.schemas import ProjectBrief, DesignAnalysis, DesignElement, CostBreakdown, CostItem
    from dataclasses import asdict

    data = request.get_json(silent=True) or {}
    brief_data = data.get("project_brief", data)

    brief = ProjectBrief(
        project_name=brief_data.get("project_name", "미지정 프로젝트"),
        project_type=brief_data.get("project_type", ""),
        total_area=float(brief_data.get("total_area", 0)),
        total_cost=float(brief_data.get("total_cost", 0)),
        ve_target_rate=float(brief_data.get("ve_target_rate", 5.0)),
        focus_disciplines=brief_data.get("focus_disciplines", []),
        constraints=brief_data.get("constraints", []),
        description=brief_data.get("description", ""),
    )

    errors = brief.validate()
    if errors:
        return jsonify({"error": errors}), 400

    # 도면/내역 AI 데이터 (선택)
    design = None
    if "design_analysis" in data and data["design_analysis"]:
        d = data["design_analysis"]
        design = DesignAnalysis(
            elements=[DesignElement(**e) for e in d.get("elements", [])]
        )

    cost = None
    if "cost_breakdown" in data and data["cost_breakdown"]:
        c = data["cost_breakdown"]
        cost = CostBreakdown(
            items=[CostItem(**i) for i in c.get("items", [])]
        )

    leader = _get_ve_leader()

    # 동기 실행 (50초 이내 완료)
    try:
        session = leader.run_session(brief, design, cost)
        return jsonify({
            "session_id": session.session_id,
            "status": session.status,
            "progress": session.progress,
            "ideas_count": len(session.ideas),
            "reviews_count": len(session.domain_reviews),
            "report_length": len(session.report_markdown),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ve/session/<session_id>/status")
def ve_session_status(session_id):
    """VE 세션 진행 상태 조회."""
    leader = _get_ve_leader()
    session = leader.sessions.get(session_id)
    if not session:
        return jsonify({"error": "세션을 찾을 수 없습니다."}), 404
    return jsonify({
        "session_id": session.session_id,
        "status": session.status,
        "current_step": session.current_step,
        "total_steps": session.total_steps,
        "progress": session.progress,
    })


@app.route("/api/ve/session/<session_id>/result")
def ve_session_result(session_id):
    """VE 세션 최종 결과 조회."""
    from dataclasses import asdict
    leader = _get_ve_leader()
    session = leader.sessions.get(session_id)
    if not session:
        return jsonify({"error": "세션을 찾을 수 없습니다."}), 404

    return jsonify({
        "session_id": session.session_id,
        "status": session.status,
        "project": {
            "name": session.project_brief.project_name,
            "type": session.project_brief.project_type,
            "area": session.project_brief.total_area,
            "cost": session.project_brief.total_cost,
        },
        "targets": [asdict(t) for t in session.targets],
        "ideas": [asdict(i) for i in session.ideas],
        "domain_reviews": [asdict(r) for r in session.domain_reviews],
        "report_markdown": session.report_markdown,
        "step_results": {
            str(k): v.to_dict() for k, v in session.step_results.items()
        },
    })


@app.route("/api/ve/session/<session_id>/feedback", methods=["POST"])
def ve_session_feedback(session_id):
    """사용자 피드백 저장."""
    leader = _get_ve_leader()
    session = leader.sessions.get(session_id)
    if not session:
        return jsonify({"error": "세션을 찾을 수 없습니다."}), 404

    feedback = request.get_json(silent=True) or {}
    # 향후 피드백 저장 로직 구현 예정
    return jsonify({"status": "feedback_received", "session_id": session_id})


@app.route("/api/ve/sessions")
def ve_list_sessions():
    """모든 VE 세션 목록 조회."""
    leader = _get_ve_leader()
    sessions = []
    for sid, s in leader.sessions.items():
        sessions.append({
            "session_id": sid,
            "project_name": s.project_brief.project_name,
            "status": s.status,
            "ideas_count": len(s.ideas),
            "created_at": s.created_at,
        })
    return jsonify({"sessions": sessions})


# ═══════════════════════════════════════════════════════════
#  VE Roundtable API (Async v2 — 비동기 처리)
# ═══════════════════════════════════════════════════════════

_roundtable_sessions = {}


@app.route("/api/ve/roundtable", methods=["POST"])
def ve_roundtable():
    """VE 라운드테이블 토론 세션 생성 (비동기).

    세션 ID를 즉시 반환하고, 백그라운드에서 Agent 토론을 실행합니다.
    프론트엔드는 GET /api/ve/roundtable/<id>/messages?since=<index> 로
    새 메시지를 폴링하여 실시간으로 수신합니다.
    """
    from src.agents.roundtable import start_roundtable_async

    project_text = ""
    project_name = ""
    disciplines = []

    # 파일 업로드 처리
    if "file" in request.files:
        f = request.files["file"]
        fname = f.filename.lower()
        if fname.endswith(".txt"):
            project_text = f.read().decode("utf-8", errors="ignore")
        elif fname.endswith(".pdf"):
            try:
                import fitz
                pdf_bytes = f.read()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                pages = []
                for page in doc:
                    pages.append(page.get_text())
                    if len(pages) >= 10:
                        break
                project_text = "\n".join(pages)
            except Exception as e:
                project_text = f"(PDF 파싱 실패: {e})"
        project_name = request.form.get("project_name", f.filename)
        disc_raw = request.form.get("disciplines", "건축,전기")
        disciplines = [d.strip() for d in disc_raw.split(",") if d.strip()]
        api_key = request.form.get("api_key", "").strip()
    else:
        data = request.get_json(silent=True) or {}
        project_text = data.get("project_text", "")
        project_name = data.get("project_name", "VE 프로젝트")
        disciplines = data.get("disciplines", ["건축", "전기"])
        api_key = data.get("api_key", "").strip()

    if not project_text:
        return jsonify({"error": "프로젝트 정보가 없습니다. 파일을 업로드하거나 텍스트를 입력하세요."}), 400

    try:
        # 비동기 시작 — 세션 즉시 반환
        session = start_roundtable_async(project_text, project_name, disciplines, api_key=api_key)
        _roundtable_sessions[session.session_id] = session
        return jsonify({
            "session_id": session.session_id,
            "status": session.status,
            "message_count": 0,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ve/roundtable/<session_id>/messages")
def ve_roundtable_messages(session_id):
    """라운드테이블 메시지 폴링 조회.

    Query params:
        since (int): 이 인덱스 이후의 새 메시지만 반환 (0-indexed).
                     최초 요청 시 since=0, 이후 반환된 total_count를 전달.
    """
    session = _roundtable_sessions.get(session_id)
    if not session:
        return jsonify({"error": "세션 없음"}), 404

    since = request.args.get("since", 0, type=int)

    with session._lock:
        all_messages = list(session.messages)

    new_messages = all_messages[since:]

    return jsonify({
        "session_id": session_id,
        "status": session.status,
        "error": session.error,
        "total_count": len(all_messages),
        "new_messages": [m.to_dict() for m in new_messages],
    })


@app.route("/api/ve/roundtable/sessions")
def ve_roundtable_sessions():
    """완료된 라운드테이블 세션 목록 조회 (보고서 페이지용)."""
    sessions = []
    for sid, s in _roundtable_sessions.items():
        with s._lock:
            msg_count = len(s.messages)
        sessions.append({
            "session_id": sid,
            "project_name": s.project_name,
            "status": s.status,
            "message_count": msg_count,
            "created_at": s.created_at,
        })
    sessions.sort(key=lambda x: -x["created_at"])
    return jsonify({"sessions": sessions})


@app.route("/api/ve/fast-diagram", methods=["POST"])
def ve_fast_diagram():
    """AI 기반 FAST Diagram Mermaid 코드 생성."""
    data = request.get_json(force=True)
    project = data.get("project", "건축 시설")
    higher = data.get("higher_function", "")
    desc = data.get("description", "")
    api_key = data.get("api_key", "").strip() or os.environ.get("GEMINI_API_KEY", "")

    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY not set"}), 500

    prompt = f"""당신은 VE(Value Engineering) FAST Diagram 전문가(Charles Bytheway 방법론)입니다.
아래 프로젝트에 대한 표준 FAST Diagram을 Mermaid flowchart LR 코드로 작성하세요.

[프로젝트]: {project}
{f'[상위 기능]: {higher}' if higher else ''}
{f'[상세 설명]: {desc[:500]}' if desc else ''}

[표준 FAST Diagram 레이아웃 - 반드시 준수]

■ 배치 방향: flowchart LR (좌→우)
  - 좌측 시작 = Higher Order Function (WHY? 최종 상위 목적)
  - 중앙 = Basic Function → Critical Path (SCOPE/WHAT)
  - 우측 끝 = Lower Order Function (HOW? 구체적 수단/입력)
  - 화살표(-->)는 좌→우: HOF --> BF --> DC1 --> DC2 --> ... --> LOF
  - 좌→우 읽기 = "HOW?", 우→좌 읽기 = "WHY?"

■ 노드 콘텐츠 형식 (매우 중요 - HTML 라벨 사용):
  모든 노드는 제목(굵게) + 줄바꿈 + 세부설명 형태로 작성합니다.
  형식: 노드id["<b>제목</b><br/><small>세부 설명 1줄</small>"]
  예시: dc1["<b>빛 생성</b><br/><small>LED/할로겐 광원 사용</small>"]

■ 기능 분류 (모두 포함):
  a) HOF: 프로젝트 최종 목적 1개 (좌측 끝, 평행사변형)
  b) BF: 핵심 존재 이유 1개 (HOF 바로 오른쪽, :::basic 스타일)
  c) DC: Critical Path 필수 기능 4~6개 (사각 박스, 일렬 연결)
  d) LOF: 입력/전제 조건 1~2개 (우측 끝, 평행사변형)
  e) SF: Supporting Functions 3~4개 (둥근 박스, Critical Path 아래에서 When? 점선 연결)
  f) Design Criteria: 상단 subgraph 3~4개
  g) All-the-time: 상단 subgraph 3~4개

■ Mermaid 코드 규칙:
  - 첫줄: flowchart LR
  - HOF: hof[/"<b>상위기능</b><br/><small>설명</small>"/]
  - BF: bf["<b>기본기능</b><br/><small>설명</small>"]:::basic
  - DC: dc1["<b>기능명</b><br/><small>설명</small>"]
  - LOF: lof[/"<b>입력기능</b><br/><small>설명</small>"/]
  - SF: sf1("<b>지원기능</b><br/><small>설명</small>")
  - Design Criteria: subgraph DC["🔧 설계 기준 Design Criteria"] ... end
  - All-the-time: subgraph AT["⏰ 항시 기능 All-the-time"] ... end
  - Critical Path: 실선 -->
  - When?/지원: 점선 -.->|When|
  - classDef basic fill:#1E3A5F,stroke:#1E3A5F,color:#fff,font-weight:bold,font-size:16px

[출력 형식 예시 - PC 프로젝터]
flowchart LR
    subgraph DC["🔧 설계 기준 Design Criteria"]
        cr1["<b>아이디어 전달</b><br/><small>프레젠테이션 지원</small>"]
        cr2["<b>소음 최소화</b><br/><small>팬/냉각 소음 40dB 이하</small>"]
        cr3["<b>내구성 확보</b><br/><small>10,000시간 램프 수명</small>"]
    end
    subgraph AT["⏰ 항시 기능 All-the-time"]
        at1["<b>미관 향상</b><br/><small>슬림 디자인 적용</small>"]
        at2["<b>부상 방지</b><br/><small>과열 차단 장치</small>"]
        at3["<b>고객 안내</b><br/><small>OSD 메뉴 제공</small>"]
    end
    hof[/"<b>정보 공유</b><br/><small>회의실 프레젠테이션</small>"/] --> bf["<b>이미지 투사</b><br/><small>스크린에 영상 출력</small>"]:::basic --> dc1["<b>이미지 초점</b><br/><small>렌즈 광학 조정</small>"] --> dc2["<b>빛 투과</b><br/><small>LCD/DLP 패널 통과</small>"] --> dc3["<b>빛 생성</b><br/><small>광원 램프 발광</small>"] --> dc4["<b>에너지 변환</b><br/><small>전기→광 에너지</small>"] --> lof[/"<b>전기 수신</b><br/><small>AC 전원 입력</small>"/]
    dc3 -.->|When| sf1("<b>열 최소화</b><br/><small>냉각팬 작동</small>")
    dc3 -.->|When| sf2("<b>전력 최소화</b><br/><small>절전 모드</small>")
    dc2 -.->|When| sf3("<b>신호 변환</b><br/><small>디지털→아날로그</small>")
    lof2[/"<b>신호 수신</b><br/><small>HDMI/VGA 입력</small>"/] --> sf4("<b>신호 전달</b><br/><small>영상 데이터 전송</small>") -.-> sf3
    classDef basic fill:#1E3A5F,stroke:#1E3A5F,color:#fff,font-weight:bold,font-size:16px

위 예시는 참고용입니다. 프로젝트 "{project}"에 맞는 고유한 FAST Diagram을 생성하세요.
총 노드 수: 18~25개. 순수 Mermaid 코드만 출력하세요. 설명이나 마크다운 코드블록 없이."""

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=3500),
        )
        code = resp.text.strip()
        # 마크다운 코드블록 제거
        if code.startswith("```"):
            code = code.split("\n", 1)[1] if "\n" in code else code[3:]
        if code.endswith("```"):
            code = code[:-3].strip()
        if code.startswith("mermaid"):
            code = code[7:].strip()
        return jsonify({"mermaid_code": code})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print(f"VE Dashboard starting...")
    print(f"  DB: Supabase PostgreSQL ({os.getenv('SUPABASE_DB_HOST')})")
    print(f"  KG: {KG_DIR}")
    app.run(debug=True, port=5000, host="127.0.0.1")

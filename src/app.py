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
    """절대 경로 이미지 서빙."""
    fpath = request.args.get("path", "")
    p = Path(fpath)
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


if __name__ == "__main__":
    print(f"VE Dashboard starting...")
    print(f"  DB: Supabase PostgreSQL ({os.getenv('SUPABASE_DB_HOST')})")
    print(f"  KG: {KG_DIR}")
    app.run(debug=True, port=5000, host="127.0.0.1")


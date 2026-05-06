"""
VE Database Development - Knowledge Graph Visualizer
=====================================================
NetworkX 기반 Knowledge Graph를 matplotlib로 시각화합니다.

출력:
  - data/kg/kg_full_graph.png — 전체 그래프 (고해상도)
  - data/kg/kg_worktype_distribution.png — 공종별 대안 분포 차트
  - data/kg/kg_value_type_distribution.png — 가치유형 분포 차트
"""

import json
import sqlite3
import matplotlib
matplotlib.use('Agg')  # 비대화형 백엔드

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import networkx as nx
from pathlib import Path
from collections import Counter

from src.config import DB_PATH, KG_DIR, ensure_directories
from src.kg_builder import build_knowledge_graph, get_graph_stats, NODE_TYPES


# 한글 폰트 설정
def setup_korean_font():
    """matplotlib에서 한글 폰트를 설정합니다."""
    # Windows 기본 한글 폰트 경로
    font_candidates = [
        'C:/Windows/Fonts/malgun.ttf',     # 맑은 고딕
        'C:/Windows/Fonts/NanumGothic.ttf', # 나눔고딕
        'C:/Windows/Fonts/gulim.ttc',       # 굴림
    ]
    for font_path in font_candidates:
        if Path(font_path).exists():
            font_prop = fm.FontProperties(fname=font_path)
            plt.rcParams['font.family'] = font_prop.get_name()
            plt.rcParams['axes.unicode_minus'] = False
            return font_prop
    # 폴백: 기본 sans-serif
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['axes.unicode_minus'] = False
    return None


def visualize_full_graph(
    G: nx.DiGraph,
    output_path: Path = None,
    figsize: tuple = (24, 18),
):
    """
    전체 Knowledge Graph를 시각화합니다.
    노드 타입별 색상, 크기를 다르게 표시합니다.
    """
    if output_path is None:
        output_path = KG_DIR / "kg_full_graph.png"

    font_prop = setup_korean_font()

    fig, ax = plt.subplots(1, 1, figsize=figsize, facecolor='#1a1a2e')
    ax.set_facecolor('#1a1a2e')

    # 레이아웃 계산
    pos = nx.spring_layout(G, k=2.5, iterations=80, seed=42)

    # 노드 타입별 그리기
    for node_type, color in NODE_TYPES.items():
        nodes = [n for n, d in G.nodes(data=True) if d.get('node_type') == node_type]
        if not nodes:
            continue

        # 노드 크기: Alternative=150, 나머지 = degree에 비례
        if node_type == "Alternative":
            node_sizes = [150 for _ in nodes]
            alpha = 0.6
        elif node_type == "Project":
            node_sizes = [800]
            alpha = 1.0
        else:
            node_sizes = [max(200, G.degree(n) * 80) for n in nodes]
            alpha = 0.9

        nx.draw_networkx_nodes(
            G, pos, nodelist=nodes,
            node_color=color, node_size=node_sizes,
            alpha=alpha, ax=ax,
        )

    # 엣지 그리기
    edge_colors = {
        "BELONGS_TO": "#555555",
        "CLASSIFIED_AS": "#F39C12",
        "LOCATED_AT": "#45B7D1",
        "USES_MATERIAL": "#FFEAA7",
        "WORK_TYPE": "#96CEB4",
        "EVALUATED_BY": "#DDA0DD",
    }
    for edge_type, color in edge_colors.items():
        edges = [(u, v) for u, v, d in G.edges(data=True)
                 if d.get('edge_type') == edge_type]
        if edges:
            nx.draw_networkx_edges(
                G, pos, edgelist=edges,
                edge_color=color, alpha=0.3,
                width=0.5, arrows=False, ax=ax,
            )

    # 비-Alternative 노드에만 레이블 표시
    labels = {}
    for n, d in G.nodes(data=True):
        if d.get('node_type') != 'Alternative':
            labels[n] = d.get('label', n)[:15]

    nx.draw_networkx_labels(
        G, pos, labels=labels,
        font_size=7, font_color='white',
        font_weight='bold', ax=ax,
        font_family=font_prop.get_name() if font_prop else 'sans-serif',
    )

    # 범례
    legend_elements = []
    for node_type, color in NODE_TYPES.items():
        count = sum(1 for _, d in G.nodes(data=True) if d.get('node_type') == node_type)
        if count > 0:
            legend_elements.append(
                plt.scatter([], [], c=color, s=100, label=f"{node_type} ({count})")
            )

    ax.legend(handles=legend_elements, loc='upper left',
              fontsize=10, facecolor='#16213e', edgecolor='#e94560',
              labelcolor='white', framealpha=0.8)

    ax.set_title(
        'VE Report Knowledge Graph — 강원특별자치도 신청사 건립공사',
        fontsize=16, color='white', fontweight='bold', pad=20,
        fontproperties=font_prop,
    )

    stats = get_graph_stats(G)
    info_text = f"Nodes: {stats['total_nodes']} | Edges: {stats['total_edges']} | Components: {stats['components']}"
    ax.text(0.5, -0.02, info_text, transform=ax.transAxes,
            ha='center', fontsize=10, color='#aaaaaa')

    ax.axis('off')
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=200, facecolor='#1a1a2e',
                bbox_inches='tight', pad_inches=0.5)
    plt.close()

    print(f"  Full graph saved to: {output_path}")
    return output_path


def visualize_worktype_distribution(
    db_path: Path = None,
    output_path: Path = None,
):
    """공종별 대안 분포를 바 차트로 시각화합니다."""
    if db_path is None:
        db_path = DB_PATH
    if output_path is None:
        output_path = KG_DIR / "kg_worktype_distribution.png"

    font_prop = setup_korean_font()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 대안별 공종 분류 (키워드 기반)
    from src.kg_builder import WORK_TYPE_KEYWORDS
    alts = conn.execute("SELECT alt_number, proposal_title, original_description FROM alternatives").fetchall()

    worktype_counts = Counter()
    for alt in alts:
        text = f"{alt['proposal_title']} {alt['original_description']}"
        for wtype, keywords in WORK_TYPE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                worktype_counts[wtype] += 1

    conn.close()

    # 차트 생성
    fig, ax = plt.subplots(figsize=(12, 6), facecolor='#1a1a2e')
    ax.set_facecolor('#16213e')

    wt_labels = list(worktype_counts.keys())
    wt_values = list(worktype_counts.values())

    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
    bars = ax.barh(wt_labels, wt_values, color=colors[:len(wt_labels)],
                   edgecolor='white', linewidth=0.5, alpha=0.85)

    # 값 표시
    for bar, val in zip(bars, wt_values):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f'{val}개', ha='left', va='center', color='white', fontsize=11,
                fontproperties=font_prop)

    ax.set_xlabel('대안 수', fontsize=12, color='white', fontproperties=font_prop)
    ax.set_title('공종별 VE 대안 분포', fontsize=14, color='white',
                fontweight='bold', fontproperties=font_prop)
    ax.tick_params(colors='white', labelsize=11)
    for label in ax.get_yticklabels():
        label.set_fontproperties(font_prop)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#555555')
    ax.spines['left'].set_color('#555555')

    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150, facecolor='#1a1a2e', bbox_inches='tight')
    plt.close()

    print(f"  WorkType chart saved to: {output_path}")
    return output_path


def visualize_value_type_distribution(
    db_path: Path = None,
    output_path: Path = None,
):
    """가치유형별 분포를 파이 차트로 시각화합니다."""
    if db_path is None:
        db_path = DB_PATH
    if output_path is None:
        output_path = KG_DIR / "kg_value_type_distribution.png"

    font_prop = setup_korean_font()

    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("""
        SELECT value_type, COUNT(*) as cnt
        FROM value_evaluations
        WHERE value_type != '' AND value_type NOT LIKE '0%'
        GROUP BY value_type
        ORDER BY cnt DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("  No valid value type data found.")
        return None

    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]

    fig, ax = plt.subplots(figsize=(10, 8), facecolor='#1a1a2e')
    ax.set_facecolor('#1a1a2e')

    colors = ['#4ECDC4', '#FF6B6B', '#45B7D1', '#FFEAA7', '#96CEB4', '#DDA0DD']
    explode = [0.05] * len(labels)

    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors[:len(labels)],
        explode=explode, autopct='%1.1f%%',
        textprops={'color': 'white', 'fontsize': 12},
        pctdistance=0.75, labeldistance=1.15,
        shadow=True, startangle=90,
    )

    # 한글 폰트 적용
    if font_prop:
        for text in texts + autotexts:
            text.set_fontproperties(font_prop)

    ax.set_title('VE 대안 가치유형 분포', fontsize=14, color='white',
                fontweight='bold', pad=20, fontproperties=font_prop)

    # 통계 텍스트
    total = sum(values)
    info = f"총 {total}개 대안 (유형 분류 완료)"
    ax.text(0.5, -0.05, info, transform=ax.transAxes,
            ha='center', fontsize=10, color='#aaaaaa',
            fontproperties=font_prop)

    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150, facecolor='#1a1a2e', bbox_inches='tight')
    plt.close()

    print(f"  ValueType chart saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    ensure_directories()

    print("=== Building Knowledge Graph ===")
    G = build_knowledge_graph()

    print("\n=== Generating Visualizations ===")
    visualize_full_graph(G)
    visualize_worktype_distribution()
    visualize_value_type_distribution()

    print("\n=== All visualizations saved to data/kg/ ===")

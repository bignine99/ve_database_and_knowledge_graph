"""
VE Database Development - ML Classifier & Clustering
======================================================
Tier 3: 자동 분류 — TF-IDF + SVM 기반 HOW2/ValueType 분류기
Tier 4: 클러스터링 — Embedding 기반 자동 군집화 + 인사이트 생성

학습 데이터: 727개 라벨링된 VE 대안 (Supabase DB)
"""

import json
import os
import time
import pickle
import numpy as np
from pathlib import Path
from collections import Counter
from typing import Optional

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

ML_DIR = BASE_DIR / "data" / "ml_models"
EMBEDDINGS_DIR = BASE_DIR / "data" / "embeddings"
EMBEDDINGS_PATH = EMBEDDINGS_DIR / "ve_embeddings.npz"
METADATA_PATH = EMBEDDINGS_DIR / "ve_metadata.json"

# ══════════════════════════════════════════
# Tier 3: 자동 분류 (HOW2 + ValueType)
# ══════════════════════════════════════════

# 싱글톤 캐시
_how2_classifier = None
_vtype_classifier = None


def _get_db_data() -> list[dict]:
    """DB에서 학습 데이터를 조회합니다."""
    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        port=int(os.getenv("SUPABASE_DB_PORT", 5432)),
        dbname=os.getenv("SUPABASE_DB_NAME", "postgres"),
        user=os.getenv("SUPABASE_DB_USER", "postgres"),
        password=os.getenv("SUPABASE_DB_PASS"),
        sslmode="require",
    )
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT a.alt_id, a.alt_number, a.proposal_title,
               a.original_description, a.alternative_description,
               a.how2_code, a.how2_name, a.value_type_corrected,
               a.field_category
        FROM alternatives a
        ORDER BY a.alt_number
    """)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def _build_text(row: dict) -> str:
    """대안 데이터에서 분류용 텍스트를 생성합니다."""
    parts = [
        row.get("proposal_title") or "",
        row.get("original_description") or "",
        row.get("alternative_description") or "",
    ]
    return " ".join(p for p in parts if p).strip()


# HOW1 코드 매핑 (HOW2의 첫 글자 → HOW1 대분류)
HOW1_MAP = {
    "A": "A 건축공사", "B": "B 토목공사", "C": "C 조경공사",
    "D": "D 전기공사", "E": "E 기계설비공사", "F": "F 소방공사",
}

# 신뢰도 임계값
CONFIDENCE_THRESHOLD = 0.35


def train_classifiers(min_samples: int = 3) -> dict:
    """
    3개 분류기를 학습합니다:
      1) HOW1 대분류 (6클래스) — 정확도 높음
      2) HOW2 세부분류 (40클래스) — 참고용
      3) ValueType 가치유형 (4클래스)
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.svm import LinearSVC
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score
    from sklearn.pipeline import Pipeline
    from sklearn.calibration import CalibratedClassifierCV

    ML_DIR.mkdir(parents=True, exist_ok=True)
    rows = _get_db_data()
    results = {}

    # ── HOW1 대분류 분류기 (6클래스 — 핵심) ──
    print("  [ML] Training HOW1 classifier (6 classes)...", flush=True)
    how1_texts, how1_labels = [], []
    for r in rows:
        text = _build_text(r)
        code = r.get("how2_code") or ""
        if text and code and code[0] in HOW1_MAP:
            how1_texts.append(text)
            how1_labels.append(code[0])

    print(f"    Data: {len(how1_texts)} samples, {len(set(how1_labels))} classes", flush=True)

    how1_pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2), sublinear_tf=True)),
        ("svm", CalibratedClassifierCV(
            LinearSVC(C=1.0, max_iter=5000, class_weight="balanced"),
            cv=3, method="sigmoid"
        )),
    ])
    cv_how1 = cross_val_score(how1_pipeline, how1_texts, how1_labels, cv=5, scoring="accuracy")
    how1_acc = round(cv_how1.mean() * 100, 1)
    print(f"    Cross-val accuracy: {how1_acc}% (±{cv_how1.std()*100:.1f}%)", flush=True)
    how1_pipeline.fit(how1_texts, how1_labels)
    with open(ML_DIR / "how1_classifier.pkl", "wb") as f:
        pickle.dump(how1_pipeline, f)
    results["how1"] = {
        "accuracy": how1_acc, "cv_std": round(cv_how1.std()*100, 1),
        "classes": len(set(how1_labels)), "samples": len(how1_texts),
        "label_distribution": dict(Counter(how1_labels).most_common()),
    }

    # ── HOW2 세부분류 분류기 (CalibratedClassifierCV로 확률 출력) ──
    print("  [ML] Training HOW2 classifier (calibrated)...", flush=True)
    how2_texts, how2_labels = [], []
    for r in rows:
        text = _build_text(r)
        label = r.get("how2_code") or ""
        if text and label and label.strip():
            how2_texts.append(text)
            how2_labels.append(label)

    label_counts = Counter(how2_labels)
    valid_labels = {l for l, c in label_counts.items() if c >= min_samples}
    filtered_texts = [t for t, l in zip(how2_texts, how2_labels) if l in valid_labels]
    filtered_labels = [l for l in how2_labels if l in valid_labels]
    print(f"    Data: {len(filtered_texts)} samples, {len(valid_labels)} classes", flush=True)

    how2_pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2), sublinear_tf=True)),
        ("svm", CalibratedClassifierCV(
            LinearSVC(C=1.0, max_iter=5000, class_weight="balanced"),
            cv=3, method="sigmoid"
        )),
    ])
    cv_how2 = cross_val_score(how2_pipeline, filtered_texts, filtered_labels, cv=5, scoring="accuracy")
    how2_acc = round(cv_how2.mean() * 100, 1)
    print(f"    Cross-val accuracy: {how2_acc}% (±{cv_how2.std()*100:.1f}%)", flush=True)
    how2_pipeline.fit(filtered_texts, filtered_labels)
    with open(ML_DIR / "how2_classifier.pkl", "wb") as f:
        pickle.dump(how2_pipeline, f)
    results["how2"] = {
        "accuracy": how2_acc, "cv_std": round(cv_how2.std()*100, 1),
        "classes": len(valid_labels), "samples": len(filtered_texts),
        "label_distribution": dict(Counter(filtered_labels).most_common(20)),
    }

    # ── ValueType 분류기 ──
    print("  [ML] Training ValueType classifier...", flush=True)
    vtype_texts, vtype_labels = [], []
    for r in rows:
        text = _build_text(r)
        label = r.get("value_type_corrected") or ""
        if text and label and label.strip() and label not in ("미분류", "0 0.00"):
            vtype_texts.append(text)
            vtype_labels.append(label)
    print(f"    Data: {len(vtype_texts)} samples, {len(set(vtype_labels))} classes", flush=True)

    vtype_pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2), sublinear_tf=True)),
        ("svm", CalibratedClassifierCV(
            LinearSVC(C=1.0, max_iter=5000, class_weight="balanced"),
            cv=3, method="sigmoid"
        )),
    ])
    cv_vtype = cross_val_score(vtype_pipeline, vtype_texts, vtype_labels, cv=5, scoring="accuracy")
    vtype_acc = round(cv_vtype.mean() * 100, 1)
    print(f"    Cross-val accuracy: {vtype_acc}% (±{cv_vtype.std()*100:.1f}%)", flush=True)
    vtype_pipeline.fit(vtype_texts, vtype_labels)
    with open(ML_DIR / "vtype_classifier.pkl", "wb") as f:
        pickle.dump(vtype_pipeline, f)
    results["vtype"] = {
        "accuracy": vtype_acc, "cv_std": round(cv_vtype.std()*100, 1),
        "classes": len(set(vtype_labels)), "samples": len(vtype_texts),
        "label_distribution": dict(Counter(vtype_labels).most_common()),
    }

    with open(ML_DIR / "training_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return results


# 싱글톤 캐시
_how1_classifier = None


def _load_classifier(name: str):
    """학습된 분류기를 로드합니다."""
    path = ML_DIR / f"{name}_classifier.pkl"
    if not path.exists():
        raise FileNotFoundError(f"분류기 {path}가 없습니다. train_classifiers()를 먼저 실행하세요.")
    with open(path, "rb") as f:
        return pickle.load(f)


def classify_alternative(text: str) -> dict:
    """
    새로운 대안 텍스트에 대해 HOW1/HOW2 대공종과 ValueType을 자동 분류합니다.

    개선 사항:
      - HOW1 대분류 (6클래스, 정확도 높음) 추가
      - 신뢰도 임계값 35% — 미달 시 "분류 불확실" + Top-3 후보 반환
      - CalibratedClassifierCV로 실제 확률 기반 신뢰도

    Returns:
        {"how1": {"code", "name", "confidence", "reliable"},
         "how2": {"code", "confidence", "reliable", "top3": [...]},
         "value_type": {"type", "confidence", "reliable", "top3": [...]}}
    """
    global _how1_classifier, _how2_classifier, _vtype_classifier

    if _how1_classifier is None:
        _how1_classifier = _load_classifier("how1")
    if _how2_classifier is None:
        _how2_classifier = _load_classifier("how2")
    if _vtype_classifier is None:
        _vtype_classifier = _load_classifier("vtype")

    result = {}

    # ── HOW1 대분류 (6클래스, 신뢰도 높음) ──
    how1_proba = _how1_classifier.predict_proba([text])[0]
    how1_classes = _how1_classifier.classes_
    how1_idx = np.argmax(how1_proba)
    how1_conf = float(how1_proba[how1_idx])
    how1_code = how1_classes[how1_idx]
    result["how1"] = {
        "code": how1_code,
        "name": HOW1_MAP.get(how1_code, how1_code),
        "confidence": round(how1_conf, 3),
        "reliable": how1_conf >= CONFIDENCE_THRESHOLD,
    }

    # ── HOW2 세부분류 (40클래스, 신뢰도 임계값 적용) ──
    how2_proba = _how2_classifier.predict_proba([text])[0]
    how2_classes = _how2_classifier.classes_
    how2_sorted = np.argsort(how2_proba)[::-1]
    how2_top_idx = how2_sorted[0]
    how2_conf = float(how2_proba[how2_top_idx])
    how2_code = how2_classes[how2_top_idx]

    # Top-3 후보
    how2_top3 = []
    for idx in how2_sorted[:3]:
        how2_top3.append({
            "code": how2_classes[idx],
            "confidence": round(float(how2_proba[idx]), 3),
        })

    result["how2"] = {
        "code": how2_code if how2_conf >= CONFIDENCE_THRESHOLD else None,
        "confidence": round(how2_conf, 3),
        "reliable": how2_conf >= CONFIDENCE_THRESHOLD,
        "status": "확정" if how2_conf >= CONFIDENCE_THRESHOLD else "불확실 — 후보 참고",
        "top3": how2_top3,
    }

    # ── ValueType 분류 ──
    vtype_proba = _vtype_classifier.predict_proba([text])[0]
    vtype_classes = _vtype_classifier.classes_
    vtype_sorted = np.argsort(vtype_proba)[::-1]
    vtype_top_idx = vtype_sorted[0]
    vtype_conf = float(vtype_proba[vtype_top_idx])

    vtype_top3 = []
    for idx in vtype_sorted[:3]:
        vtype_top3.append({
            "type": vtype_classes[idx],
            "confidence": round(float(vtype_proba[idx]), 3),
        })

    result["value_type"] = {
        "type": vtype_classes[vtype_top_idx],
        "confidence": round(vtype_conf, 3),
        "reliable": vtype_conf >= CONFIDENCE_THRESHOLD,
        "top3": vtype_top3,
    }

    return result


# ══════════════════════════════════════════
# Tier 4: 클러스터링 + 인사이트
# ══════════════════════════════════════════

def build_clusters(n_clusters: int = 8) -> dict:
    """
    727개 VE 대안을 임베딩 벡터 기반으로 클러스터링합니다.

    Args:
        n_clusters: 클러스터 수

    Returns:
        {"clusters": [...], "silhouette_score": float}
    """
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    # 임베딩 로드
    if not EMBEDDINGS_PATH.exists() or not METADATA_PATH.exists():
        raise FileNotFoundError("임베딩 인덱스가 없습니다. semantic_search.build_embedding_index()를 먼저 실행하세요.")

    data = np.load(str(EMBEDDINGS_PATH))
    embeddings = data["embeddings"]
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print(f"  [Clustering] {embeddings.shape[0]} vectors, dim={embeddings.shape[1]}", flush=True)
    print(f"  [Clustering] K-Means with k={n_clusters}...", flush=True)

    t0 = time.time()

    # K-Means 클러스터링
    kmeans = KMeans(
        n_clusters=n_clusters,
        n_init=10,
        max_iter=300,
        random_state=42,
    )
    labels = kmeans.fit_predict(embeddings)

    # 실루엣 점수
    sil_score = round(silhouette_score(embeddings, labels), 4)
    build_time = round(time.time() - t0, 2)

    print(f"  [Clustering] Done in {build_time}s, silhouette={sil_score}", flush=True)

    # 클러스터별 분석
    clusters = []
    for cluster_id in range(n_clusters):
        member_indices = np.where(labels == cluster_id)[0]
        members = [metadata[i] for i in member_indices]

        # 통계
        how2_dist = Counter(m["how2_name"] for m in members if m.get("how2_name"))
        vtype_dist = Counter(m["value_type"] for m in members if m.get("value_type"))
        space_dist = Counter(m["space"] for m in members if m.get("space"))

        avg_savings = np.mean([m.get("savings_rate", 0) for m in members])
        avg_value = np.mean([m.get("value_change", 0) for m in members])
        avg_perf = np.mean([m.get("perf_change", 0) for m in members])
        avg_cost = np.mean([m.get("cost_change", 0) for m in members])

        # 대표 키워드 (가장 빈번한 HOW2 + Space)
        top_how2 = how2_dist.most_common(3)
        top_vtype = vtype_dist.most_common(2)
        top_space = space_dist.most_common(3)

        # 클러스터 자동 라벨링
        label_parts = []
        if top_how2:
            label_parts.append(top_how2[0][0].replace("공사", ""))
        if top_space:
            label_parts.append(top_space[0][0])
        if top_vtype:
            label_parts.append(top_vtype[0][0])
        cluster_label = " / ".join(label_parts) if label_parts else f"클러스터 {cluster_id}"

        # 중심에 가장 가까운 대안 (대표 대안)
        centroid = kmeans.cluster_centers_[cluster_id]
        member_embs = embeddings[member_indices]
        distances = np.linalg.norm(member_embs - centroid, axis=1)
        representative_idx = member_indices[np.argmin(distances)]
        representative = metadata[representative_idx]

        clusters.append({
            "cluster_id": cluster_id,
            "label": cluster_label,
            "size": len(members),
            "representative": {
                "alt_number": representative["alt_number"],
                "title": representative["title"],
            },
            "how2_distribution": [{"name": k, "count": v} for k, v in top_how2],
            "vtype_distribution": [{"name": k, "count": v} for k, v in top_vtype],
            "space_distribution": [{"name": k, "count": v} for k, v in top_space],
            "avg_savings_rate": round(avg_savings, 2),
            "avg_value_change": round(avg_value, 2),
            "avg_perf_change": round(avg_perf, 2),
            "avg_cost_change": round(avg_cost, 2),
            "members": [
                {"alt_number": m["alt_number"], "title": m["title"][:40]}
                for m in sorted(members, key=lambda x: x["alt_number"])
            ],
        })

    # 정렬: 사이즈 내림차순
    clusters.sort(key=lambda c: -c["size"])

    # 대안별 클러스터 할당 맵
    alt_cluster_map = {}
    for i, label in enumerate(labels):
        alt_cluster_map[metadata[i]["alt_number"]] = int(label)

    result = {
        "n_clusters": n_clusters,
        "silhouette_score": sil_score,
        "total_alternatives": len(metadata),
        "build_time": build_time,
        "clusters": clusters,
        "alt_cluster_map": alt_cluster_map,
    }

    # 저장
    ML_DIR.mkdir(parents=True, exist_ok=True)
    with open(ML_DIR / "cluster_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result


def get_cluster_for_alternative(alt_number: int) -> Optional[dict]:
    """특정 대안이 속한 클러스터 정보를 반환합니다."""
    result_path = ML_DIR / "cluster_result.json"
    if not result_path.exists():
        return None

    with open(result_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cluster_id = data["alt_cluster_map"].get(str(alt_number))
    if cluster_id is None:
        return None

    cluster = next((c for c in data["clusters"] if c["cluster_id"] == cluster_id), None)
    return cluster


# ══════════════════════════════════════════
# CLI: 학습 + 클러스터링 실행
# ══════════════════════════════════════════

if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 60)
    print("  VE ML Pipeline — Classifier Training + Clustering")
    print("=" * 60)

    # ── Tier 3: 분류기 학습 ──
    print("\n── Tier 3: Training Classifiers ──")
    train_result = train_classifiers(min_samples=5)

    print(f"\n  HOW1 Classifier (대분류):")
    print(f"    Accuracy: {train_result['how1']['accuracy']}% (±{train_result['how1']['cv_std']}%)")
    print(f"    Classes: {train_result['how1']['classes']}")
    print(f"    Samples: {train_result['how1']['samples']}")

    print(f"\n  HOW2 Classifier (세부):")
    print(f"    Accuracy: {train_result['how2']['accuracy']}% (±{train_result['how2']['cv_std']}%)")
    print(f"    Classes: {train_result['how2']['classes']}")
    print(f"    Samples: {train_result['how2']['samples']}")

    print(f"\n  ValueType Classifier:")
    print(f"    Accuracy: {train_result['vtype']['accuracy']}% (±{train_result['vtype']['cv_std']}%)")
    print(f"    Classes: {train_result['vtype']['classes']}")
    print(f"    Samples: {train_result['vtype']['samples']}")

    # 분류 테스트
    print(f"\n── Classification Test (with confidence threshold={CONFIDENCE_THRESHOLD:.0%}) ──")
    test_texts = [
        "옥상 방수를 우레탄 도막방수에서 액체방수로 변경",
        "LED 조명기구를 에너지 절감형으로 교체",
        "지하주차장 바닥 에폭시 코팅을 콘크리트 폴리싱으로 변경",
        "엘리베이터 설치 위치를 변경하여 공간 효율성 확보",
        "외벽 단열재를 경질우레탄폼 두께 축소",
    ]
    for text in test_texts:
        pred = classify_alternative(text)
        h1 = pred["how1"]
        h2 = pred["how2"]
        vt = pred["value_type"]
        print(f"\n  '{text[:45]}'")
        h1_mark = '✅' if h1['reliable'] else '⚠'
        print(f"    HOW1: {h1['name']} (conf={h1['confidence']:.1%}) {h1_mark}")
        top3_str = ', '.join(f"{c['code']}({c['confidence']:.0%})" for c in h2['top3'])
        print(f"    HOW2: {h2['status']} — Top3: {top3_str}")
        vt_mark = '✅' if vt['reliable'] else '⚠'
        print(f"    VType: {vt['type']} (conf={vt['confidence']:.1%}) {vt_mark}")

    # ── Tier 4: 클러스터링 ──
    print(f"\n\n── Tier 4: Building Clusters ──")
    cluster_result = build_clusters(n_clusters=8)

    print(f"\n  Silhouette Score: {cluster_result['silhouette_score']}")
    print(f"\n  Cluster Summary:")
    for c in cluster_result["clusters"]:
        print(f"\n    [{c['cluster_id']}] {c['label']} ({c['size']}건)")
        print(f"      대표: #{c['representative']['alt_number']:03d} {c['representative']['title'][:40]}")
        print(f"      절감율: {c['avg_savings_rate']:+.2f}% | 가치변화: {c['avg_value_change']:+.2f}%")
        if c["how2_distribution"]:
            h2_str = ", ".join(f"{d['name']}({d['count']})" for d in c["how2_distribution"])
            print(f"      공종: {h2_str}")

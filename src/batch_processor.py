"""
VE Database Development - Batch Processor
============================================
전체 PDF에서 모든 대안을 순회하며 통합 파이프라인을 실행합니다.

산출물:
  - data/extracted/alt_001.json ~ alt_107.json
  - data/images/{alt_label}/ — 개요도/차트 이미지
  - scratch/batch_report.json — 처리 결과 리포트
"""

import json
import time
import traceback
from pathlib import Path
from typing import Optional

from src.config import EXTRACTED_DIR, ensure_directories
from src.pdf_processor import get_pdf_path, detect_alternative_pages
from src.pipeline import extract_single_alternative, save_alternative_json
from src.schemas import validate_alternative


def run_batch(
    pdf_path: Path = None,
    limit: Optional[int] = None,
    skip_images: bool = False,
    resume_from: int = 0,
) -> dict:
    """
    전체 PDF에서 모든 대안을 배치 처리합니다.

    Args:
        pdf_path: PDF 파일 경로 (None이면 자동 탐색)
        limit: 처리할 최대 대안 수 (테스트용)
        skip_images: 이미지 추출 건너뛰기 (속도 향상)
        resume_from: 이 번호부터 재개 (중단/재개 기능)

    Returns:
        {
            "total": int,
            "success": int,
            "failed": int,
            "skipped": int,
            "results": [{"alt_number": int, "status": str, ...}],
            "elapsed_seconds": float,
        }
    """
    ensure_directories()

    if pdf_path is None:
        pdf_path = get_pdf_path()

    spreads = detect_alternative_pages(pdf_path)
    if limit:
        spreads = spreads[:limit]

    total = len(spreads)
    success = 0
    failed = 0
    skipped = 0
    results = []

    start_time = time.time()

    for idx, spread in enumerate(spreads):
        alt_label = spread["alt_label"]

        # 중단/재개: resume_from 이전은 건너뛰기
        alt_num_match = _extract_alt_number(alt_label)
        if alt_num_match and alt_num_match < resume_from:
            skipped += 1
            results.append({
                "alt_label": alt_label,
                "alt_number": alt_num_match,
                "status": "skipped",
                "reason": f"resume_from={resume_from}",
            })
            continue

        # 이미 추출된 파일이 있으면 건너뛰기 (재실행 시)
        existing = EXTRACTED_DIR / f"alt_{alt_num_match:03d}.json"
        if existing.exists() and resume_from > 0:
            skipped += 1
            results.append({
                "alt_label": alt_label,
                "alt_number": alt_num_match,
                "status": "skipped",
                "reason": "already_exists",
            })
            continue

        print(f"  [{idx+1}/{total}] Processing {alt_label}...", end="", flush=True)

        try:
            data = extract_single_alternative(
                pdf_path, spread, extract_images=not skip_images
            )

            # 검증
            validation = validate_alternative(data)

            # JSON 저장
            json_path = save_alternative_json(data)

            success += 1
            results.append({
                "alt_label": alt_label,
                "alt_number": data.alt_number,
                "status": "success",
                "completeness": validation["completeness"],
                "valid": validation["valid"],
                "missing": validation["missing"],
                "warnings": validation["warnings"],
                "json_path": str(json_path),
            })
            print(f" OK (completeness={validation['completeness']})")

        except Exception as e:
            failed += 1
            error_msg = str(e)
            results.append({
                "alt_label": alt_label,
                "alt_number": alt_num_match,
                "status": "failed",
                "error": error_msg,
                "traceback": traceback.format_exc(),
            })
            print(f" FAILED: {error_msg}")

    elapsed = time.time() - start_time

    report = {
        "total": total,
        "success": success,
        "failed": failed,
        "skipped": skipped,
        "elapsed_seconds": round(elapsed, 2),
        "avg_seconds_per_alt": round(elapsed / max(success, 1), 2),
        "results": results,
    }

    # 리포트 저장
    report_path = Path("scratch") / "batch_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n=== Batch Complete ===")
    print(f"  Total: {total}")
    print(f"  Success: {success}")
    print(f"  Failed: {failed}")
    print(f"  Skipped: {skipped}")
    print(f"  Elapsed: {elapsed:.1f}s ({elapsed/max(success,1):.1f}s/alt)")
    print(f"  Report: {report_path}")

    # 실패 리스트 출력
    failed_items = [r for r in results if r["status"] == "failed"]
    if failed_items:
        print(f"\n  Failed alternatives:")
        for fi in failed_items:
            print(f"    {fi['alt_label']}: {fi['error'][:80]}")

    return report


def _extract_alt_number(alt_label: str) -> int:
    """대안 레이블에서 번호를 추출합니다."""
    import re
    match = re.search(r'(\d+)', alt_label)
    return int(match.group(1)) if match else 0


if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # 전체 배치 실행
    report = run_batch()

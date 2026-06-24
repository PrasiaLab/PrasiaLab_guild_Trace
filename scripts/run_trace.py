# -*- coding: utf-8 -*-
"""
PrasiaLab_guild_Trace 통합 실행기.

이 파일 하나로 아래 작업을 순서대로 실행합니다.
1) 랭킹 JSON을 스냅샷으로 저장
2) 해당 스냅샷의 결사 점수 파일 생성
3) 이전/이후 스냅샷 비교 결과 생성

가장 기본 사용:
  python scripts/run_trace.py --snapshot-id 2026-06-25_1200

이전 스냅샷을 지정해서 바로 비교:
  python scripts/run_trace.py --snapshot-id 2026-06-25_1200 --before 2026-06-24_1800

이미 저장된 스냅샷끼리 비교만 실행:
  python scripts/run_trace.py --compare-only --before 2026-06-24_1800 --after 2026-06-25_1200

스냅샷 저장만 하고 비교는 생략:
  python scripts/run_trace.py --snapshot-id 2026-06-25_1200 --no-compare
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SNAPSHOT_DIR = ROOT / "data" / "snapshots"
MANIFEST = SNAPSHOT_DIR / "manifest.json"


def now_snapshot_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M")


def run_step(args: List[str], label: str) -> None:
    print(f"\n[STEP] {label}")
    print("[CMD]", " ".join(args))
    subprocess.check_call([sys.executable, *args], cwd=str(ROOT))


def read_manifest() -> list[dict[str, Any]]:
    if not MANIFEST.exists():
        return []
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return []
    snapshots = data.get("snapshots", [])
    return sorted([x for x in snapshots if x.get("id")], key=lambda x: x.get("id", ""))


def previous_snapshot_id(current_id: str) -> Optional[str]:
    ids = [x["id"] for x in read_manifest() if x.get("id")]
    ids = [x for x in ids if x != current_id]
    older = [x for x in ids if x < current_id]
    if older:
        return older[-1]
    if ids:
        return ids[-1]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="추적 연구소 작업을 한 번에 실행합니다.")
    parser.add_argument("--snapshot-id", default=None, help="이번에 저장할 스냅샷 ID. 예: 2026-06-25_1200")
    parser.add_argument("--guild-source", default="data/Who_are_you_guild_score.json", help="결사 랭킹 JSON 경로 또는 URL")
    parser.add_argument("--member-source", action="append", default=[], help="개인/직업 랭킹 JSON 경로 또는 URL. 여러 번 입력 가능")
    parser.add_argument("--before", default=None, help="비교할 이전 스냅샷 ID")
    parser.add_argument("--after", default=None, help="비교할 이후 스냅샷 ID. compare-only에서 주로 사용")
    parser.add_argument("--compare-only", action="store_true", help="스냅샷 저장 없이 기존 스냅샷끼리 비교만 실행")
    parser.add_argument("--no-compare", action="store_true", help="스냅샷 저장/점수 계산만 하고 비교는 실행하지 않음")
    parser.add_argument("--top-n", type=int, default=3, help="이전 결사별 후보 개수")
    parser.add_argument("--before-limit", type=int, default=200, help="비교할 이전 결사 순위 상한. 0이면 전체")
    parser.add_argument("--after-limit", type=int, default=300, help="비교할 이후 후보 결사 순위 상한. 0이면 전체")
    parser.add_argument("--min-score", type=float, default=35.0, help="출력 최소 유사도")
    args = parser.parse_args()

    snapshot_id = args.snapshot_id or now_snapshot_id()

    if args.compare_only:
        before_id = args.before
        after_id = args.after
        if not before_id or not after_id:
            raise SystemExit("compare-only는 --before 와 --after 를 모두 입력해야 합니다.")
    else:
        run_args = [
            str(SCRIPTS / "01_collect_snapshot.py"),
            "--snapshot-id", snapshot_id,
            "--guild-source", args.guild_source,
        ]
        for source in args.member_source:
            run_args.extend(["--member-source", source])
        run_step(run_args, "랭킹 데이터 스냅샷 저장")

        run_step([
            str(SCRIPTS / "02_build_guild_score.py"),
            "--snapshot-id", snapshot_id,
        ], "결사 점수 계산")

        if args.no_compare:
            print("\n[OK] 스냅샷 저장과 점수 계산만 완료했습니다.")
            return

        after_id = snapshot_id
        before_id = args.before or previous_snapshot_id(after_id)
        if not before_id:
            print("\n[WARN] 비교할 이전 스냅샷이 없습니다. 첫 스냅샷이면 정상입니다.")
            print("[OK] 다음 스냅샷 저장 후 다시 실행하면 비교 결과가 생성됩니다.")
            return

    run_step([
        str(SCRIPTS / "03_build_trace_compare.py"),
        "--before", before_id,
        "--after", after_id,
        "--top-n", str(args.top_n),
        "--before-limit", str(args.before_limit),
        "--after-limit", str(args.after_limit),
        "--min-score", str(args.min_score),
    ], f"스냅샷 비교 결과 생성: {before_id} → {after_id}")

    print("\n[DONE] 추적 연구소 데이터 생성 완료")
    print(f"- before: {before_id}")
    print(f"- after : {after_id}")
    print("- output: data/compare/latest.json")


if __name__ == "__main__":
    main()

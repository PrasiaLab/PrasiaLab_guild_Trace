# -*- coding: utf-8 -*-
"""
PrasiaLab_guild_Trace 통합 실행기.

일반 운영에서는 이 파일 하나만 실행하면 됩니다.

기본 사용:
  python scripts/run_trace.py --snapshot-id 2026-06-25_1200

이전 스냅샷 지정:
  python scripts/run_trace.py --snapshot-id 2026-06-25_1200 --before 2026-06-24_1800

저장된 스냅샷끼리 비교만:
  python scripts/run_trace.py --compare-only --before 2026-06-24_1800 --after 2026-06-25_1200

스냅샷 저장만:
  python scripts/run_trace.py --snapshot-id 2026-06-25_1150 --no-compare
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SNAPSHOT_DIR = ROOT / "data" / "snapshots"
MANIFEST = SNAPSHOT_DIR / "manifest.json"
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "run_trace.log"


def now_snapshot_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M")


def choose_python_executable() -> str:
    """Windows에서 pythonw.exe로 실행되면 자식 스크립트 오류가 안 보일 수 있어 python.exe를 우선 사용합니다."""
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        candidate = exe.with_name("python.exe")
        if candidate.exists():
            return str(candidate)
    return str(exe)


def append_log(text: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fp:
        fp.write(text + "\n")


def run_step(args: List[str], label: str) -> None:
    python_exe = choose_python_executable()
    cmd = [python_exe, *args]
    print(f"\n[STEP] {label}")
    print("[CMD]", " ".join(cmd))
    append_log(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] STEP: {label}")
    append_log("CMD: " + " ".join(cmd))

    try:
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        msg = f"[ERROR] Python 실행 파일을 찾지 못했습니다: {python_exe} / {exc}"
        print(msg)
        append_log(msg)
        raise SystemExit(1)

    if completed.stdout:
        print(completed.stdout.rstrip())
        append_log("STDOUT:\n" + completed.stdout.rstrip())
    if completed.stderr:
        print(completed.stderr.rstrip())
        append_log("STDERR:\n" + completed.stderr.rstrip())

    if completed.returncode != 0:
        msg = f"[ERROR] 단계 실패: {label} / exit code {completed.returncode}"
        print(msg)
        print(f"[LOG] 자세한 내용: {LOG_FILE}")
        append_log(msg)
        raise SystemExit(completed.returncode)


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


def source_exists_or_url(source: str) -> bool:
    if source.startswith("http://") or source.startswith("https://"):
        return True
    path = Path(source)
    if not path.is_absolute():
        path = ROOT / path
    return path.exists()


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

    print(f"[ROOT] {ROOT}")
    print(f"[PYTHON] {choose_python_executable()}")
    append_log("=" * 80)
    append_log(f"START: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    append_log(f"ROOT: {ROOT}")
    append_log(f"PYTHON: {choose_python_executable()}")

    snapshot_id = args.snapshot_id or now_snapshot_id()

    if args.compare_only:
        before_id = args.before
        after_id = args.after
        if not before_id or not after_id:
            raise SystemExit("compare-only는 --before 와 --after 를 모두 입력해야 합니다.")
    else:
        if not source_exists_or_url(args.guild_source):
            print(f"[ERROR] 결사 랭킹 원본을 찾지 못했습니다: {args.guild_source}")
            print("[CHECK] 압축 해제한 폴더의 data/Who_are_you_guild_score.json 파일이 있는지 확인해줘.")
            print("[TIP] 다른 파일명을 쓰는 경우 --guild-source data/파일명.json 으로 지정하면 돼.")
            raise SystemExit(1)

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

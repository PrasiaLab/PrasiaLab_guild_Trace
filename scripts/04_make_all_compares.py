# -*- coding: utf-8 -*-
"""저장된 스냅샷 조합 전체에 대해 비교 파일을 생성합니다."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "snapshots" / "manifest.json"
SCRIPT = ROOT / "scripts" / "03_build_trace_compare.py"


def main() -> None:
    if not MANIFEST.exists():
        raise FileNotFoundError("data/snapshots/manifest.json이 없습니다.")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ids = [x["id"] for x in manifest.get("snapshots", []) if x.get("id")]
    if len(ids) < 2:
        raise RuntimeError("비교하려면 스냅샷이 2개 이상 필요합니다.")
    for i, before in enumerate(ids):
        for after in ids[i + 1:]:
            print(f"[RUN] {before} -> {after}")
            subprocess.check_call([sys.executable, str(SCRIPT), "--before", before, "--after", after])


if __name__ == "__main__":
    main()

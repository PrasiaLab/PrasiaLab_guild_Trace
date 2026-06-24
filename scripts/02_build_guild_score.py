# -*- coding: utf-8 -*-
"""
스냅샷에서 결사 점수 파일을 생성합니다.

실행 예시:
  python scripts/02_build_guild_score.py --snapshot-id 2026-06-25_1200

출력:
  data/Who_are_you_guild_score.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

try:
    from config import DATA_DIR, LEVEL_SCORE_MAP, ROOT_DIR, SNAPSHOT_DIR
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from config import DATA_DIR, LEVEL_SCORE_MAP, ROOT_DIR, SNAPSHOT_DIR


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


def score_from_level_counts(level_counts: Dict[str, int]) -> int:
    total = 0
    for level, count in level_counts.items():
        total += int(count or 0) * int(LEVEL_SCORE_MAP.get(str(level), 0))
    return total


def fingerprint_decimal(guild: Dict[str, Any]) -> float:
    """동점 방지를 위한 아주 작은 보조 소수점."""
    level_class = guild.get("level_class_distribution") or {}
    class_seed = {
        "향사수": 1,
        "집행관": 2,
        "주문각인사": 3,
        "환영검사": 4,
        "심연추방자": 5,
        "야만투사": 6,
        "태양감시자": 7,
    }
    value = 0.0
    for level, classes in level_class.items():
        try:
            level_num = int(level)
        except ValueError:
            continue
        for class_name, count in (classes or {}).items():
            value += (level_num * 0.0001 + class_seed.get(class_name, 9) * 0.000001) * int(count or 0)
    return round(value, 6)


def latest_snapshot_id() -> str:
    manifest_path = SNAPSHOT_DIR / "manifest.json"
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        snapshots = manifest.get("snapshots") or []
        if snapshots:
            return snapshots[-1]["id"]
    raise FileNotFoundError("스냅샷을 찾을 수 없습니다. 01_collect_snapshot.py를 먼저 실행하세요.")


def main() -> None:
    parser = argparse.ArgumentParser(description="스냅샷 기반 결사 점수를 계산합니다.")
    parser.add_argument("--snapshot-id", default=None)
    parser.add_argument("--output", default="data/Who_are_you_guild_score.json")
    args = parser.parse_args()

    snapshot_id = args.snapshot_id or latest_snapshot_id()
    snapshot_path = SNAPSHOT_DIR / snapshot_id / "guilds.json"
    payload = read_json(snapshot_path)
    guilds: List[Dict[str, Any]] = payload.get("guilds") or []

    rankings = []
    for guild in guilds:
        level_counts = guild.get("level_counts") or guild.get("level_distribution") or {}
        base_score = score_from_level_counts(level_counts)
        score = base_score + fingerprint_decimal(guild)
        rankings.append({
            "world": guild.get("server"),
            "world_group_id": guild.get("world_group_id", ""),
            "world_id": guild.get("world_id", ""),
            "guild_name": guild.get("guild_name"),
            "guild_master": guild.get("guild_master"),
            "guild_level": guild.get("guild_level"),
            "guild_member_count": guild.get("guild_member_count"),
            "max_guild_member_count": guild.get("max_guild_member_count"),
            "ranked_member_count": guild.get("guild_member_count"),
            "scored_member_count": sum(int(v or 0) for v in level_counts.values()),
            "level_counts": level_counts,
            "score": score,
            "previous_score": guild.get("guild_score", score),
            "previous_rank": guild.get("guild_rank"),
        })

    rankings.sort(key=lambda x: (-float(x.get("score") or 0), int(x.get("previous_rank") or 999999)))
    for idx, item in enumerate(rankings, 1):
        item["rank"] = idx
        if item.get("previous_rank"):
            item["rank_change"] = int(item["previous_rank"]) - idx
        else:
            item["rank_change"] = 0
        item["score_change"] = round(float(item["score"] or 0) - float(item.get("previous_score") or 0), 6)
        item["is_new"] = False

    out_path = ROOT_DIR / args.output
    write_json(out_path, {
        "metadata": {
            "snapshot_id": snapshot_id,
            "source": str(snapshot_path.relative_to(ROOT_DIR)),
            "total_guilds": len(rankings),
            "note": "91+ 및 레벨별 직업군 보조 소수점이 포함될 수 있습니다.",
        },
        "level_score_map": LEVEL_SCORE_MAP,
        "rankings": rankings,
    })
    print(f"[OK] guild score saved: {out_path}")
    print(f"[OK] guild count: {len(rankings):,}")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
랭킹 데이터를 스냅샷으로 저장하는 스크립트.

우선 로컬 JSON을 기준으로 동작하게 구성했습니다.
- 결사 랭킹 JSON: data/Who_are_you_guild_score.json 또는 data/Who_are_you_guild.json
- 개인/직업별 랭킹 JSON: 선택 입력. 있으면 결사별 91+ 멤버/직업군 분포를 더 정확히 생성합니다.

실행 예시:
  python scripts/01_collect_snapshot.py --snapshot-id 2026-06-25_1200
  python scripts/01_collect_snapshot.py --guild-source data/Who_are_you_guild_score.json --member-source data/Who_are_you.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.request import Request, urlopen

try:
    from config import CLASS_ALIASES, DATA_DIR, HIGH_LEVEL_MIN, ROOT_DIR, SNAPSHOT_DIR
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from config import CLASS_ALIASES, DATA_DIR, HIGH_LEVEL_MIN, ROOT_DIR, SNAPSHOT_DIR


def now_snapshot_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M")


def read_json(source: str | Path) -> Any:
    source_text = str(source)
    if source_text.startswith("http://") or source_text.startswith("https://"):
        req = Request(source_text, headers={"User-Agent": "PrasiaLabGuildTrace/1.0"})
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    path = Path(source)
    if not path.is_absolute():
        path = ROOT_DIR / path
    if not path.exists():
        raise FileNotFoundError(f"JSON 원본 파일을 찾지 못했습니다: {path}")
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


def pick(obj: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            return obj[key]
    return default


def normalize_class(value: Any) -> str:
    text = str(value or "").strip()
    return CLASS_ALIASES.get(text, text or "미확인")


def as_list(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("rankings", "data", "items", "guilds", "characters", "ranking"):
        value = payload.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    return []


def server_value(item: Dict[str, Any]) -> str:
    return str(pick(item, "server", "world", "world_name", "server_name", "world_id", default="-")).strip()


def guild_key(server: str, guild_name: str, guild_master: str = "") -> str:
    return "|".join([server.strip().lower(), guild_name.strip().lower(), guild_master.strip().lower()])


def fallback_key(guild_name: str, guild_master: str = "") -> str:
    return "|".join([guild_name.strip().lower(), guild_master.strip().lower()])


def normalize_guild(item: Dict[str, Any], index: int) -> Dict[str, Any]:
    level_counts = pick(item, "level_counts", "level_distribution", default={}) or {}
    level_counts = {str(k): int(v or 0) for k, v in level_counts.items() if str(k).isdigit() and int(v or 0) > 0}

    return {
        "server": server_value(item),
        "world_group_id": pick(item, "world_group_id", default=""),
        "world_id": pick(item, "world_id", default=""),
        "guild_name": str(pick(item, "guild_name", "guild", "guildName", default="-")).strip(),
        "guild_master": str(pick(item, "guild_master", "master", "master_name", "guildMaster", default="-")).strip(),
        "guild_rank": int(pick(item, "rank", "guild_rank", "previous_rank", default=index + 1) or index + 1),
        "guild_score": float(pick(item, "score", "guild_score", "previous_score", default=0) or 0),
        "guild_level": pick(item, "guild_level", default=None),
        "guild_member_count": pick(item, "guild_member_count", "member_count", default=None),
        "max_guild_member_count": pick(item, "max_guild_member_count", default=None),
        "level_counts": level_counts,
        "members": [],
    }


def normalize_member(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    guild_name = str(pick(item, "guild_name", "guild", "guildName", default="")).strip()
    if not guild_name:
        return None
    level_raw = pick(item, "level", "character_level", "gc_level", default=0)
    try:
        level = int(float(level_raw))
    except (TypeError, ValueError):
        level = 0

    return {
        "server": server_value(item),
        "guild_name": guild_name,
        "guild_master": str(pick(item, "guild_master", "master", "master_name", default="")).strip(),
        "nickname": str(pick(item, "nickname", "name", "character_name", "gc_name", default="-")).strip(),
        "level": level,
        "class": normalize_class(pick(item, "class", "class_name", "job", "character_class", "classCode", default="")),
        "rank": pick(item, "rank", default=None),
    }


def attach_members(guilds: List[Dict[str, Any]], members: Iterable[Dict[str, Any]]) -> None:
    by_key: Dict[str, Dict[str, Any]] = {}
    by_fallback: Dict[str, Dict[str, Any]] = {}
    for guild in guilds:
        by_key[guild_key(guild["server"], guild["guild_name"], guild["guild_master"])] = guild
        by_fallback[fallback_key(guild["guild_name"], guild["guild_master"])] = guild
        by_fallback[fallback_key(guild["guild_name"])] = guild

    for member in members:
        normalized = normalize_member(member)
        if not normalized:
            continue
        candidates = [
            guild_key(normalized["server"], normalized["guild_name"], normalized.get("guild_master", "")),
            fallback_key(normalized["guild_name"], normalized.get("guild_master", "")),
            fallback_key(normalized["guild_name"]),
        ]
        guild = None
        for key in candidates:
            guild = by_key.get(key) or by_fallback.get(key)
            if guild:
                break
        if guild:
            normalized["is_master"] = normalized["nickname"] == guild.get("guild_master")
            guild["members"].append(normalized)


def build_profile(guild: Dict[str, Any]) -> Dict[str, Any]:
    members = [m for m in guild.get("members", []) if int(m.get("level") or 0) >= HIGH_LEVEL_MIN]
    members.sort(key=lambda m: (int(m.get("level") or 0), str(m.get("class") or ""), str(m.get("nickname") or "")), reverse=True)

    level_distribution = Counter()
    class_distribution = Counter()
    level_class_distribution: Dict[str, Counter] = defaultdict(Counter)

    if members:
        for member in members:
            level = str(member.get("level"))
            cls = normalize_class(member.get("class"))
            level_distribution[level] += 1
            class_distribution[cls] += 1
            level_class_distribution[level][cls] += 1
    else:
        # 멤버 원본이 없을 때는 결사 랭킹의 레벨 카운트라도 사용합니다.
        for level, count in (guild.get("level_counts") or {}).items():
            if int(level) >= HIGH_LEVEL_MIN:
                level_distribution[str(level)] += int(count or 0)

    high_level_count = sum(level_distribution.values())
    max_level = max([int(x) for x in level_distribution.keys()], default=None)

    return {
        "high_level_count": high_level_count,
        "max_level": max_level,
        "level_distribution": dict(sorted(level_distribution.items(), key=lambda x: int(x[0]), reverse=True)),
        "class_distribution": dict(class_distribution.most_common()),
        "level_class_distribution": {
            level: dict(counter.most_common())
            for level, counter in sorted(level_class_distribution.items(), key=lambda x: int(x[0]), reverse=True)
        },
        "members": members,
    }


def load_members(paths: List[str]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for source in paths:
        if not source:
            continue
        payload = read_json(source)
        merged.extend(as_list(payload))
    return merged


def update_manifest(snapshot_id: str, created_at: str) -> None:
    manifest_path = SNAPSHOT_DIR / "manifest.json"
    manifest = {"snapshots": []}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    snapshots = [x for x in manifest.get("snapshots", []) if x.get("id") != snapshot_id]
    snapshots.append({"id": snapshot_id, "label": created_at, "created_at": created_at})
    snapshots.sort(key=lambda x: x.get("id", ""))
    write_json(manifest_path, {"snapshots": snapshots})


def main() -> None:
    parser = argparse.ArgumentParser(description="랭킹 데이터를 추적 연구소 스냅샷으로 저장합니다.")
    parser.add_argument("--snapshot-id", default=now_snapshot_id(), help="예: 2026-06-25_1200")
    parser.add_argument("--guild-source", default="data/Who_are_you_guild_score.json", help="결사 랭킹 JSON 경로 또는 URL")
    parser.add_argument("--member-source", action="append", default=[], help="개인/직업 랭킹 JSON 경로 또는 URL. 여러 번 입력 가능")
    args = parser.parse_args()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    guild_payload = read_json(args.guild_source)
    guilds = [normalize_guild(item, idx) for idx, item in enumerate(as_list(guild_payload))]

    default_member_sources = ["data/Who_are_you.json", "data/Who_are_you_class.json"]
    member_sources = args.member_source or [src for src in default_member_sources if (ROOT_DIR / src).exists()]
    if member_sources:
        attach_members(guilds, load_members(member_sources))

    for guild in guilds:
        guild.update(build_profile(guild))

    out_dir = SNAPSHOT_DIR / args.snapshot_id
    write_json(out_dir / "guilds.json", {
        "meta": {
            "snapshot_id": args.snapshot_id,
            "created_at": created_at,
            "high_level_min": HIGH_LEVEL_MIN,
            "guild_count": len(guilds),
            "member_sources": member_sources,
        },
        "guilds": guilds,
    })
    write_json(out_dir / "snapshot_info.json", {
        "snapshot_id": args.snapshot_id,
        "created_at": created_at,
        "guild_count": len(guilds),
        "high_level_min": HIGH_LEVEL_MIN,
    })
    write_json(DATA_DIR / "latest" / "guilds.json", {"meta": {"snapshot_id": args.snapshot_id, "created_at": created_at}, "guilds": guilds})
    update_manifest(args.snapshot_id, created_at)
    print(f"[OK] snapshot saved: {out_dir}")
    print(f"[OK] guild count: {len(guilds):,}")


if __name__ == "__main__":
    main()

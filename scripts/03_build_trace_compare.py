# -*- coding: utf-8 -*-
"""
두 스냅샷을 비교해 추적 연구소용 비교 결과를 생성합니다.

실행 예시:
  python scripts/03_build_trace_compare.py --before 2026-06-24_1200 --after 2026-06-25_1200
  python scripts/03_build_trace_compare.py --before 2026-06-24_1200 --after 2026-06-25_1200 --top-n 3

출력:
  data/compare/<before>__<after>.json
  data/compare/latest.json
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

try:
    from config import COMPARE_DIR, DATA_DIR, HIGH_LEVEL_MIN, SNAPSHOT_DIR, TRACE_WEIGHTS, normalize_server_name
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from config import COMPARE_DIR, DATA_DIR, HIGH_LEVEL_MIN, SNAPSHOT_DIR, TRACE_WEIGHTS, normalize_server_name


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


def normalize(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "")


def vector_similarity(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    keys = set((a or {}).keys()) | set((b or {}).keys())
    if not keys:
        return 0.0
    diff = 0.0
    total = 0.0
    for key in keys:
        av = float((a or {}).get(key) or 0)
        bv = float((b or {}).get(key) or 0)
        diff += abs(av - bv)
        total += max(av, bv)
    if total <= 0:
        return 0.0
    return max(0.0, 1.0 - diff / total)


def flatten_level_class(value: Dict[str, Dict[str, int]]) -> Dict[str, int]:
    flattened = {}
    for level, classes in (value or {}).items():
        for class_name, count in (classes or {}).items():
            flattened[f"{level}:{class_name}"] = int(count or 0)
    return flattened


def count_similarity(a: int | float, b: int | float) -> float:
    a = float(a or 0)
    b = float(b or 0)
    if a <= 0 and b <= 0:
        return 0.0
    return max(0.0, 1.0 - abs(a - b) / max(a, b, 1.0))


def score_closeness(a: float, b: float) -> float:
    a = float(a or 0)
    b = float(b or 0)
    if a <= 0 and b <= 0:
        return 0.0
    gap = abs(a - b) / max(a, b, 1.0)
    # 0% 차이 = 1.0, 30% 이상 차이 = 0.0
    return max(0.0, 1.0 - gap / 0.30)


def master_similarity(a: str, b: str) -> float:
    na = normalize(a)
    nb = normalize(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.55
    return 0.0


def name_bonus(a: str, b: str) -> float:
    na = normalize(a)
    nb = normalize(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.45
    return 0.0


def grade(score: float) -> str:
    if score >= 85:
        return "매우 유력"
    if score >= 70:
        return "유력"
    if score >= 55:
        return "가능성 있음"
    return "낮음"


def compare_pair(before: Dict[str, Any], after: Dict[str, Any]) -> Tuple[float, Dict[str, float], List[str]]:
    weights = TRACE_WEIGHTS
    scores = {
        "master": master_similarity(before.get("guild_master"), after.get("guild_master")) * weights["master"],
        "level_class_distribution": vector_similarity(
            flatten_level_class(before.get("level_class_distribution") or {}),
            flatten_level_class(after.get("level_class_distribution") or {}),
        ) * weights["level_class_distribution"],
        "level_distribution": vector_similarity(before.get("level_distribution") or {}, after.get("level_distribution") or {}) * weights["level_distribution"],
        "class_distribution": vector_similarity(before.get("class_distribution") or {}, after.get("class_distribution") or {}) * weights["class_distribution"],
        "high_level_count": count_similarity(before.get("high_level_count"), after.get("high_level_count")) * weights["high_level_count"],
        "guild_score_closeness": score_closeness(before.get("guild_score"), after.get("guild_score")) * weights["guild_score_closeness"],
        "guild_name_bonus": name_bonus(before.get("guild_name"), after.get("guild_name")) * weights["guild_name_bonus"],
    }
    total = round(sum(scores.values()), 2)
    evidence = []
    if scores["master"] >= weights["master"] * 0.9:
        evidence.append("결사장 일치")
    if scores["level_class_distribution"] >= weights["level_class_distribution"] * 0.75:
        evidence.append("91+ 레벨/직업 유사")
    if scores["level_distribution"] >= weights["level_distribution"] * 0.75:
        evidence.append("91+ 레벨 분포 유사")
    if scores["class_distribution"] >= weights["class_distribution"] * 0.75:
        evidence.append("직업군 분포 유사")
    if scores["guild_score_closeness"] >= weights["guild_score_closeness"] * 0.7:
        evidence.append("기존 점수 근접")
    if scores["guild_name_bonus"] >= weights["guild_name_bonus"] * 0.9:
        evidence.append("결사명 일치")
    if not evidence:
        evidence.append("부분 유사")
    return total, {k: round(v, 2) for k, v in scores.items()}, evidence


def load_snapshot(snapshot_id: str) -> Dict[str, Any]:
    path = SNAPSHOT_DIR / snapshot_id / "guilds.json"
    if not path.exists():
        raise FileNotFoundError(f"스냅샷 파일 없음: {path}")
    return read_json(path)


def dedupe_members(members: List[Dict[str, Any]], master_name: str = "") -> List[Dict[str, Any]]:
    seen = set()
    rows = []
    master_key = str(master_name or "").strip().lower()
    for member in members or []:
        nickname = str(member.get("nickname") or member.get("name") or "-").strip()
        row = dict(member)
        row["nickname"] = nickname
        row["is_master"] = bool(row.get("is_master")) or (bool(master_key) and nickname.lower() == master_key)
        key = "|".join([nickname.lower(), str(row.get("level") or ""), str(row.get("class") or row.get("class_name") or "").strip().lower()])
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    rows.sort(key=lambda m: (not bool(m.get("is_master")), -int(m.get("level") or 0), str(m.get("nickname") or "")))
    return rows

def compact_guild(guild: Dict[str, Any]) -> Dict[str, Any]:
    members = dedupe_members(guild.get("members") or [], guild.get("guild_master") or "")
    return {
        "server": normalize_server_name(guild.get("server")),
        "guild_name": guild.get("guild_name"),
        "guild_master": guild.get("guild_master"),
        "guild_rank": guild.get("guild_rank"),
        "guild_score": guild.get("guild_score"),
        "high_level_count": guild.get("high_level_count"),
        "level_distribution": guild.get("level_distribution") or {},
        "class_distribution": guild.get("class_distribution") or {},
        "level_class_distribution": guild.get("level_class_distribution") or {},
        "members": members,
    }


def snapshot_options() -> List[Dict[str, str]]:
    manifest_path = SNAPSHOT_DIR / "manifest.json"
    if not manifest_path.exists():
        return []
    manifest = read_json(manifest_path)
    return [
        {"id": item.get("id"), "label": item.get("label") or item.get("created_at") or item.get("id")}
        for item in manifest.get("snapshots", [])
        if item.get("id")
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="스냅샷 2개를 비교해 추적 연구소 결과 JSON을 생성합니다.")
    parser.add_argument("--before", required=True, help="이전 스냅샷 ID")
    parser.add_argument("--after", required=True, help="이후 스냅샷 ID")
    parser.add_argument("--top-n", type=int, default=3, help="이전 결사별 후보 개수")
    parser.add_argument("--before-limit", type=int, default=200, help="비교할 이전 결사 순위 상한. 0이면 전체")
    parser.add_argument("--after-limit", type=int, default=300, help="비교할 이후 후보 결사 순위 상한. 0이면 전체")
    parser.add_argument("--min-score", type=float, default=35.0, help="출력 최소 유사도")
    args = parser.parse_args()

    before_payload = load_snapshot(args.before)
    after_payload = load_snapshot(args.after)
    before_guilds = sorted(before_payload.get("guilds") or [], key=lambda g: int(g.get("guild_rank") or 999999))
    after_guilds = sorted(after_payload.get("guilds") or [], key=lambda g: int(g.get("guild_rank") or 999999))
    if args.before_limit and args.before_limit > 0:
        before_guilds = before_guilds[: args.before_limit]
    if args.after_limit and args.after_limit > 0:
        after_guilds = after_guilds[: args.after_limit]

    matches: List[Dict[str, Any]] = []
    for before_index, before in enumerate(before_guilds, 1):
        candidates = []
        for after in after_guilds:
            total, scores, evidence = compare_pair(before, after)
            if total >= args.min_score:
                candidates.append((total, after, scores, evidence))
        candidates.sort(key=lambda item: (-item[0], int(item[1].get("guild_rank") or 999999)))
        for candidate_index, (total, after, scores, evidence) in enumerate(candidates[: args.top_n], 1):
            matches.append({
                "id": f"{args.before}-{before_index:04d}-{candidate_index}",
                "similarity": total,
                "grade": grade(total),
                "before": compact_guild(before),
                "after": compact_guild(after),
                "scores": scores,
                "evidence": evidence,
            })

    matches.sort(key=lambda m: (int(m["before"].get("guild_rank") or 999999), -float(m.get("similarity") or 0)))

    result = {
        "meta": {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "before_snapshot": args.before,
            "after_snapshot": args.after,
            "high_level_min": HIGH_LEVEL_MIN,
            "available_snapshots": snapshot_options(),
            "before_guild_count": len(before_guilds),
            "after_guild_count": len(after_guilds),
        },
        "weights": TRACE_WEIGHTS,
        "matches": matches,
    }

    out_path = COMPARE_DIR / f"{args.before}__{args.after}.json"
    write_json(out_path, result)
    write_json(COMPARE_DIR / "latest.json", result)
    print(f"[OK] compare saved: {out_path}")
    print(f"[OK] matches: {len(matches):,}")


if __name__ == "__main__":
    main()

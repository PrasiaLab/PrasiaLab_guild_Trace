"""
PrasiaLab_guild_Trace 비교 로직 초안

역할:
- before/after 스냅샷 JSON을 읽는다.
- 결사장, 91+ 레벨/직업군 분포, 결사순위 점수 근접도, 결사명 보너스로 유사도를 계산한다.
- data/compare/latest.json 형태로 저장한다.

주의:
- 일반 결사원 닉네임은 비교 기준에서 제외한다.
- 결사명은 필수 조건이 아니라 보너스 조건으로만 사용한다.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

WEIGHTS = {
    "master": 25,
    "level_class_distribution": 25,
    "level_distribution": 15,
    "class_distribution": 15,
    "high_level_count": 10,
    "guild_score_closeness": 7,
    "guild_name_bonus": 3,
}


def normalize_name(value: Any) -> str:
    return str(value or "").strip().replace(" ", "").lower()


def dict_similarity(before: Dict[str, int], after: Dict[str, int], weight: float) -> float:
    """두 분포의 유사도. 완전 동일이면 weight, 완전 불일치에 가까우면 0."""
    keys = set(before or {}) | set(after or {})
    if not keys:
        return 0.0

    diff = sum(abs(int(before.get(key, 0)) - int(after.get(key, 0))) for key in keys)
    base = max(sum(int(v) for v in before.values()), sum(int(v) for v in after.values()), 1)
    score = max(0.0, 1.0 - (diff / base)) * weight
    return round(score, 3)


def nested_distribution_similarity(before: Dict[str, Dict[str, int]], after: Dict[str, Dict[str, int]], weight: float) -> float:
    levels = set(before or {}) | set(after or {})
    if not levels:
        return 0.0

    total_score = 0.0
    total_weight = 0.0
    for level in levels:
        # 높은 레벨일수록 조금 더 비중을 둔다.
        level_weight = max(float(level), 1.0)
        total_score += dict_similarity(before.get(level, {}), after.get(level, {}), 1.0) * level_weight
        total_weight += level_weight

    return round((total_score / total_weight) * weight if total_weight else 0.0, 3)


def count_similarity(before_count: int, after_count: int, weight: float) -> float:
    base = max(int(before_count or 0), int(after_count or 0), 1)
    diff = abs(int(before_count or 0) - int(after_count or 0))
    return round(max(0.0, 1.0 - diff / base) * weight, 3)


def score_closeness(before_score: float, after_score: float, weight: float) -> float:
    base = max(abs(float(before_score or 0)), abs(float(after_score or 0)), 1.0)
    ratio = abs(float(before_score or 0) - float(after_score or 0)) / base
    # 10% 차이까지는 완만하게, 그 이상은 빠르게 낮아지도록 처리
    normalized = max(0.0, 1.0 - min(ratio / 0.10, 1.0))
    return round(normalized * weight, 3)


def grade(score: float) -> str:
    if score >= 85:
        return "매우 유력"
    if score >= 70:
        return "유력"
    if score >= 55:
        return "가능성 있음"
    return "낮음"


def evidence(before: Dict[str, Any], after: Dict[str, Any], scores: Dict[str, float]) -> List[str]:
    result: List[str] = []
    if scores.get("master", 0) > 0:
        result.append("결사장 일치")
    else:
        result.append("결사장 불일치")

    if scores.get("level_class_distribution", 0) >= WEIGHTS["level_class_distribution"] * 0.75:
        result.append("91+ 전력 구조 유사")
    if scores.get("guild_score_closeness", 0) >= WEIGHTS["guild_score_closeness"] * 0.7:
        result.append("결사점수 근접")
    if scores.get("guild_name_bonus", 0) > 0:
        result.append("결사명 보너스")
    else:
        result.append("결사명 변경 가능성")

    return result


def compare_pair(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    before_profile = before.get("high_level_profile", {})
    after_profile = after.get("high_level_profile", {})

    scores = {
        "master": WEIGHTS["master"] if normalize_name(before.get("guild_master")) == normalize_name(after.get("guild_master")) else 0,
        "level_class_distribution": nested_distribution_similarity(
            before_profile.get("level_class_distribution", {}),
            after_profile.get("level_class_distribution", {}),
            WEIGHTS["level_class_distribution"],
        ),
        "level_distribution": dict_similarity(before_profile.get("level_distribution", {}), after_profile.get("level_distribution", {}), WEIGHTS["level_distribution"]),
        "class_distribution": dict_similarity(before_profile.get("class_distribution", {}), after_profile.get("class_distribution", {}), WEIGHTS["class_distribution"]),
        "high_level_count": count_similarity(before_profile.get("count", 0), after_profile.get("count", 0), WEIGHTS["high_level_count"]),
        "guild_score_closeness": score_closeness(before.get("guild_score", 0), after.get("guild_score", 0), WEIGHTS["guild_score_closeness"]),
        "guild_name_bonus": WEIGHTS["guild_name_bonus"] if normalize_name(before.get("guild_name")) == normalize_name(after.get("guild_name")) else 0,
    }
    total = round(sum(scores.values()), 3)

    return {
        "id": f"{before.get('server','')}-{before.get('guild_name','')}__{after.get('server','')}-{after.get('guild_name','')}",
        "similarity": total,
        "grade": grade(total),
        "before": flatten_guild(before),
        "after": flatten_guild(after),
        "scores": scores,
        "evidence": evidence(before, after, scores),
    }


def flatten_guild(guild: Dict[str, Any]) -> Dict[str, Any]:
    profile = guild.get("high_level_profile", {})
    return {
        "server": guild.get("server"),
        "guild_name": guild.get("guild_name"),
        "guild_master": guild.get("guild_master"),
        "guild_rank": guild.get("guild_rank"),
        "guild_score": guild.get("guild_score"),
        "high_level_count": profile.get("count", 0),
        "level_distribution": profile.get("level_distribution", {}),
        "class_distribution": profile.get("class_distribution", {}),
        "level_class_distribution": profile.get("level_class_distribution", {}),
    }


def load_guilds(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data.get("guilds", [])
    if isinstance(data, list):
        return data
    return []


def build_matches(before_guilds: Iterable[Dict[str, Any]], after_guilds: Iterable[Dict[str, Any]], top_n: int) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for before in before_guilds:
        candidates = [compare_pair(before, after) for after in after_guilds]
        candidates.sort(key=lambda item: item["similarity"], reverse=True)
        results.extend(candidates[:top_n])

    results.sort(key=lambda item: item["similarity"], reverse=True)
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True, help="이전 스냅샷 guilds.json")
    parser.add_argument("--after", required=True, help="이후 스냅샷 guilds.json")
    parser.add_argument("--out", default="data/compare/latest.json")
    parser.add_argument("--top-n", type=int, default=3, help="이전 결사별 후보 보존 개수")
    args = parser.parse_args()

    before_path = Path(args.before)
    after_path = Path(args.after)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    before_guilds = load_guilds(before_path)
    after_guilds = load_guilds(after_path)

    payload = {
        "meta": {
            "title": "추적 연구소 비교 결과",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "before_snapshot": before_path.parent.name,
            "after_snapshot": after_path.parent.name,
            "description": "공개 랭킹 데이터 기반 유사성 추론 결과입니다.",
        },
        "weights": WEIGHTS,
        "matches": build_matches(before_guilds, after_guilds, args.top_n),
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()

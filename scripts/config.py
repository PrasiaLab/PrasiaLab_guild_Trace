# -*- coding: utf-8 -*-
"""PrasiaLab Guild Trace 공통 설정."""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
COMPARE_DIR = DATA_DIR / "compare"

HIGH_LEVEL_MIN = 91

# 기존 꼬꼬 페이지 기준 점수 계산용 기본값.
# 필요하면 숫자만 조정하면 됩니다.
LEVEL_SCORE_MAP = {
    "93": 1000,
    "92": 300,
    "91": 100,
    "90": 25,
    "89": 10,
    "88": 5,
    "87": 2,
}

CLASS_ORDER = [
    "향사수",
    "집행관",
    "주문각인사",
    "환영검사",
    "심연추방자",
    "야만투사",
    "태양감시자",
]

CLASS_ALIASES = {
    "IncenseArcher": "향사수",
    "Enforcer": "집행관",
    "RuneScribe": "주문각인사",
    "MirageBlade": "환영검사",
    "AbyssRevenant": "심연추방자",
    "WildWarrior": "야만투사",
    "SolarSentinel": "태양감시자",
}

TRACE_WEIGHTS = {
    "master": 25,
    "level_class_distribution": 25,
    "level_distribution": 15,
    "class_distribution": 15,
    "high_level_count": 10,
    "guild_score_closeness": 7,
    "guild_name_bonus": 3,
}

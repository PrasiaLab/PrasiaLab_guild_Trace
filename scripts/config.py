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

SERVER_ALIASES = {
    "2-1": "론도01", "2-2": "론도02", "2-3": "론도03", "2-4": "론도04", "2-5": "론도05",
    "3-1": "라인소프01", "3-2": "라인소프02", "3-3": "라인소프03", "3-4": "라인소프04", "3-5": "라인소프05",
    "5-1": "아민타01", "5-2": "아민타02", "5-3": "아민타03", "5-4": "아민타04", "5-5": "아민타05",
    "8-1": "가리안01", "8-2": "가리안02", "8-3": "가리안03", "8-4": "가리안04", "8-5": "가리안05",
    "16-1": "타리아01", "16-2": "타리아02", "16-3": "타리아03", "16-4": "타리아04", "16-5": "타리아05",
    "11-1": "제롬01", "11-2": "제롬02", "11-3": "제롬03", "11-4": "제롬04", "11-5": "제롬05",
    "14-1": "나세르01", "14-2": "나세르02", "14-3": "나세르03", "14-4": "나세르04", "14-5": "나세르05",
    "10-1": "사도바01", "10-2": "사도바02", "10-3": "사도바03", "10-4": "사도바04", "10-5": "사도바05",
    "12-1": "아티산01", "12-2": "아티산02", "12-3": "아티산03", "12-4": "아티산04", "12-5": "아티산05",
    "27-1": "메르비스01", "27-2": "메르비스02", "27-3": "메르비스03", "27-4": "메르비스04", "27-5": "메르비스05",
}


def normalize_server_name(value):
    text = str(value or "").strip()
    if not text or text == "-":
        return "-"
    if text in SERVER_ALIASES:
        return SERVER_ALIASES[text]
    return text

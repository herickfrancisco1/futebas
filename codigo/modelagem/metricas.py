"""Small, well-named metric functions used by the dashboard's KPI cards.

Kept separate from ``prepare.py`` (table shaping) so each metric shown in
a ``st.metric`` widget has a single, testable source of truth.
"""
from __future__ import annotations

import pandas as pd


def pass_accuracy(passes: pd.DataFrame) -> float:
    if len(passes) == 0:
        return 0.0
    return float(passes["completed"].sum()) / len(passes)


def shot_conversion_rate(shots: pd.DataFrame) -> float:
    if len(shots) == 0:
        return 0.0
    return float(shots["is_goal"].sum()) / len(shots)


def player_pass_stats(passes: pd.DataFrame, player: str) -> dict:
    p = passes[passes["player"] == player]
    total = len(p)
    completed = int(p["completed"].sum()) if total else 0
    return {
        "player": player,
        "total_passes": total,
        "completed_passes": completed,
        "accuracy": completed / total if total else 0.0,
    }


def player_shot_stats(shots: pd.DataFrame, player: str) -> dict:
    s = shots[shots["player"] == player]
    total = len(s)
    goals = int(s["is_goal"].sum()) if total else 0
    avg_xg = float(s["shot_statsbomb_xg"].mean()) if total and "shot_statsbomb_xg" in s.columns else 0.0
    return {
        "player": player,
        "total_shots": total,
        "goals": goals,
        "conversion": goals / total if total else 0.0,
        "avg_xg": avg_xg,
    }

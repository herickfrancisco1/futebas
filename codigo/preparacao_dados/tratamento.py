"""Cleaning and shaping helpers that turn raw StatsBomb events into the
tidy tables the dashboard's visualizations expect.
"""
from __future__ import annotations

import pandas as pd

EVENT_DISPLAY_COLUMNS = [
    "minute",
    "second",
    "team",
    "player",
    "type",
    "location",
    "pass_recipient",
    "pass_outcome",
    "shot_outcome",
    "shot_statsbomb_xg",
]


def split_location(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Expand a StatsBomb ``[x, y]`` location column into two float columns."""
    if col not in df.columns:
        return df
    df = df.copy()

    def _coord(value, index):
        if isinstance(value, list) and len(value) > index:
            return value[index]
        return None

    df[f"{col}_x"] = df[col].apply(lambda v: _coord(v, 0))
    df[f"{col}_y"] = df[col].apply(lambda v: _coord(v, 1))
    return df


def get_passes(events: pd.DataFrame) -> pd.DataFrame:
    """Completed and incomplete passes, with start/end coordinates split out."""
    passes = events[events["type"] == "Pass"].copy()
    passes = split_location(passes, "location")
    passes = split_location(passes, "pass_end_location")
    passes["completed"] = passes["pass_outcome"].isna()
    return passes


def get_shots(events: pd.DataFrame, include_shootout: bool = False) -> pd.DataFrame:
    """Shots, with start/end coordinates split out and a goal flag.

    StatsBomb tags a penalty shootout as ``period == 5``. Those kicks are not
    part of open play, so they are excluded from shot/goal statistics by
    default to keep "goals in the match" matching the actual scoreline.
    """
    shots = events[events["type"] == "Shot"].copy()
    if not include_shootout and "period" in shots.columns:
        shots = shots[shots["period"] != 5]
    shots = split_location(shots, "location")
    shots = split_location(shots, "shot_end_location")
    shots["is_goal"] = shots["shot_outcome"] == "Goal"
    return shots


def team_names(match_row: pd.Series) -> tuple[str, str]:
    return match_row["home_team"], match_row["away_team"]


def match_basic_stats(events: pd.DataFrame, home_team: str, away_team: str) -> pd.DataFrame:
    """One row per team with goals, shots and passes for a single match."""
    shots = get_shots(events)
    passes = get_passes(events)
    rows = []
    for team in (home_team, away_team):
        team_shots = shots[shots["team"] == team]
        team_passes = passes[passes["team"] == team]
        rows.append(
            {
                "team": team,
                "goals": int(team_shots["is_goal"].sum()),
                "shots": int(len(team_shots)),
                "passes": int(len(team_passes)),
                "passes_completed": int(team_passes["completed"].sum()),
            }
        )
    return pd.DataFrame(rows)


def events_table(events: pd.DataFrame) -> pd.DataFrame:
    """Slim, readable view of the raw event stream for the data explorer tab."""
    cols = [c for c in EVENT_DISPLAY_COLUMNS if c in events.columns]
    table = events[cols].copy()
    if "location" in table.columns:
        table["location"] = table["location"].apply(
            lambda v: f"({v[0]:.1f}, {v[1]:.1f})" if isinstance(v, list) else None
        )
    return table.sort_values(["minute", "second"], na_position="last").reset_index(drop=True)


def stage_team_aggregate(events: pd.DataFrame) -> pd.DataFrame:
    """One row per team per match: goals, shots and passes.

    Expects ``events`` to already carry ``match_id``, ``home_team`` and
    ``away_team`` columns, as produced by
    ``data_loader.load_events_for_matches``.
    """
    shots = get_shots(events)
    passes = get_passes(events)
    rows = []
    for match_id, match_events in events.groupby("match_id"):
        home_team = match_events["home_team"].iloc[0]
        away_team = match_events["away_team"].iloc[0]
        stage = match_events["competition_stage"].iloc[0]
        match_shots = shots[shots["match_id"] == match_id]
        match_passes = passes[passes["match_id"] == match_id]
        for team in (home_team, away_team):
            team_shots = match_shots[match_shots["team"] == team]
            team_passes = match_passes[match_passes["team"] == team]
            rows.append(
                {
                    "match_id": match_id,
                    "stage": stage,
                    "team": team,
                    "goals": int(team_shots["is_goal"].sum()),
                    "shots": int(len(team_shots)),
                    "passes": int(len(team_passes)),
                    "passes_completed": int(team_passes["completed"].sum()),
                }
            )
    return pd.DataFrame(rows)


def top_players(events: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Goals + completed passes per player, across all matches in ``events``."""
    shots = get_shots(events)
    passes = get_passes(events)

    goals = shots[shots["is_goal"]].groupby("player").size().rename("goals")
    shot_count = shots.groupby("player").size().rename("shots")
    pass_count = passes.groupby("player").size().rename("passes")
    completed = passes[passes["completed"]].groupby("player").size().rename("passes_completed")

    summary = pd.concat([goals, shot_count, pass_count, completed], axis=1).fillna(0)
    summary = summary.astype(int).reset_index().rename(columns={"index": "player"})
    summary["pass_accuracy"] = summary.apply(
        lambda r: r["passes_completed"] / r["passes"] if r["passes"] else 0.0, axis=1
    )
    summary["shot_conversion"] = summary.apply(
        lambda r: r["goals"] / r["shots"] if r["shots"] else 0.0, axis=1
    )
    return summary.sort_values(["goals", "passes"], ascending=False).head(top_n).reset_index(drop=True)

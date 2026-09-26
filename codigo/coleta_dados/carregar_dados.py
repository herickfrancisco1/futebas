"""Cached wrappers around StatsBombPy's open-data API.

All functions here hit the public StatsBomb open-data repository (no
credentials required) and are wrapped in ``st.cache_data`` so repeated
selections in the dashboard do not re-download the same JSON payloads.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
from statsbombpy import sb


@st.cache_data(show_spinner=False, ttl=60 * 60 * 12)
def load_competitions() -> pd.DataFrame:
    """All competitions/seasons available in StatsBomb's open data."""
    return sb.competitions()


@st.cache_data(show_spinner=False, ttl=60 * 60 * 12)
def load_matches(competition_id: int, season_id: int) -> pd.DataFrame:
    """All matches for one competition/season."""
    matches = sb.matches(competition_id=competition_id, season_id=season_id)
    return matches.sort_values("match_date").reset_index(drop=True)


@st.cache_data(show_spinner=False, ttl=60 * 60 * 12)
def load_events(match_id: int) -> pd.DataFrame:
    """Full event stream (passes, shots, duels, ...) for one match."""
    return sb.events(match_id=match_id)


@st.cache_data(show_spinner=False, ttl=60 * 60 * 12)
def load_lineups(match_id: int) -> dict[str, pd.DataFrame]:
    """Squad lists (with positions/cards) for one match, keyed by team name."""
    return sb.lineups(match_id=match_id)


def load_events_for_matches(
    matches_df: pd.DataFrame,
    progress_callback=None,
) -> pd.DataFrame:
    """Load and concatenate events for every match in ``matches_df``.

    Reuses ``load_events`` (and therefore its cache) per match, so a
    match already opened elsewhere in the app is not re-downloaded.
    ``progress_callback(done, total, label)`` is called after each match,
    letting the caller drive a ``st.progress`` bar.
    """
    total = len(matches_df)
    frames = []
    for i, (_, match) in enumerate(matches_df.iterrows(), start=1):
        match_id = int(match["match_id"])
        events = load_events(match_id)
        events = events.copy()
        events["match_id"] = match_id
        events["home_team"] = match["home_team"]
        events["away_team"] = match["away_team"]
        events["competition_stage"] = match["competition_stage"]
        frames.append(events)
        if progress_callback is not None:
            label = f"{match['home_team']} {match['home_score']}-{match['away_score']} {match['away_team']}"
            progress_callback(i, total, label)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)

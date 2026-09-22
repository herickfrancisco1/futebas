"""Futebol Analytics — dashboard interativo com StatsBombPy + mplsoccer.

Pergunta central do projeto: em partidas de mata-mata de grandes torneios,
quais equipes e jogadores mais criam (passes) e convertem (chutes) chances
de gol, e como esse padrão aparece nos mapas de passe e de chute?
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st
from mplsoccer import Pitch

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "Code" / "DataAcquisition"))
sys.path.append(str(ROOT / "Code" / "DataPreparation"))
sys.path.append(str(ROOT / "Code" / "Modeling"))

from data_loader import load_competitions, load_events, load_events_for_matches, load_lineups, load_matches  # noqa: E402
from prepare import events_table, get_passes, get_shots, match_basic_stats, stage_team_aggregate, top_players  # noqa: E402
import metrics as met  # noqa: E402

st.set_page_config(page_title="Futebol Analytics", page_icon="⚽", layout="wide")
sns.set_theme(style="whitegrid")

PITCH_COLOR = "#0e1117"
LINE_COLOR = "#c7c7c7"


def colored_metric(label: str, value: str, good: bool | None) -> None:
    """A st.metric look-alike whose value is tinted green/red/gray."""
    color = "#2ecc71" if good is True else "#e74c3c" if good is False else "#a5a5a5"
    st.markdown(
        f"""
        <div style="line-height:1.1">
            <span style="font-size:0.85rem;color:#9aa0a6">{label}</span><br>
            <span style="font-size:1.8rem;font-weight:600;color:{color}">{value}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def new_pitch():
    pitch = Pitch(pitch_type="statsbomb", pitch_color=PITCH_COLOR, line_color=LINE_COLOR)
    fig, ax = pitch.draw(figsize=(8, 5.2))
    fig.patch.set_facecolor(PITCH_COLOR)
    return pitch, fig, ax


st.title("⚽ Futebol Analytics — Passes, Chutes e Criação de Gols")
st.caption(
    "Dados abertos do StatsBomb (via **statsbombpy**), visualizações com **mplsoccer**. "
    "Pergunta central: quais equipes e jogadores mais criam e convertem chances de gol, "
    "e como isso aparece nos mapas de passe e chute de cada partida?"
)

# ---------------------------------------------------------------- sidebar --
with st.sidebar:
    st.header("Filtros")

    with st.spinner("Carregando competições disponíveis..."):
        competitions = load_competitions()

    comp_names = sorted(competitions["competition_name"].unique())
    default_comp = "FIFA World Cup" if "FIFA World Cup" in comp_names else comp_names[0]
    competition_name = st.selectbox(
        "Campeonato", comp_names, index=comp_names.index(default_comp), key="competition_name"
    )

    comp_rows = competitions[competitions["competition_name"] == competition_name]
    season_names = list(comp_rows.sort_values("season_name", ascending=False)["season_name"].unique())
    default_season_idx = season_names.index("2022") if "2022" in season_names else 0
    season_name = st.selectbox("Temporada", season_names, index=default_season_idx, key="season_name")

    comp_season_row = comp_rows[comp_rows["season_name"] == season_name].iloc[0]
    competition_id = int(comp_season_row["competition_id"])
    season_id = int(comp_season_row["season_id"])

    with st.spinner("Carregando partidas da temporada..."):
        matches = load_matches(competition_id, season_id)

    stages = sorted(matches["competition_stage"].unique())
    stage_filter = st.multiselect("Fase da competição", stages, default=stages, key="stage_filter")
    matches_in_stage = matches[matches["competition_stage"].isin(stage_filter)] if stage_filter else matches

    match_labels = {
        int(row["match_id"]): (
            f"{row['match_date']} · {row['home_team']} {row['home_score']}-{row['away_score']} "
            f"{row['away_team']} ({row['competition_stage']})"
        )
        for _, row in matches_in_stage.sort_values("match_date", ascending=False).iterrows()
    }
    if not match_labels:
        st.warning("Nenhuma partida para essa combinação de filtros.")
        st.stop()

    match_id = st.selectbox(
        "Partida",
        options=list(match_labels.keys()),
        format_func=lambda mid: match_labels[mid],
        key="match_id",
    )

match_row = matches[matches["match_id"] == match_id].iloc[0]
home_team, away_team = match_row["home_team"], match_row["away_team"]

with st.spinner(f"Carregando eventos de {home_team} x {away_team}..."):
    events = load_events(match_id)

passes = get_passes(events)
shots = get_shots(events)
basic_stats = match_basic_stats(events, home_team, away_team)

players = sorted(events["player"].dropna().unique())
team_of_player = events.dropna(subset=["player"]).drop_duplicates("player").set_index("player")["team"]

tabs = st.tabs(["📋 Visão Geral", "🎯 Chutes", "🔁 Passes", "🧑‍🤝‍🧑 Comparar Jogadores", "🏆 Estatísticas do Torneio", "🗂️ Dados"])

# --------------------------------------------------------------- overview --
with tabs[0]:
    st.subheader(f"{competition_name} {season_name} — {home_team} {match_row['home_score']}-{match_row['away_score']} {away_team}")
    st.write(f"**Fase:** {match_row['competition_stage']} · **Data:** {match_row['match_date']} · **Estádio:** {match_row.get('stadium', 'N/D')}")

    total_goals = int(basic_stats["goals"].sum())
    total_shots = int(basic_stats["shots"].sum())
    total_passes = int(basic_stats["passes"].sum())
    conv_rate = met.shot_conversion_rate(shots)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Gols na partida", total_goals)
    with c2:
        st.metric("Chutes na partida", total_shots)
    with c3:
        st.metric("Passes na partida", total_passes)
    with c4:
        colored_metric("Taxa de conversão de chutes", f"{conv_rate:.1%}", good=conv_rate >= 0.15)

    st.markdown("##### Estatísticas por equipe")
    st.dataframe(basic_stats, use_container_width=True, hide_index=True)
    if (events["period"] == 5).any():
        st.caption("Gols e chutes de pênaltis na disputa por pênaltis (período 5) não entram nessas estatísticas — apenas jogo em campo.")

    st.markdown("##### Eventos da partida")
    st.dataframe(events_table(events).head(300), use_container_width=True, height=320)

# ------------------------------------------------------------------ shots --
with tabs[1]:
    st.subheader("Mapa de chutes")
    col_filters, col_plot = st.columns([1, 2.2])

    with col_filters:
        shot_team = st.radio("Equipe", [home_team, away_team], key="shot_team")
        only_goals = st.checkbox("Mostrar apenas gols", value=False, key="shots_only_goals")

    team_shots = shots[shots["team"] == shot_team]
    if only_goals:
        team_shots = team_shots[team_shots["is_goal"]]

    with col_plot:
        pitch, fig, ax = new_pitch()
        if len(team_shots):
            non_goals = team_shots[~team_shots["is_goal"]]
            goals = team_shots[team_shots["is_goal"]]
            pitch.scatter(
                non_goals["location_x"], non_goals["location_y"], ax=ax,
                s=(non_goals["shot_statsbomb_xg"].fillna(0.05) * 900).clip(lower=40) if "shot_statsbomb_xg" in non_goals else 80,
                color="#3498db", edgecolors="white", alpha=0.7, label="Chute",
            )
            pitch.scatter(
                goals["location_x"], goals["location_y"], ax=ax,
                s=(goals["shot_statsbomb_xg"].fillna(0.1) * 900).clip(lower=60) if "shot_statsbomb_xg" in goals else 140,
                color="#2ecc71", edgecolors="white", marker="*", label="Gol",
            )
            ax.legend(facecolor=PITCH_COLOR, labelcolor="white", loc="upper left")
        ax.set_title(f"Chutes — {shot_team}", color="white")
        st.pyplot(fig, use_container_width=True)

    with col_filters:
        st.markdown("##### Indicadores")
        st.metric("Chutes", len(team_shots))
        st.metric("Gols", int(team_shots["is_goal"].sum()))
        colored_metric(
            "Conversão", f"{met.shot_conversion_rate(team_shots):.1%}",
            good=met.shot_conversion_rate(team_shots) >= 0.15,
        )

# ----------------------------------------------------------------- passes --
with tabs[2]:
    st.subheader("Mapa de passes e mapa de calor")
    team_players = sorted(team_of_player[team_of_player.isin([home_team, away_team])].index)
    default_player = team_players[0] if team_players else None

    col_a, col_b = st.columns(2)
    with col_a:
        pass_player = st.selectbox("Jogador", team_players, index=0 if default_player else None, key="pass_player")
    with col_b:
        viz_kind = st.radio("Visualização", ["Mapa de passes", "Mapa de calor (toques)"], horizontal=True, key="pass_viz_kind")

    player_passes = passes[passes["player"] == pass_player]
    player_events = events[events["player"] == pass_player]
    player_events = player_events.dropna(subset=["location"]) if "location" in player_events.columns else player_events

    pitch, fig, ax = new_pitch()
    if viz_kind == "Mapa de passes":
        completed = player_passes[player_passes["completed"]]
        incomplete = player_passes[~player_passes["completed"]]
        pitch.arrows(
            completed["location_x"], completed["location_y"],
            completed["pass_end_location_x"], completed["pass_end_location_y"],
            ax=ax, color="#2ecc71", width=2, headwidth=6, label="Completo",
        )
        pitch.arrows(
            incomplete["location_x"], incomplete["location_y"],
            incomplete["pass_end_location_x"], incomplete["pass_end_location_y"],
            ax=ax, color="#e74c3c", width=2, headwidth=6, label="Incompleto",
        )
        ax.legend(facecolor=PITCH_COLOR, labelcolor="white", loc="upper left")
        ax.set_title(f"Passes — {pass_player}", color="white")
    else:
        from prepare import split_location
        touches = split_location(player_events, "location")
        if len(touches) >= 2:
            pitch.kdeplot(
                touches["location_x"], touches["location_y"], ax=ax,
                fill=True, cmap="magma", levels=100, thresh=0.02, alpha=0.85,
            )
        ax.set_title(f"Mapa de calor — {pass_player}", color="white")
    st.pyplot(fig, use_container_width=True)

    stats = met.player_pass_stats(passes, pass_player)
    c1, c2, c3 = st.columns(3)
    c1.metric("Passes tentados", stats["total_passes"])
    c2.metric("Passes completos", stats["completed_passes"])
    with c3:
        colored_metric("Precisão", f"{stats['accuracy']:.1%}", good=stats["accuracy"] >= 0.8)

# ------------------------------------------------------------- comparison --
with tabs[3]:
    st.subheader("Comparar dois jogadores")
    with st.form("compare_players_form"):
        colp1, colp2 = st.columns(2)
        with colp1:
            player_a = st.selectbox("Jogador A", players, index=0, key="player_a")
        with colp2:
            default_b = 1 if len(players) > 1 else 0
            player_b = st.selectbox("Jogador B", players, index=default_b, key="player_b")
        minute_range = st.slider(
            "Intervalo de tempo da partida (minutos)",
            min_value=0, max_value=int(events["minute"].max() or 90),
            value=(0, int(events["minute"].max() or 90)),
            key="compare_minute_range",
        )
        submitted = st.form_submit_button("Comparar")

    if submitted or True:  # always show the last submitted (or default) comparison
        lo, hi = minute_range
        scoped_events = events[(events["minute"] >= lo) & (events["minute"] <= hi)]
        scoped_passes = get_passes(scoped_events)
        scoped_shots = get_shots(scoped_events)

        rows = []
        for p in (player_a, player_b):
            ps = met.player_pass_stats(scoped_passes, p)
            ss = met.player_shot_stats(scoped_shots, p)
            rows.append(
                {
                    "Jogador": p,
                    "Passes": ps["total_passes"],
                    "Precisão de passe": ps["accuracy"],
                    "Chutes": ss["total_shots"],
                    "Gols": ss["goals"],
                    "Conversão": ss["conversion"],
                }
            )
        compare_df = pd.DataFrame(rows).set_index("Jogador")
        st.dataframe(
            compare_df.style.format({"Precisão de passe": "{:.1%}", "Conversão": "{:.1%}"}),
            use_container_width=True,
        )

        fig, ax = plt.subplots(figsize=(7, 3.5))
        compare_df[["Passes", "Chutes", "Gols"]].plot(kind="bar", ax=ax, color=["#3498db", "#f39c12", "#2ecc71"])
        ax.set_ylabel("Contagem")
        ax.set_title(f"{player_a} vs {player_b} ({lo}'–{hi}')")
        plt.xticks(rotation=0)
        st.pyplot(fig, use_container_width=True)

# -------------------------------------------------------- tournament aggs --
with tabs[4]:
    st.subheader("Estatísticas agregadas do torneio")
    st.caption(
        "Carrega os eventos de todas as partidas das fases selecionadas na barra lateral "
        "para explorar a relação entre passes, chutes e gols — e revelar os artilheiros "
        "e os jogadores mais influentes na construção de jogadas."
    )
    n_matches = len(matches_in_stage)
    st.write(f"Fases selecionadas: **{', '.join(stage_filter)}** · **{n_matches} partidas**")

    if "tournament_events" not in st.session_state:
        st.session_state.tournament_events = None
        st.session_state.tournament_scope = None

    load_clicked = st.button("📥 Carregar estatísticas do torneio", key="load_tournament_stats")

    current_scope = (competition_id, season_id, tuple(sorted(stage_filter)))
    if load_clicked:
        progress = st.progress(0.0, text="Iniciando...")

        def _update(done, total, label):
            progress.progress(done / total, text=f"Partida {done}/{total}: {label}")

        tournament_events = load_events_for_matches(matches_in_stage, progress_callback=_update)
        progress.empty()
        st.session_state.tournament_events = tournament_events
        st.session_state.tournament_scope = current_scope

    if st.session_state.tournament_events is not None and st.session_state.tournament_scope == current_scope:
        tour_events = st.session_state.tournament_events
        agg = stage_team_aggregate(tour_events)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Chutes x Gols por equipe/partida")
            fig, ax = plt.subplots(figsize=(6, 4.2))
            sns.regplot(
                data=agg, x="shots", y="goals", ax=ax,
                scatter_kws={"alpha": 0.6, "color": "#3498db"}, line_kws={"color": "#e74c3c"},
            )
            ax.set_xlabel("Chutes")
            ax.set_ylabel("Gols")
            st.pyplot(fig, use_container_width=True)
        with c2:
            st.markdown("##### Passes x Gols por equipe/partida")
            fig2, ax2 = plt.subplots(figsize=(6, 4.2))
            sns.scatterplot(
                data=agg, x="passes", y="goals", hue="stage", ax=ax2, palette="viridis", alpha=0.8,
            )
            ax2.set_xlabel("Passes")
            ax2.set_ylabel("Gols")
            st.pyplot(fig2, use_container_width=True)

        st.markdown("##### Top jogadores (gols e passes) nas fases selecionadas")
        top_n = st.slider("Quantidade de jogadores a exibir", 5, 25, 10, key="top_n_players")
        top_df = top_players(tour_events, top_n=top_n)
        st.dataframe(
            top_df.style.format({"pass_accuracy": "{:.1%}", "shot_conversion": "{:.1%}"}),
            use_container_width=True, hide_index=True,
        )

        csv_agg = agg.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Baixar agregados por equipe/partida (CSV)", csv_agg,
            file_name=f"agregados_{competition_name}_{season_name}.csv".replace(" ", "_"), mime="text/csv",
        )
    else:
        st.info("Clique em **Carregar estatísticas do torneio** para gerar os gráficos agregados.")

# ------------------------------------------------------------------- data --
with tabs[5]:
    st.subheader("Explorador de dados da partida")
    with st.form("data_filter_form"):
        event_types = sorted(events["type"].dropna().unique())
        chosen_types = st.multiselect("Tipos de evento", event_types, default=["Pass", "Shot"], key="data_event_types")
        player_query = st.text_input("Buscar jogador (contém)", key="data_player_query")
        max_rows = st.slider("Máximo de linhas", 10, 500, 100, key="data_max_rows")
        apply_filters = st.form_submit_button("Aplicar filtros")

    filtered = events[events["type"].isin(chosen_types)] if chosen_types else events
    if player_query:
        filtered = filtered[filtered["player"].str.contains(player_query, case=False, na=False)]
    table = events_table(filtered).head(max_rows)

    st.dataframe(table, use_container_width=True, height=420)
    st.caption(f"Exibindo {len(table)} de {len(filtered)} eventos filtrados (de {len(events)} no total da partida).")

    csv_bytes = table.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Baixar eventos filtrados (CSV)", csv_bytes,
        file_name=f"eventos_{match_id}_{home_team}_vs_{away_team}.csv".replace(" ", "_"), mime="text/csv",
    )

    with st.expander("Escalações (lineups)"):
        with st.spinner("Carregando escalações..."):
            lineups = load_lineups(match_id)
        lcol1, lcol2 = st.columns(2)
        for col, team in zip((lcol1, lcol2), (home_team, away_team)):
            with col:
                st.markdown(f"**{team}**")
                if team in lineups:
                    st.dataframe(lineups[team][["player_name", "jersey_number", "country"]], hide_index=True, use_container_width=True)

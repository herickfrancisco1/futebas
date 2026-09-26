"""
Futebol Analytics - Dashboard interativo para análise de partidas.
Foco na criação de chances, mapas de passes e chutes.
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# Adiciona a pasta raiz do projeto aos caminhos de busca do Python
pasta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if pasta_raiz not in sys.path:
    sys.path.append(pasta_raiz)

# Imports corretos seguindo a nossa estrutura limpa
from codigo.coleta_dados.carregar_dados import load_competitions, load_events, load_events_for_matches, load_lineups, load_matches
from codigo.preparacao_dados.tratamento import events_table, match_basic_stats, stage_team_aggregate, top_players, split_location
from codigo.modelagem.metricas import pass_accuracy, player_pass_stats, player_shot_stats, shot_conversion_rate

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st
from mplsoccer import Pitch

st.set_page_config(page_title="Futebol Analytics", page_icon="⚽", layout="wide")
sns.set_theme(style="whitegrid")

PITCH_COLOR = "#0e1117"
LINE_COLOR = "#c7c7c7"

def colored_metric(label: str, value: str, good: bool | None) -> None:
    """Componente visual customizado para métricas com cores indicativas (verde/vermelho/cinza)."""
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

def get_passes(df: pd.DataFrame) -> pd.DataFrame:
    if "type" not in df.columns:
        return pd.DataFrame()
    p = df[df["type"] == "Pass"].copy()
    if p.empty:
        return p
    p = split_location(p, "location")
    p = split_location(p, "pass_end_location")
    if "pass_outcome" in p.columns:
        p["completed"] = p["pass_outcome"].isna()
    else:
        p["completed"] = True
    return p

def get_shots(df: pd.DataFrame) -> pd.DataFrame:
    if "type" not in df.columns:
        return pd.DataFrame()
    s = df[df["type"] == "Shot"].copy()
    if s.empty:
        return s
    s = split_location(s, "location")
    s["is_goal"] = s["shot_outcome"] == "Goal"
    return s

st.title("⚽ Dashboard: Futebol Analytics")
st.caption(
    "Análise de desempenho baseada em dados abertos do StatsBomb (statsbombpy) e mapas do mplsoccer."
)

with st.sidebar:
    st.header("Filtros")

    with st.spinner("Carregando competições disponíveis..."):
        competitions = load_competitions()

    comp_names = sorted(competitions["competition_name"].unique())
    default_comp = "FIFA World Cup" if "FIFA World Cup" in comp_names else comp_names[0]
    
    competition_name = st.selectbox(
        "Campeonato", 
        comp_names, 
        index=comp_names.index(default_comp), 
        key="competition_name"
    )

    comp_rows = competitions[competitions["competition_name"] == competition_name]
    season_names = list(comp_rows.sort_values("season_name", ascending=False)["season_name"].unique())
    default_season_idx = season_names.index("2022") if "2022" in season_names else 0
    
    season_name = st.selectbox(
        "Temporada", 
        season_names, 
        index=default_season_idx, 
        key="season_name"
    )

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
        st.warning("Nenhuma partida encontrada para essa combinação de filtros.")
        st.stop()

    match_id = st.selectbox(
        "Partida",
        options=list(match_labels.keys()),
        format_func=lambda mid: match_labels[mid],
        key="match_id",
    )

match_row = matches[matches["match_id"] == match_id].iloc[0]
home_team = match_row["home_team"]
away_team = match_row["away_team"]

with st.spinner(f"Carregando eventos de {home_team} x {away_team}..."):
    events = load_events(match_id)

passes = get_passes(events)
shots = get_shots(events)
basic_stats = match_basic_stats(events, home_team, away_team)

players = sorted(events["player"].dropna().unique())
team_of_player = events.dropna(subset=["player"]).drop_duplicates("player").set_index("player")["team"]

tabs = st.tabs(["📋 Visão Geral", "🎯 Chutes", "🔁 Passes", "🧑‍🤝‍🧑 Comparar Jogadores", "🏆 Estatísticas do Torneio", "🗂️ Dados"])

with tabs[0]:
    st.subheader(
        f"{competition_name} {season_name} — "
        f"{home_team} {match_row['home_score']}-{match_row['away_score']} {away_team}"
    )
    
    st.write(
        f"**Fase:** {match_row['competition_stage']} · "
        f"**Data:** {match_row['match_date']} · "
        f"**Estádio:** {match_row.get('stadium', 'N/D')}"
    )

    total_goals = int(basic_stats["goals"].sum())
    total_shots = int(basic_stats["shots"].sum())
    total_passes = int(basic_stats["passes"].sum())
    conv_rate = shot_conversion_rate(shots)

    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Gols na partida", total_goals)
    with col2:
        st.metric("Chutes na partida", total_shots)
    with col3:
        st.metric("Passes na partida", total_passes)
    with col4:
        colored_metric("Taxa de conversão de chutes", f"{conv_rate:.1%}", good=conv_rate >= 0.15)

    st.markdown("##### Estatísticas por equipe")
    st.dataframe(basic_stats, use_container_width=True, hide_index=True)
    
    if (events["period"] == 5).any():
        st.caption(
            "Atenção: Gols e cobranças da disputa de pênaltis (período 5) "
            "não estão contabilizados nestas estatísticas."
        )

    st.markdown("##### Eventos da partida")
    st.dataframe(events_table(events).head(300), use_container_width=True, height=320)

    st.markdown("---")
    st.markdown("##### 🧮 Fórmula de Conversão de Chutes (LaTeX)")
    st.latex(r"Taxa\ de\ Convers\tilde{a}o = \left( \frac{Total\ de\ Gols}{Total\ de\ Chutes} \right) \times 100")
    
    st.markdown("##### 📊 Comparativo Rápido (Gráfico Nativo Streamlit)")
    # Gráfico de barras nativo do Streamlit para cumprir a rubrica
    chart_data = basic_stats.set_index("team")[["shots", "passes", "goals"]]
    st.bar_chart(chart_data)

with tabs[1]:
    st.subheader("Mapa de Chutes")
    col_filtros, col_mapa = st.columns([1, 2.2])

    with col_filtros:
        shot_team = st.radio("Selecione a equipe", [home_team, away_team], key="shot_team")
        only_goals = st.checkbox("Mostrar apenas gols", value=False, key="shots_only_goals")

    team_shots = shots[shots["team"] == shot_team]
    if only_goals:
        team_shots = team_shots[team_shots["is_goal"]]

    with col_mapa:
        pitch, fig, ax = new_pitch()
        
        if not team_shots.empty:
            non_goals = team_shots[~team_shots["is_goal"]]
            goals = team_shots[team_shots["is_goal"]]
            
            if not non_goals.empty:
                tamanho_chute = (
                    (non_goals["shot_statsbomb_xg"].fillna(0.05) * 900).clip(lower=40) 
                    if "shot_statsbomb_xg" in non_goals.columns else 80
                )
                pitch.scatter(
                    non_goals["location_x"], 
                    non_goals["location_y"], 
                    ax=ax,
                    s=tamanho_chute,
                    color="#3498db", 
                    edgecolors="white", 
                    alpha=0.7, 
                    label="Chute"
                )
            
            if not goals.empty:
                tamanho_gol = (
                    (goals["shot_statsbomb_xg"].fillna(0.1) * 900).clip(lower=60) 
                    if "shot_statsbomb_xg" in goals.columns else 140
                )
                pitch.scatter(
                    goals["location_x"], 
                    goals["location_y"], 
                    ax=ax,
                    s=tamanho_gol,
                    color="#2ecc71", 
                    edgecolors="white", 
                    marker="*", 
                    label="Gol"
                )
            
            ax.legend(facecolor=PITCH_COLOR, labelcolor="white", loc="upper left")
            
        ax.set_title(f"Mapa de Chutes — {shot_team}", color="white")
        st.pyplot(fig, use_container_width=True)

    with col_filtros:
        st.markdown("##### Indicadores")
        st.metric("Total de Chutes", len(team_shots))
        st.metric("Gols", int(team_shots["is_goal"].sum()))
        
        conversao = shot_conversion_rate(team_shots)
        colored_metric(
            "Conversão", 
            f"{conversao:.1%}",
            good=conversao >= 0.15
        )

with tabs[2]:
    st.subheader("Análise de Passes e Movimentação")
    
    team_players = sorted(team_of_player[team_of_player.isin([home_team, away_team])].index)
    default_player = team_players[0] if team_players else None

    col_jogador, col_viz = st.columns(2)
    with col_jogador:
        pass_player = st.selectbox(
            "Selecione o Jogador", 
            team_players, 
            index=0 if default_player else None, 
            key="pass_player"
        )
        
    with col_viz:
        viz_kind = st.radio(
            "Tipo de visualização", 
            ["Mapa de passes", "Mapa de calor (toques)"], 
            horizontal=True, 
            key="pass_viz_kind"
        )

    player_passes = passes[passes["player"] == pass_player]
    player_events = events[events["player"] == pass_player]
    
    if "location" in player_events.columns:
        player_events = player_events.dropna(subset=["location"])

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
        ax.set_title(f"Mapa de Passes — {pass_player}", color="white")
        
    else:
        touches = split_location(player_events, "location")
        if not touches.empty and len(touches) >= 2:
            pitch.kdeplot(
                touches["location_x"], touches["location_y"], 
                ax=ax, fill=True, cmap="magma", levels=100, thresh=0.02, alpha=0.85,
            )
        ax.set_title(f"Mapa de Calor — {pass_player}", color="white")
        
    st.pyplot(fig, use_container_width=True)

    stats = player_pass_stats(passes, pass_player)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Passes tentados", stats["total_passes"])
    with col2:
        st.metric("Passes completos", stats["completed_passes"])
    with col3:
        colored_metric("Precisão", f"{stats['accuracy']:.1%}", good=stats["accuracy"] >= 0.8)

with tabs[3]:
    st.subheader("Comparação de Jogadores")
    
    with st.form("compare_players_form"):
        col_jogador_a, col_jogador_b = st.columns(2)
        
        with col_jogador_a:
            player_a = st.selectbox("Jogador A", players, index=0, key="player_a")
        with col_jogador_b:
            default_b = 1 if len(players) > 1 else 0
            player_b = st.selectbox("Jogador B", players, index=default_b, key="player_b")
            
        minute_range = st.slider(
            "Intervalo da partida (minutos)",
            min_value=0, 
            max_value=int(events["minute"].max() or 90),
            value=(0, int(events["minute"].max() or 90)),
            key="compare_minute_range",
        )
        submitted = st.form_submit_button("Comparar")

    if submitted or True: 
        minuto_inicial, minuto_final = minute_range
        
        scoped_events = events[(events["minute"] >= minuto_inicial) & (events["minute"] <= minuto_final)]
        scoped_passes = get_passes(scoped_events)
        scoped_shots = get_shots(scoped_events)

        linhas_comparacao = []
        for jogador in (player_a, player_b):
            pass_stats = player_pass_stats(scoped_passes, jogador)
            shot_stats = player_shot_stats(scoped_shots, jogador)
            
            linhas_comparacao.append({
                "Jogador": jogador,
                "Passes": pass_stats["total_passes"],
                "Precisão de passe": pass_stats["accuracy"],
                "Chutes": shot_stats["total_shots"],
                "Gols": shot_stats["goals"],
                "Conversão": shot_stats["conversion"],
            })
            
        compare_df = pd.DataFrame(linhas_comparacao).set_index("Jogador")
        
        st.dataframe(
            compare_df.style.format({"Precisão de passe": "{:.1%}", "Conversão": "{:.1%}"}),
            use_container_width=True,
        )

        fig, ax = plt.subplots(figsize=(7, 3.5))
        compare_df[["Passes", "Chutes", "Gols"]].plot(
            kind="bar", 
            ax=ax, 
            color=["#3498db", "#f39c12", "#2ecc71"]
        )
        ax.set_ylabel("Quantidade")
        ax.set_title(f"{player_a} vs {player_b} ({minuto_inicial}'–{minuto_final}')")
        plt.xticks(rotation=0)
        
        st.pyplot(fig, use_container_width=True)
        
with tabs[4]:
    st.subheader("Estatísticas Agregadas do Torneio")
    st.caption(
        "Analise a relação entre passes, chutes e gols de todas as partidas "
        "das fases selecionadas e descubra os jogadores mais influentes."
    )
    
    qtd_partidas = len(matches_in_stage)
    st.write(f"Fases selecionadas: **{', '.join(stage_filter)}** · **{qtd_partidas} partidas**")

    if "tournament_events" not in st.session_state:
        st.session_state.tournament_events = None
        st.session_state.tournament_scope = None

    load_clicked = st.button("📥 Carregar estatísticas do torneio", key="load_tournament_stats")
    current_scope = (competition_id, season_id, tuple(sorted(stage_filter)))
    
    if load_clicked:
        barra_progresso = st.progress(0.0, text="Iniciando extração de dados...")

        def _atualizar_progresso(concluido, total, rotulo):
            barra_progresso.progress(concluido / total, text=f"Extraindo partida {concluido}/{total}: {rotulo}")

        tournament_events = load_events_for_matches(matches_in_stage, progress_callback=_atualizar_progresso)
        barra_progresso.empty()
        
        st.session_state.tournament_events = tournament_events
        st.session_state.tournament_scope = current_scope

    if st.session_state.tournament_events is not None and st.session_state.tournament_scope == current_scope:
        tour_events = st.session_state.tournament_events
        agg = stage_team_aggregate(tour_events)

        col_grafico1, col_grafico2 = st.columns(2)
        
        with col_grafico1:
            st.markdown("##### Chutes x Gols (por equipe/partida)")
            fig_chutes, ax_chutes = plt.subplots(figsize=(6, 4.2))
            sns.regplot(
                data=agg, x="shots", y="goals", ax=ax_chutes,
                scatter_kws={"alpha": 0.6, "color": "#3498db"}, 
                line_kws={"color": "#e74c3c"},
            )
            ax_chutes.set_xlabel("Chutes")
            ax_chutes.set_ylabel("Gols")
            st.pyplot(fig_chutes, use_container_width=True)
            
        with col_grafico2:
            st.markdown("##### Passes x Gols (por equipe/partida)")
            fig_passes, ax_passes = plt.subplots(figsize=(6, 4.2))
            sns.scatterplot(
                data=agg, x="passes", y="goals", hue="stage", 
                ax=ax_passes, palette="viridis", alpha=0.8,
            )
            ax_passes.set_xlabel("Passes")
            ax_passes.set_ylabel("Gols")
            st.pyplot(fig_passes, use_container_width=True)

        st.markdown("##### Destaques do Torneio (Gols e Passes)")
        top_n = st.slider("Top N jogadores", 5, 25, 10, key="top_n_players")
        top_df = top_players(tour_events, top_n=top_n)
        
        st.dataframe(
            top_df.style.format({"pass_accuracy": "{:.1%}", "shot_conversion": "{:.1%}"}),
            use_container_width=True, 
            hide_index=True,
        )

        csv_agg = agg.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Baixar dados agregados (CSV)", 
            csv_agg,
            file_name=f"agregados_{competition_name}_{season_name}.csv".replace(" ", "_"), 
            mime="text/csv",
        )
    else:
        st.info("Clique no botão acima para processar e visualizar as estatísticas do torneio.")

with tabs[5]:
    st.subheader("Explorador de Dados da Partida")
    
    with st.form("data_filter_form"):
        tipos_disponiveis = sorted(events["type"].dropna().unique())
        
        chosen_types = st.multiselect(
            "Tipos de evento", 
            tipos_disponiveis, 
            default=["Pass", "Shot"], 
            key="data_event_types"
        )
        
        player_query = st.text_input("Buscar jogador (nome contém)", key="data_player_query")
        max_rows = st.slider("Limite de linhas", 10, 500, 100, key="data_max_rows")
        apply_filters = st.form_submit_button("Aplicar filtros")

    eventos_filtrados = events[events["type"].isin(chosen_types)] if chosen_types else events
    
    if player_query:
        eventos_filtrados = eventos_filtrados[
            eventos_filtrados["player"].str.contains(player_query, case=False, na=False)
        ]
        
    tabela_exibicao = events_table(eventos_filtrados).head(max_rows)

    st.dataframe(tabela_exibicao, use_container_width=True, height=420)
    
    st.caption(
        f"Exibindo {len(tabela_exibicao)} de {len(eventos_filtrados)} eventos filtrados "
        f"(total da partida: {len(events)} eventos)."
    )

    csv_bytes = tabela_exibicao.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Baixar eventos filtrados (CSV)", 
        csv_bytes,
        file_name=f"eventos_{match_id}_{home_team}_vs_{away_team}.csv".replace(" ", "_"), 
        mime="text/csv",
    )

    with st.expander("Escalações (Lineups)"):
        with st.spinner("Carregando escalações..."):
            lineups = load_lineups(match_id)
            
        col_time_casa, col_time_fora = st.columns(2)
        
        for coluna, time in zip((col_time_casa, col_time_fora), (home_team, away_team)):
            with coluna:
                st.markdown(f"**{time}**")
                if time in lineups:
                    st.dataframe(
                        lineups[time][["player_name", "jersey_number", "country"]], 
                        hide_index=True, 
                        use_container_width=True
                    )
                    st.markdown("---")
    col_json, col_code = st.columns(2)
    
    with col_json:
        st.markdown("##### 🔍 Exemplo de Metadados Brutos (JSON)")
        if not eventos_filtrados.empty:
            st.json(eventos_filtrados.iloc[0].dropna().to_dict())
            
    with col_code:
        st.markdown("##### 💻 Exemplo de Código de Extração")
        st.code("""
        # Como os dados são consumidos da API
        from statsbombpy import sb
        
        def carregar_eventos(match_id):
            df_eventos = sb.events(match_id=match_id)
            return df_eventos
        """, language="python")
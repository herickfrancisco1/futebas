# Project Charter — Futebol Analytics

## Objetivo

Construir um dashboard interativo que responda: **quais equipes e jogadores mais criam
(passes) e convertem (chutes) chances de gol em partidas de mata-mata de grandes torneios,
e como isso aparece nos mapas de passe e de chute de cada partida?**

## Motivação

Dados de eventos (passes, chutes, duelos) permitem ir além do placar e entender *como* um
resultado foi construído. Times e analistas usam esse tipo de leitura para preparar
partidas, escalar jogadores e justificar decisões táticas.

## Fonte de dados

StatsBomb Open Data (gratuito, sem necessidade de credenciais), acessado via `statsbombpy`.
Cobre Copas do Mundo, Euros, Champions League, La Liga (dados do Messi), Women's World Cup,
entre outros — 80 combinações de campeonato/temporada disponíveis no momento da construção
deste projeto.

## Escopo

- Nível de partida: placar, estatísticas por equipe, mapa de passes, mapa de chutes, mapa
  de calor por jogador, comparação entre dois jogadores.
- Nível de torneio: agregação de gols/chutes/passes por equipe e por partida nas fases
  escolhidas pelo usuário, ranking de artilheiros/passadores.

## Fora de escopo

- Estatísticas agregadas "oficiais" da StatsBomb (`player_season_stats`,
  `team_season_stats`) exigem credenciais pagas e não são usadas — todas as agregações do
  torneio são calculadas a partir dos eventos brutos, no próprio dashboard.
- Pênaltis da disputa por pênaltis (period 5) são excluídos das estatísticas de
  gols/chutes/conversão para manter esses números coerentes com o placar oficial da
  partida.

## Entregáveis

1. Dashboard Streamlit publicado (Streamlit Community Cloud).
2. Repositório GitHub com código organizado (`app/`, `Code/`, `Data/`, `Docs/`) e
   `requirements.txt`.
3. Este *Project Charter*.

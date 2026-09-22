# ⚽ Futebol Analytics — Passes, Chutes e Criação de Gols

Dashboard interativo em **Streamlit** sobre dados abertos de futebol do **StatsBomb**
(`statsbombpy`), com visualizações táticas em **mplsoccer**.

**Pergunta central:** em partidas de mata-mata de grandes torneios (Copa do Mundo, Euro,
Champions League, ...), quais equipes e jogadores mais **criam** (passes) e **convertem**
(chutes) chances de gol — e como esse padrão aparece nos mapas de passe e de chute de cada
partida?

## Funcionalidades

- Seleção de **campeonato**, **temporada**, **fase** e **partida** (dados oficiais StatsBomb
  open data, sem necessidade de credenciais).
- **Visão geral**: placar, gols/chutes/passes da partida, tabela de eventos.
- **Mapa de chutes** (mplsoccer) com tamanho do marcador proporcional ao xG, filtro por
  equipe e por "somente gols".
- **Mapa de passes** e **mapa de calor** (kdeplot) por jogador.
- **Comparação de dois jogadores** com filtro por intervalo de minutos da partida.
- **Estatísticas agregadas do torneio**: carrega os eventos de várias partidas (com barra de
  progresso), mostra a relação chutes×gols e passes×gols, e o ranking de artilheiros/passadores.
- **Explorador de dados**: filtro por tipo de evento e jogador, tabela paginada e
  **download em CSV** dos eventos filtrados (ou dos agregados do torneio).
- Escalações (lineups) de cada partida.
- Cache (`st.cache_data`) para não baixar os mesmos dados duas vezes e `st.session_state`
  para manter os agregados do torneio calculados ao navegar entre abas.

## Estrutura do projeto (TDSP)

```
futebol-analytics-dashboard/
├── app/
│   └── app.py                     # Aplicação Streamlit (Deployment)
├── Code/
│   ├── DataAcquisition/
│   │   └── data_loader.py         # Wrappers cacheados sobre statsbombpy
│   ├── DataPreparation/
│   │   └── prepare.py             # Limpeza de eventos, passes, chutes, agregados
│   ├── Modeling/
│   │   └── metrics.py             # Métricas: precisão de passe, conversão de chute...
│   └── Deployment/
│       └── DEPLOY.md              # Passo a passo do deploy no Streamlit Community Cloud
├── Data/
│   ├── Raw/                       # (vazio — dados vêm ao vivo da API do StatsBomb)
│   └── Processed/
├── Docs/
│   └── Project/
│       └── project_charter.md
├── requirements.txt
└── README.md
```

## Como rodar localmente

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
streamlit run app/app.py
```

O app abre em `http://localhost:8501`. Nenhuma chave de API é necessária: os dados usados
são o **StatsBomb open data**, acessado publicamente pelo pacote `statsbombpy`.

## Fonte dos dados

- [StatsBomb Open Data](https://github.com/statsbomb/open-data) via
  [`statsbombpy`](https://github.com/statsbomb/statsbombpy).
- Visualizações táticas: [`mplsoccer`](https://mplsoccer.readthedocs.io/).

## Deploy

Veja [`Code/Deployment/DEPLOY.md`](Code/Deployment/DEPLOY.md) para o passo a passo de
publicação no Streamlit Community Cloud.

---

Projeto acadêmico — Herick Francisco.

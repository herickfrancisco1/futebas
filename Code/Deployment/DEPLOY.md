# Deploy no Streamlit Community Cloud

1. Suba este projeto para um repositório no GitHub (público ou privado — para deploy
   gratuito, o Streamlit Community Cloud exige acesso ao repo, mas ele pode ser privado se
   você conectar sua conta GitHub).
2. Acesse [share.streamlit.io](https://share.streamlit.io) e faça login com GitHub.
3. Clique em **New app**, escolha o repositório, o branch (`main`) e o caminho do script
   principal: `app/app.py`.
4. Em **Advanced settings**, defina a versão do Python (recomendado 3.11 ou 3.12 — as
   dependências deste projeto, especialmente `mplsoccer`, têm melhor suporte testado nessas
   versões do que em versões muito recentes do Python).
5. Clique em **Deploy**. O Streamlit Cloud instala automaticamente o `requirements.txt` na
   raiz do projeto.
6. Depois do primeiro deploy bem-sucedido, qualquer `git push` no branch configurado
   atualiza o app automaticamente.

## Observações

- Não é necessária nenhuma credencial/secret: os dados vêm do StatsBomb Open Data, que é
  público. Não crie um `secrets.toml` para isso.
- A aba **Estatísticas do Torneio** baixa os eventos de várias partidas ao vivo da StatsBomb
  na primeira vez que é usada para cada combinação de campeonato/temporada/fase — isso pode
  levar de alguns segundos a ~1 minuto dependendo da quantidade de partidas selecionadas na
  barra lateral. Os resultados ficam em cache (`st.cache_data` + `st.session_state`)
  enquanto o app estiver rodando.

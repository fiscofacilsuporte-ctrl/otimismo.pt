name: Atualizar Notícias

on:
  schedule:
    - cron: '0 6,12,18 * * *'   # 3x por dia: 6h, 12h e 18h UTC
  workflow_dispatch:              # permite correr manualmente

jobs:
  fetch:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout repositório
        uses: actions/checkout@v4

      - name: Configurar Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Instalar dependências
        run: pip install -r requirements.txt

      - name: Correr fetch_news.py
        run: python fetch_news.py

      - name: Commit e push noticias.json
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add noticias.json
          git diff --cached --quiet || git commit -m "🤖 Atualização automática de notícias"
          git push

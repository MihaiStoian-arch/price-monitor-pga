# Numele workflow-ului
name: Price Scraper

# Când se declanșează
on:
  # Rulează manual din interfața GitHub Actions
  workflow_dispatch:
  # Rulează zilnic la o oră fixă (de exemplu, 08:00 UTC)
  schedule:
    - cron: '0 8 * * *'

# Job-ul principal
jobs:
  run_scraper:
    runs-on: ubuntu-latest

    steps:
      # 1. Checkout codul
      - name: Checkout repository
        uses: actions/checkout@v4

      # 2. Setează mediul Python
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      # 3. Instalează dependențele (inclusiv Playwright)
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          # Asigurați-vă că requirements.txt conține "playwright"
          pip install -r requirements.txt

      # 4. Instalează Browserele Playwright (PAS CRITIC!)
      - name: Install Playwright browsers
        run: playwright install

      # 5. Rulează Scriptul Principal
      - name: Run main script
        run: python main.py

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import requests
# --- IMPORTURI PENTRU EMAIL ---
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio # Esențial pentru Pyppeteer

# --- CONFIGURARE EMAIL (SCHIMBĂ VALORILE CU DATELE TALE) ---
SENDER_EMAIL = 'mihaistoian889@gmail.com'
RECEIVER_EMAIL = 'octavian@atvrom.ro'
SMTP_PASSWORD = 'igcu wwbs abit ganm'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
# ------------------------------------------------------------

# ⚠️ ASIGURĂ-TE CĂ AI INSTALAT TOATE DEPENDENȚELE:
# pip install gspread oauth2client requests beautifulsoup4 pyppeteer

# --- IMPORTURI FUNCȚII DE SCRAPING ESENȚIALE PENTRU DEBUG ---
# Acestea sunt singurele fișiere de care avem nevoie acum
from monitor.sites.moto24 import scrape_moto24_search 
from monitor.sites.nordicamoto import scrape_nordicamoto_search
# ------------------------------------------------------------


# ----------------------------------------------------
## 1. ⚙️ Configurare
# ... (Aici vin celelalte variabile de configurare din fisierul tau original)

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CREDS_FILE = 'service_account_credentials.json'
SPREADSHEET_KEY = '19jH8sI2q3vP5pG7r9tX0yZ4wE6uI1mK3lO2nQ8R4sT6uV0' # SCHIMBĂ CU CHEIA TA REALĂ
SHEET_NAME = 'Sheet1' 

# Coloanele din foaia de calcul (0-indexed)
COD_PRODUS_COL_INDEX = 0
LINK_COL_INDEX = 1
PRET_ACTUAL_COL_INDEX = 2
PRET_VECHI_COL_INDEX = 3
SITE_COL_INDEX = 4
STATUS_COL_INDEX = 5
EMAIL_STATUS_COL_INDEX = 6
PRET_MOTO24_COL_INDEX = 8
PRET_NORDICAMOTO_COL_INDEX = 9
# etc.

# Funcția setup_sheets_client (PĂSTRAȚI CODUL ORIGINAL)
def setup_sheets_client():
    # ... (logica de inițializare gspread) ...
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
        client = gspread.authorize(creds)
        print("✅ Conexiune la Google Sheets reușită.")
        return client
    except Exception as e:
        print(f"❌ Eroare la inițializarea Google Sheets: {e}")
        return None

# ... (includeti restul functiilor, inclusiv send_email, process_atvrom_price_map, run_price_monitor etc. - dacă acestea există și nu le-ați eliminat) ...


# ----------------------------------------------------
## 3. 🔄 Logica de Procesare (păstrată pentru integritate, dar nefolosită în debug)
# ----------------------------------------------------

def get_scraper_function(site_name):
    """Returnează funcția de scraping corespunzătoare pentru un anumit site."""
    # MAPARE SITE -> FUNCȚIE
    mapping = {
        'moto24.ro': scrape_moto24_search,
        'nordicamoto.ro': scrape_nordicamoto_search,
        # Aici ar veni celelalte site-uri când revenim la monitorizarea completă
    }
    return mapping.get(site_name)

def run_price_monitor(sheet_client):
    # ... (logica principală de monitorizare, lăsați-o pe cea existentă) ...
    pass
    

# ----------------------------------------------------
## 4. 🏁 Punctul de Intrare
# ----------------------------------------------------

def run_debug_test():
    """Rulează un test izolat pe codul HJC100528-XS pentru a forța log-urile."""
    PRODUCT_CODE = 'HJC100528-XS' 

    print("--- TEST NORDICAMOTO (PYPPETEER) ---")
    try:
        price_nordicamoto = scrape_nordicamoto_search(PRODUCT_CODE)
        print(f"REZULTAT NORDICAMOTO FINAL: {price_nordicamoto}")
    except Exception as e:
        print(f"⚠️ EROARE GRAVĂ DE DEBUG NORDICAMOTO: {e}")

    print("\n--- TEST MOTO24 (PYPPETEER) ---")
    try:
        price_moto24 = scrape_moto24_search(PRODUCT_CODE)
        print(f"REZULTAT MOTO24 FINAL: {price_moto24}")
    except Exception as e:
        print(f"⚠️ EROARE GRAVĂ DE DEBUG MOTO24: {e}")
    
    print("\n--- SFÂRȘITUL TESTULUI DE DEBUG ---")

if __name__ == "__main__":
    
    # RULĂM DOAR TESTUL DE DEBUG
    run_debug_test()
    
    # Codul original al monitorului este dezactivat temporar.
    # sheet_client = setup_sheets_client()
    # if sheet_client:
    #     run_price_monitor(sheet_client)

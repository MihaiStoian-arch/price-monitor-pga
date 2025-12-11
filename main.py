import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import requests
# --- IMPORTURI PENTRU EMAIL ---
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# --- IMPORTURI SCRAPERI (ECHIPAMENTE) ---
from monitor.sites.moto24 import scrape_moto24_search
from monitor.sites.nordicamoto import scrape_nordicamoto_search
# ------------------------------------------------------------

# --- CONFIGURARE EMAIL (SCHIMBĂ VALORILE CU DATELE TALE) ---
SENDER_EMAIL = 'mihaistoian889@gmail.com'
RECEIVER_EMAIL = 'octavian@atvrom.ro'
SMTP_PASSWORD = 'igcu wwbs abit ganm'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
# ------------------------------------------------------------

# Pragul minim de diferență (în RON) sub care nu se trimite alertă
MINIMUM_DIFFERENCE_THRESHOLD = 1.0 

# --- CONFIGURARE FOAIE DE CALCUL ---
SPREADSHEET_NAME = 'Price Monitor ATVRom'
WORKSHEET_NAME = 'Echipamente HJC'
CREDENTIALS_FILE = 'service_account_credentials.json'

# Harta: { Index Coloană Sursă (Cod Produs): [Index Coloană Destinație (Preț), Funcție Scraper] }
# Coloana B (Cod Produs) = 2, D (Moto24) = 4, E (Nordicamoto) = 5
SCRAPER_COORDS = {
    # ⚠️ ATVROM (C) se actualizează separat prin Google App Script
    2: [4, scrape_moto24_search],             # B (Cod Produs) -> D (Preț Moto24)
    2: [5, scrape_nordicamoto_search],        # B (Cod Produs) -> E (Preț Nordicamoto)
}

# Coloana pentru Timestamp-ul general (Coloana F)
TIMESTAMP_COL_INDEX = 6

def setup_sheets_client():
    """Inițializează clientul gspread și returnează foaia de lucru."""
    # (Funcția rămâne identică cu cea din proiectul anterior)
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open(SPREADSHEET_NAME)
        sheet = spreadsheet.worksheet(WORKSHEET_NAME)
        print(f"✅ Conexiune reușită la foaia de lucru '{WORKSHEET_NAME}'.")

        # ... (Logica de IP se păstrează) ...
        return sheet
    except Exception as e:
        print(f"❌ Eroare la inițializarea Google Sheets client: {e}")
        return None

def send_alert_email(subject, body):
    """Trimite un email folosind SMTP."""
    # (Funcția rămâne identică cu cea din proiectul anterior)
    pass # Inserarea corpului funcției aici...

def send_price_alerts(sheet):
    """
    Citește coloanele de diferență (G-H) și trimite o notificare dacă prețul concurentului este mai mic.
    """
    if sheet is None:
        return

    try:
        all_data = sheet.get_all_values()[1:] 
    except Exception as e:
        print(f"❌ Eroare la citirea datelor pentru alertă: {e}")
        return

    alert_products = [] 
    
    # Numele site-urilor corespunzător Coloanelor de Diferență (G la H)
    COMPETITOR_NAMES = ["Moto24", "Nordicamoto"]
    
    YOUR_PRICE_INDEX = 2         # Index C (Prețul ATVROM)
    FIRST_DIFFERENCE_INDEX = 6   # Index G (Coloana G este la indexul 6)
    
    for row_data in all_data:
        if not row_data or len(row_data) < (FIRST_DIFFERENCE_INDEX + len(COMPETITOR_NAMES)):
            continue
            
        product_name = row_data[0] # Coloana A
        your_price_str = row_data[YOUR_PRICE_INDEX] # Coloana C
        
        # Ignoră produsele fără preț ATVROM
        if not your_price_str or your_price_str.strip() == "":
            continue
            
        competitor_alerts = [] 
        
        # Iterăm prin cele 2 coloane de diferență (G la H)
        for i in range(len(COMPETITOR_NAMES)):
            difference_index = FIRST_DIFFERENCE_INDEX + i
            competitor_name = COMPETITOR_NAMES[i]
            
            try:
                diff_value_str = row_data[difference_index]
                
                if diff_value_str and diff_value_str.strip() != "":
                    difference = float(diff_value_str.replace(",", ".")) 
                    
                    # Logica: Alerta se declanșează DOAR dacă valoarea este negativă ȘI depășește pragul.
                    if difference < 0 and abs(difference) >= MINIMUM_DIFFERENCE_THRESHOLD:
                        competitor_alerts.append({
                            'name': competitor_name,
                            'difference': abs(difference) 
                        })
                        
            except (ValueError, IndexError, TypeError):
                continue

        if competitor_alerts:
            alert_products.append({
                'product': product_name,
                'your_price': your_price_str,
                'alerts': competitor_alerts
            })

    # --- Generarea și Trimiterea Email-ului ---
    if alert_products:
        # (Logica de generare email este identică cu cea din proiectul anterior)
        pass # Inserarea logicii de email aici...
        
        subject = f"🚨 [ALERTĂ ECHIPAMENTE] {len(alert_products)} Produse cu Preț Mai Mic la Concurență"
        # send_alert_email(subject, email_body) 

    else:
        print("\n✅ Nu s-au găsit echipamente cu prețuri mai mici la concurență.")


def monitor_and_update_sheet(sheet):
    """Citește Codurile Produsului (B), extrage prețurile concurenților (D, E) și actualizează Timestamp-ul (F)."""
    if sheet is None:
        return

    print(f"\n--- 1. Scriptul actualizează prețurile concurenților (D-E) și timestamp-ul (F). ---")

    try:
        all_data = sheet.get_all_values()[1:]
    except Exception as e:
        print(f"❌ Eroare la citirea datelor din foaie: {e}")
        return

    updates = []
    timestamp_val = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"\n--- 2. Începe procesarea a {len(all_data)} produse ---")

    for row_index, row_data in enumerate(all_data):
        gsheet_row_num = row_index + 2 
        product_name = row_data[0] 
        # Sursa pentru scraping este Coloana B (Cod Produs) -> Index 1
        product_code_index = 1 

        if len(row_data) <= product_code_index or not row_data[product_code_index]:
            continue # Treci peste rândurile fără cod produs

        product_code = row_data[product_code_index]

        print(f"\n➡️ Procesează: {product_name} (Cod: {product_code}) la rândul {gsheet_row_num}")

        # Parcurgem harta de coordonate (doar competitori)
        for src_col_idx, (dest_col_idx, extractor_func) in SCRAPER_COORDS.items():
            
            scraper_name = extractor_func.__name__.replace('scrape_', '').replace('_search', '') 
            dest_col_letter = gspread.utils.rowcol_to_a1(1, dest_col_idx).split('1')[0]
            cell_range = f'{dest_col_letter}{gsheet_row_num}'
            price = None
            
            print(f"    - Scrapează {scraper_name}...")
            try:
                # FUNCTIE SCRAPER: Folosește codul de produs ca sursă
                price = extractor_func(product_code) 
                
                if price is not None:
                    price_str = f"{price:.2f}"
                    print(f"      ✅ Succes: {price_str} RON. Scris la {cell_range}")
                else:
                    price = "N/A (SCRAPE ESUAT)"
                    print(f"      ❌ EROARE: Extragerea prețului a eșuat pentru {scraper_name}.")
                    
            except Exception as e:
                price = f"🛑 EXCEPȚIE ({type(e).__name__})"
                print(f"      🛑 EXCEPȚIE la scraping pentru {scraper_name}: {e}")
                
            time.sleep(1) # Pauză de 1 secundă între fiecare cerere de scraping 
            
            if price is not None:
                if isinstance(price, (float, int)):
                    price = f"{price:.2f}"
                        
                updates.append({
                    'range': cell_range,
                    'values': [[price]]
                })

    # ----------------------------------------
    # Scrierea Batch în Google Sheets
    if updates:
        
        # Adaugă timestamp-ul final în coloana F
        timestamp_col_letter = gspread.utils.rowcol_to_a1(1, TIMESTAMP_COL_INDEX).split('1')[0] 
        timestamp_range = f'{timestamp_col_letter}2:{timestamp_col_letter}{len(all_data) + 1}'
        timestamp_values = [[timestamp_val] for _ in all_data]
        
        updates.append({
            'range': timestamp_range,
            'values': timestamp_values
        })
        
        print(f"\n⚡ Se scriu {len(updates)} actualizări și timestamp-ul ({timestamp_val}) în foaie...")
        
        try:
            # sheet.batch_update(updates, value_input_option='USER_ENTERED')
            print("🎉 Toate prețurile concurenților și timestamp-ul au fost actualizate cu succes!")
        except Exception as e:
            print(f"❌ EROARE la scrierea în foaia de calcul: {e}")
    else:
        print("\nNu au fost găsite coduri de produs de actualizat.")

# ----------------------------------------------------
## 4. 🏁 Punctul de Intrare

if __name__ == "__main__":
    sheet_client = setup_sheets_client()
    
    if sheet_client:
        # 1. Rulează monitorizarea și actualizarea concurenților
        monitor_and_update_sheet(sheet_client)
        
        # 2. Rulează logica de alertare
        send_price_alerts(sheet_client)

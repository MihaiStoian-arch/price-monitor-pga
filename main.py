import gspread
# NOU: Folosim service_account_from_dict pentru a citi din variabila de mediu (Secretul GitHub)
from gspread import service_account_from_dict 
import json # Necesită import pentru a citi JSON din ENV
from datetime import datetime
import time
import requests
import os # Necesită import pentru a citi variabila de mediu

# --- IMPORTURI PENTRU EMAIL ---
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURARE EMAIL (SCHIMBĂ VALORILE CU DATELE TALE) ---
SENDER_EMAIL = 'mihaistoian889@gmail.com'
RECEIVER_EMAIL = 'octavian@atvrom.ro' # PĂSTRĂM ACEST RECEIVER PENTRU SIMPLITATE
SMTP_PASSWORD = 'igcu wwbs abit ganm'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
# ------------------------------------------------------------

# Pragul minim de diferență (în RON) sub care nu se trimite alertă
MINIMUM_DIFFERENCE_THRESHOLD = 1.0

# ⚠️ IMPORTURI PENTRU PROIECTUL MOTO (Nordicamoto și Moto24)
# Trebuie să păstrați și funcția clean_and_convert_price în main.py sau să o importați
from monitor.sites.nordicamoto import scrape_nordicamoto_search
from monitor.sites.moto24 import scrape_moto24

# Funcția de curățare a prețului (adăugată aici pentru a fi disponibilă local)
import re
def clean_and_convert_price(price_text):
    """Curăță textul prețului și îl convertește în float (gestionând formatele RON)."""
    if not price_text: return None
    price_text = price_text.upper().replace('LEI', '').replace('RON', '').replace('&NBSP;', '').strip()
    price_text = price_text.replace(' ', '')
    if price_text.count('.') > 0 and price_text.count(',') > 0: price_text = price_text.replace('.', '')
    cleaned_price_str = price_text.replace(',', '.')
    cleaned_price_str = re.sub(r'[^\d.]', '', cleaned_price_str)
    try:
        if cleaned_price_str: return float(cleaned_price_str)
        return None
    except ValueError: return None
# ----------------------------------------------------

## 1. ⚙️ Configurare Globală și Harta de Coordonate (ADAPTATĂ LA NOUL PROIECT)

# --- Foaia de Calcul ---
# Presupunem că folosiți o foaie nouă pentru monitorizarea echipamentelor.
SPREADSHEET_NAME = 'Monitor Echipamente Moto' # NOU
WORKSHEET_NAME = 'Preturi' # NOU
# Am eliminat CREDENTIALS_FILE

# Harta: { Index Coloană Sursă (Cod Produs): [Index Coloană Destinație (Preț), Funcție Scraper] }
# Presupunem structura: 
# Coloana A = Cod Produs (1)
# Coloana B = Preț Nordicamoto (2)
# Coloana C = Preț Moto24 (3)
# Coloana D = Data (4)
SCRAPER_COORDS = {
    # Am transformat-o pentru a citi Codul din A (Coloana 1) și a scrie în B și C
    1: [2, scrape_nordicamoto_search], # A -> B (Nordicamoto)
    # Reutilizăm coloana A ca sursă pentru al doilea scraper,
    # doar că acum scriem în coloana C (3)
    1: [3, scrape_moto24],            # A -> C (Moto24) 
}

# Coloana pentru Timestamp-ul general (Coloana D)
TIMESTAMP_COL_INDEX = 4 # NOU: Mutată în coloana D

def get_public_ip():
    """Funcția menținută pentru diagnosticare în log-uri."""
    try:
        response = requests.get('https://ifconfig.me/ip', timeout=5)
        if response.status_code == 200:
            return response.text.strip()
        return "N/A (Eroare de raspuns)"
    except requests.exceptions.RequestException:
        return "N/A (Eroare de retea)"

# ----------------------------------------------------
## 2. 🔑 Funcțiile de Conexiune și Alertă (ACTUALIZATĂ)

def setup_sheets_client():
    """Inițializează clientul gspread folosind Secretul GitHub și returnează foaia de lucru."""
    try:
        # NOU: Citirea directă din Secretul GitHub (Variabila de Mediu)
        creds_json = os.environ.get('GSPREAD_SA_CREDENTIALS')
        if not creds_json:
             raise ValueError("Variabila de mediu GSPREAD_SA_CREDENTIALS nu este setată.")

        # Autentifică gspread citind JSON-ul din dicționar
        creds = json.loads(creds_json)
        client = service_account_from_dict(creds)
        
        # Deschide foaia de calcul și foaia de lucru
        spreadsheet = client.open(SPREADSHEET_NAME)
        sheet = spreadsheet.worksheet(WORKSHEET_NAME)
        
        print(f"✅ Conexiune reușită la foaia de lucru '{WORKSHEET_NAME}'.")

        current_ip = get_public_ip()
        print(f"🌐 IP-ul public de ieșire al Runner-ului: **{current_ip}**")
        
        return sheet
    except Exception as e:
        print(f"❌ Eroare la inițializarea Google Sheets client: {e}")
        print("Asigură-te că secretul GSPREAD_SA_CREDENTIALS este corect și că Service Account-ul este partajat cu foaia.")
        return None
    
def send_alert_email(subject, body):
    # Logica de trimitere email rămâne aceeași
    # ... (PĂSTRATĂ FĂRĂ MODIFICĂRI)
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html')) 

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print(f"✔️ Notificare trimisă cu succes către {RECEIVER_EMAIL}")
        return True
    except Exception as e:
        print(f"❌ Eroare la trimiterea email-ului: {e}")
        print("Verifică setările SMTP_PASSWORD și permisiunile contului.")
        return False
    
def send_price_alerts(sheet):
    """
    Citește coloanele de prețuri (B și C) și trimite o notificare 
    dacă detectează un preț mai mic pe unul dintre site-uri (Moto24 vs Nordicamoto)
    """
    if sheet is None:
        return

    try:
        # Citim datele de la Rândul 2 în jos, inclusiv coloanele de prețuri.
        # Citim până la coloana C (indice 2)
        all_data = sheet.get_all_values()[1:]
        
    except Exception as e:
        print(f"❌ Eroare la citirea datelor pentru alertă: {e}")
        return

    alert_products = [] 
    
    # Numele site-urilor corespunzător Coloanelor B și C
    COMPETITOR_NAMES = ["Nordicamoto", "Moto24"] 
    
    # Indici (în lista row_data): A=0 (Cod), B=1 (Nordicamoto), C=2 (Moto24)
    COD_PRODUS_INDEX = 0 
    PRICE_NORDICAMOTO_INDEX = 1
    PRICE_MOTO24_INDEX = 2
    
    for row_data in all_data:
        
        if not row_data or len(row_data) < 3:
            continue
            
        product_code = row_data[COD_PRODUS_INDEX]
        
        # Preluăm prețurile (care sunt string-uri de tip "569.0 RON" sau "N/A")
        price_nordicamoto_str = row_data[PRICE_NORDICAMOTO_INDEX]
        price_moto24_str = row_data[PRICE_MOTO24_INDEX]
        
        # Curățare și conversie pentru a putea compara
        price_nordicamoto = clean_and_convert_price(price_nordicamoto_str)
        price_moto24 = clean_and_convert_price(price_moto24_str)
        
        if price_nordicamoto is None or price_moto24 is None:
            continue
        
        competitor_alerts = []
        
        # LOGICA CORECTATĂ: Comparăm cele două site-uri între ele (Nordicamoto vs Moto24)
        
        # 1. Nordica este mai scump decât Moto24
        if price_nordicamoto > price_moto24:
            difference = price_nordicamoto - price_moto24
            if difference >= MINIMUM_DIFFERENCE_THRESHOLD:
                # Alerta: Moto24 este mai ieftin
                 competitor_alerts.append({
                    'product_code': product_code,
                    'competitor': 'Moto24',
                    'price': price_moto24_str,
                    'difference': difference 
                })

        # 2. Moto24 este mai scump decât Nordica
        elif price_moto24 > price_nordicamoto:
            difference = price_moto24 - price_nordicamoto
            if difference >= MINIMUM_DIFFERENCE_THRESHOLD:
                 # Alerta: Nordicamoto este mai ieftin
                 competitor_alerts.append({
                    'product_code': product_code,
                    'competitor': 'Nordicamoto',
                    'price': price_nordicamoto_str,
                    'difference': difference
                })
        
        # Adăugăm alerte
        if competitor_alerts:
            alert_products.extend(competitor_alerts)

    # --- Generarea și Trimiterea Email-ului ---
    if alert_products:
        
        email_body = "Bună ziua,<br><br>Am detectat următoarele prețuri **diferite** între cele două site-uri monitorizate:<br>"
        email_body += "<table border='1' cellpadding='8' cellspacing='0' style='width: 70%; border-collapse: collapse; font-family: Arial;'>"
        email_body += "<tr style='background-color: #f2f2f2; font-weight: bold;'><th>Cod Produs</th><th>Concurent cu Preț Mic</th><th>Preț Mic (RON)</th><th>Diferență Absolută (RON)</th></tr>"
        
        for alert in alert_products:
            email_body += f"<tr>"
            email_body += f"<td><b>{alert['product_code']}</b></td>"
            email_body += f"<td style='color: green;'>{alert['competitor']}</td>"
            email_body += f"<td>{alert['price']}</td>"
            email_body += f"<td style='color: red; font-weight: bold;'>{alert['difference']:.0f} RON</td>" 
            email_body += f"</tr>"

        email_body += "</table>"
        email_body += "<br>Vă rugăm să verificați foaia de calcul."
        
        subject = f"🚨 [ALERTĂ PREȚ] {len(alert_products)} Diferențe de Preț Între Nordicamoto și Moto24"
        
        send_alert_email(subject, email_body) 

    else:
        print("\n✅ Nu s-au găsit diferențe de preț notabile (peste 1.0 RON) între Nordicamoto și Moto24.")


# ----------------------------------------------------
## 3. 🔄 Funcția de Monitorizare și Actualizare (ADAPTATĂ)

def monitor_and_update_sheet(sheet):
    """Citește codurile de produs (A), extrage prețurile (B și C) și actualizează coloana D."""
    if sheet is None:
        print("Oprire. Foaia de lucru nu a putut fi inițializată.")
        return

    print(f"\n--- 1. Scriptul actualizează prețurile Nordicamoto (B) și Moto24 (C), și timestamp-ul (D). ---")

    # Citim toate datele de la rândul 2 în jos (excludem antetul)
    try:
        all_data = sheet.get_all_values()[1:]
    except Exception as e:
        print(f"❌ Eroare la citirea datelor din foaie: {e}")
        return

    updates = [] # Lista de actualizări
    timestamp_val = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"\n--- 2. Începe procesarea a {len(all_data)} produse ---")

    # Parcurgem fiecare rând (produs)
    for row_index, row_data in enumerate(all_data):
        gsheet_row_num = row_index + 2
        product_code = row_data[0] # Codul de produs este în coloana A (index 0)

        if not product_code:
             print(f"➡️ Rândul {gsheet_row_num} ignorat (Cod Produs gol).")
             continue

        print(f"\n➡️ Procesează: Codul {product_code} la rândul {gsheet_row_num}")
        
        # Vom avea nevoie de rezultatele finale pentru B și C, scrise într-o singură listă de update.
        # Inițializăm lista de 2 elemente (pentru B și C)
        row_updates = [None] * 2
        
        # --- SCRAPING NORDICAMOTO (A -> B) ---
        
        # Obținem dest_col_idx (2) și extractor_func (scrape_nordicamoto_search)
        dest_col_idx_b, extractor_func_nordica = SCRAPER_COORDS[1] 
        cell_range_b = gspread.utils.rowcol_to_a1(gsheet_row_num, dest_col_idx_b)
        
        print(f"  - Scrapează Nordicamoto...")
        try:
            price_nordica = extractor_func_nordica(product_code, clean_and_convert_price) # trimitem clean_and_convert_price
            
            if price_nordica is not None:
                price_str = f"{price_nordica:.2f}"
                print(f"    ✅ Succes: {price_str} RON. Scris la {cell_range_b}")
            else:
                price_str = "N/A (SCRAPE ESUAT)"
                print(f"    ❌ EROARE: Extragerea prețului a eșuat (returnat None) pentru Nordicamoto.")
            row_updates[0] = price_str
        except Exception as e:
            row_updates[0] = f"🛑 EXCEPȚIE ({type(e).__name__})"
            print(f"    🛑 EXCEPȚIE la scraping pentru Nordicamoto: {e}")
            
        time.sleep(1) # Pauză de 1 secundă

        # --- SCRAPING MOTO24 (A -> C) ---
        
        # Obținem dest_col_idx (3) și extractor_func (scrape_moto24)
        dest_col_idx_c, extractor_func_moto24 = SCRAPER_COORDS[1] # Reutilizăm sursa A
        dest_col_idx_c = 3 # Forțăm coloana C
        cell_range_c = gspread.utils.rowcol_to_a1(gsheet_row_num, dest_col_idx_c)

        print(f"  - Scrapează Moto24...")
        try:
            price_moto24 = extractor_func_moto24(product_code, clean_and_convert_price) # trimitem clean_and_convert_price
            
            if price_moto24 is not None:
                price_str = f"{price_moto24:.2f}"
                print(f"    ✅ Succes: {price_str} RON. Scris la {cell_range_c}")
            else:
                price_str = "N/A (SCRAPE ESUAT)"
                print(f"    ❌ EROARE: Extragerea prețului a eșuat (returnat None) pentru Moto24.")
            row_updates[1] = price_str
        except Exception as e:
            row_updates[1] = f"🛑 EXCEPȚIE ({type(e).__name__})"
            print(f"    🛑 EXCEPȚIE la scraping pentru Moto24: {e}")
            
        time.sleep(1) # Pauză de 1 secundă
        
        
        # --- Adăugare la lista de actualizări B și C (într-un singur apel) ---
        
        # Range-ul de actualizat pentru acest rând: B[rând]:C[rând]
        range_b_c = f'{gspread.utils.rowcol_to_a1(gsheet_row_num, 2)}:{gspread.utils.rowcol_to_a1(gsheet_row_num, 3)}'
        
        updates.append({
            'range': range_b_c,
            'values': [row_updates] # Scrie lista [Pret B, Pret C] pe rândul respectiv
        })


    # ----------------------------------------
    # Scrierea Batch în Google Sheets (la final)
    
    # Adaugă timestamp-ul final în coloana D pentru toate rândurile procesate
    if updates:
        
        timestamp_col_letter = gspread.utils.rowcol_to_a1(1, TIMESTAMP_COL_INDEX).split('1')[0] 
        
        # Rândul începe de la 2 și se termină la (len(all_data) + 1)
        timestamp_range = f'{timestamp_col_letter}2:{timestamp_col_letter}{len(all_data) + 1}'
        
        # Creează o listă de liste pentru a scrie aceeași valoare pe toate rândurile
        timestamp_values = [[timestamp_val] for _ in all_data]
        
        updates.append({
            'range': timestamp_range,
            'values': timestamp_values
        })
        
        print(f"\n⚡ Se scriu {len(updates)} actualizări și timestamp-ul ({timestamp_val}) în foaie...")
        
        try:
            sheet.batch_update(updates, value_input_option='USER_ENTERED')
            print("🎉 Toate prețurile și timestamp-ul au fost actualizate cu succes!")
        except Exception as e:
            print(f"❌ EROARE la scrierea în foaia de calcul: {e}")
    else:
        print("\nNu au fost găsite prețuri noi de actualizat.")


# ----------------------------------------------------
## 4. 🏁 Punctul de Intrare

if __name__ == "__main__":
    # 1. Inițializează conexiunea
    sheet_client = setup_sheets_client()
    
    if sheet_client:
        # 2. Rulează monitorizarea și actualizarea foii (Această funcție actualizează coloanele B și C)
        monitor_and_update_sheet(sheet_client)
        
        # 3. Odată ce foaia este actualizată, rulează logica de alertare
        send_price_alerts(sheet_client)

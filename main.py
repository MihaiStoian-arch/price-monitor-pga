import gspread
import json 
from datetime import datetime
import time
import requests
import os
import re 

# --- IMPORTURI PENTRU EMAIL ---
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ⚠️ IMPORTĂRILE FUNCȚIILOR DE SCRAPING
from monitor.sites.nordicamoto import scrape_nordicamoto_search
from monitor.sites.moto24 import scrape_moto24_search 

# --- CONFIGURARE EMAIL ---
SENDER_EMAIL = 'mihaistoian889@gmail.com'
RECEIVER_EMAIL = 'octavian@atvrom.ro'
# ATENȚIE: SMTP_PASSWORD ar trebui setat ca variabilă de mediu în GitHub Actions
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'igcu wwbs abit ganm') 
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
# ------------------------------------------------------------

# Pragul minim de diferență (în RON) sub care nu se trimite alertă
MINIMUM_DIFFERENCE_THRESHOLD = 1.0

# ----------------------------------------------------
## 1. ⚙️ Configurare Globală și Harta de Coordonate 

# --- Foaia de Calcul ---
SPREADSHEET_NAME = 'Price Monitor ATVRom'
WORKSHEET_NAME = 'Echipamente HJC' 

# Coloanele relevante (indexarea începe de la 1):
# A=1 (Titlu Produs), B=2 (Cod Produs), C=3 (Preț ATVROM), 
# D=4 (Preț Moto24), E=5 (Preț Nordicamoto), F=6 (Data Scrape)
# G=7 (Diferența Moto24), H=8 (Diferența Nordicamoto)

# Harta: Folosim doar pentru referință, nu pentru preluarea funcțiilor (pentru a evita IndexError)
SCRAPER_COORDS = {
    2: [4, scrape_moto24_search],        # B -> D (Moto24) 
    2: [5, scrape_nordicamoto_search], # B -> E (Nordicamoto) 
}

# Coloana pentru Timestamp-ul (Coloana F)
TIMESTAMP_COL_INDEX = 6

# Indicii pentru Coloane în lista de date (indexarea începe de la 0):
COD_PRODUS_INDEX = 1        # Coloana B
TITLE_PRODUS_INDEX = 0      # Coloana A
LAST_PRICE_ATVROM_INDEX = 2 # Coloana C
PRICE_MOTO24_INDEX = 3      # Coloana D
PRICE_NORDICAMOTO_INDEX = 4 # Coloana E
DIFFERENCE_MOTO24_INDEX = 6 # Coloana G (pentru alerte)
DIFFERENCE_NORDICAMOTO_INDEX = 7 # Coloana H (pentru alerte)


def clean_and_convert_price(price_text):
    """
    Curăță textul prețului și îl convertește în float, gestionând 
    formatele regionale (spații/puncte pentru mii, virgulă pentru zecimale sau mii).
    """
    if not price_text:
        return None
    
    price_text = price_text.upper().replace('LEI', '').replace('RON', '').replace('&NBSP;', '').strip()
    
    # Eliminăm spațiile folosite ca separator de mii (e.g., 2 947)
    price_text = price_text.replace(' ', '')
    
    # 1. Gestionăm virgula:
    if ',' in price_text:
        parts = price_text.split(',')
        
        # Dacă există două părți ȘI partea de după virgulă are mai mult de 2 cifre (e.g., 2,947)
        # sau nu există puncte (separator de mii), virgula este un separator de mii.
        # În acest caz, o eliminăm (2,947 -> 2947).
        if len(parts) == 2 and (len(parts[1]) > 2 or '.' not in price_text):
            price_text = price_text.replace(',', '')
        
        # Altfel, dacă virgula este separator zecimal (e.g., 2947,50), o transformăm în punct.
        else:
            price_text = price_text.replace(',', '.')

    # 2. Eliminăm punctele care au rămas (sunt separatori de mii)
    # Ex: 2.947 -> 2947
    # Dacă prețul conține deja un punct (acum zecimal), nu mai eliminăm puncte.
    if price_text.count('.') > 1:
        # Dacă există mai mult de un punct, eliminăm primul (separator de mii)
        price_text = price_text.replace('.', '', price_text.count('.') - 1)
    
    # Eliminăm orice alt caracter non-numeric sau non-punct
    cleaned_price_str = re.sub(r'[^\d.]', '', price_text)
    
    try:
        if cleaned_price_str:
            return float(cleaned_price_str)
        return None
    except ValueError:
        return None


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
## 2. 🔑 Funcțiile de Conexiune și Alertă

def setup_sheets_client():
    """Inițializează clientul gspread folosind Secretul GitHub și returnează foaia de lucru."""
    try:
        creds_json = os.environ.get('GSPREAD_SA_CREDENTIALS')
        if not creds_json:
             raise ValueError("Variabila de mediu GSPREAD_SA_CREDENTIALS nu este setată.")

        creds = json.loads(creds_json)
        client = gspread.service_account_from_dict(creds) 
        
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
    """Trimite un email folosind SMTP."""
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
    Citește coloanele de diferență (G și H) calculate de formulele din foaie
    și trimite o notificare dacă găsește diferențe negative care depășesc pragul.
    """
    if sheet is None:
        return

    print("\n--- 3. Verificare Alerte (Citire Coloane G și H) ---")
    try:
        # Citim toate datele necesare (A-H). Presupunem că citim până la H (index 7)
        all_data = sheet.get_all_values()[1:] 
    except Exception as e:
        print(f"❌ Eroare la citirea datelor pentru alertă: {e}")
        return

    alert_products = [] 
    
    DIFFERENCE_COLUMNS = [
        (DIFFERENCE_MOTO24_INDEX, "Moto24", PRICE_MOTO24_INDEX), 
        (DIFFERENCE_NORDICAMOTO_INDEX, "Nordicamoto", PRICE_NORDICAMOTO_INDEX)
    ]
    
    for row_data in all_data:
        
        if not row_data or len(row_data) < 8: 
            continue
            
        product_title = row_data[TITLE_PRODUS_INDEX]
        atvrom_price_str = row_data[LAST_PRICE_ATVROM_INDEX]
        
        for diff_index, competitor_name, price_index in DIFFERENCE_COLUMNS:
            
            diff_value_str = row_data[diff_index]
            
            try:
                if diff_value_str and diff_value_str.strip() != "":
                    # Sheets returnează numerele formatate regional. Convertim ',' la '.'
                    difference = float(diff_value_str.replace(",", ".")) 
                    
                    # Logica: Valoarea este negativă (competitorul e mai ieftin) ȘI depășește pragul
                    if difference < 0 and abs(difference) >= MINIMUM_DIFFERENCE_THRESHOLD:
                        
                        competitor_price_str = row_data[price_index]
                        
                        alert_products.append({
                            'product': product_title,
                            'your_price': atvrom_price_str,
                            'competitor': competitor_name,
                            'competitor_price': competitor_price_str,
                            'difference': abs(difference) 
                        })
                        
            except (ValueError, IndexError, TypeError):
                continue

    # --- Generarea și Trimiterea Email-ului ---
    if alert_products:
        
        email_body = "Bună ziua,<br><br>Am detectat următoarele prețuri **mai mici la concurență**:<br>"
        email_body += "<table border='1' cellpadding='8' cellspacing='0' style='width: 90%; border-collapse: collapse; font-family: Arial;'>"
        email_body += "<tr style='background-color: #f2f2f2; font-weight: bold;'><th>Produs</th><th>Prețul Tău (C)</th><th>Concurent</th><th>Prețul Concurent (D/E)</th><th>Diferență (RON)</th></tr>"
        
        for alert in alert_products:
            email_body += f"<tr>"
            email_body += f"<td><b>{alert['product']}</b></td>"
            email_body += f"<td style='color: green;'>{alert['your_price']}</td>"
            email_body += f"<td>{alert['competitor']}</td>"
            email_body += f"<td style='color: red;'>{alert['competitor_price']}</td>"
            email_body += f"<td style='color: red; font-weight: bold;'>{alert['difference']:.0f} RON mai mic</td>" 
            email_body += f"</tr>"

        email_body += "</table>"
        email_body += "<br>Vă rugăm să revizuiți strategia de preț."
        
        subject = f"🚨 [ALERTĂ PREȚ] {len(alert_products)} Produse HJC cu Preț Mai Mic la Concurență"
        
        send_alert_email(subject, email_body) 

    else:
        print("\n✅ Nu s-au găsit produse cu prețuri mai mici la concurență.")


# ----------------------------------------------------
## 3. 🔄 Funcția de Monitorizare și Actualizare

def monitor_and_update_sheet(sheet):
    """Citește codurile de produs (B), extrage prețurile (D și E) și actualizează coloana F."""
    if sheet is None:
        print("Oprire. Foaia de lucru nu a putut fi inițializată.")
        return

    print(f"\n--- 1. Scriptul actualizează prețurile Moto24 (D) și Nordicamoto (E), și timestamp-ul (F). ---")

    try:
        # Citim datele de la rândul 2 în jos (excludem antetul)
        all_data = sheet.get_all_values()[1:] 
    except Exception as e:
        print(f"❌ Eroare la citirea datelor din foaie: {e}")
        return

    updates = []
    timestamp_val = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"\n--- 2. Începe procesarea a {len(all_data)} produse ---")

    for row_index, row_data in enumerate(all_data):
        gsheet_row_num = row_index + 2
        
        product_code = row_data[COD_PRODUS_INDEX].strip()

        if not product_code:
             print(f"➡️ Rândul {gsheet_row_num} ignorat (Cod Produs gol).")
             continue

        print(f"\n➡️ Procesează: Codul {product_code} la rândul {gsheet_row_num}")
        
        # ⬅️ CORECTAT: Preluarea funcțiilor de scraping direct
        scraper_info = [
            (scrape_moto24_search, 4),      # Moto24 (Coloana D)
            (scrape_nordicamoto_search, 5)  # Nordicamoto (Coloana E)
        ]
        
        row_updates = [None] * 2
        
        # Iterăm prin cele două scrape-uri necesare: D (Moto24) și E (Nordicamoto)
        for i, (scraper_func, col_index) in enumerate(scraper_info):
            site_name = "Moto24" if col_index == 4 else "Nordicamoto"
            
            print(f"  - Scrapează {site_name}...")
            try:
                # Apelăm funcția de scraping
                price_float = scraper_func(product_code) 
                
                if price_float is not None:
                    # Asigurăm formatarea corectă pentru GSheets
                    price_str = f"{price_float:.2f}"
                    print(f"    ✅ Succes {site_name}: {price_str} RON.")
                else:
                    price_str = "N/A (SCRAPE ESUAT)"
                    print(f"    ❌ EROARE {site_name}: Extragerea prețului a eșuat (returnat None).")
                    
                row_updates[i] = price_str
            except Exception as e:
                row_updates[i] = f"🛑 EXCEPȚIE ({type(e).__name__})"
                print(f"    🛑 EXCEPȚIE {site_name}: {e}")
            
            time.sleep(1) 
        
        # --- Adăugare la lista de actualizări D și E (într-un singur apel) ---
        range_d_e = f'{gspread.utils.rowcol_to_a1(gsheet_row_num, 4)}:{gspread.utils.rowcol_to_a1(gsheet_row_num, 5)}'
        
        updates.append({
            'range': range_d_e,
            'values': [row_updates] # Scrie lista [Pret D, Pret E] pe rândul respectiv
        })


    # ----------------------------------------
    # Scrierea Batch în Google Sheets (la final)
    
    if updates:
        
        # Adaugă timestamp-ul final în coloana F (index 6) pentru toate rândurile procesate
        timestamp_col_letter = gspread.utils.rowcol_to_a1(1, TIMESTAMP_COL_INDEX).split('1')[0] 
        timestamp_range = f'{timestamp_col_letter}2:{timestamp_col_letter}{len(all_data) + 1}'
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
        # 2. Rulează monitorizarea și actualizarea foii (D, E, F)
        monitor_and_update_sheet(sheet_client)
        
        # 3. Odată ce foaia este actualizată, rulează logica de alertare (G, H)
        # Pauză de 5 secunde pentru a permite formulelor G și H să se recalculeze în Sheets
        time.sleep(5) 
        send_price_alerts(sheet_client)

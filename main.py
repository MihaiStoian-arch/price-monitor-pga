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
# Asigură-te că funcțiile sunt importate corect din directorul monitor/sites
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

# CORECȚIE CRITICĂ: Folosim o listă pentru a evita suprascrierea cheilor
# Format: (Source Column Index, Destination Column Index, Scraper Function, Scraper Name)
# Coloana B (Cod Produs) = 2, D (Moto24) = 4, E (Nordicamoto) = 5
COMPETITOR_MAPPINGS = [
    # Source Index 2 (Cod Produs) -> Destination Index 4 (Preț Moto24)
    (2, 4, scrape_moto24_search, "Moto24"),             
    # Source Index 2 (Cod Produs) -> Destination Index 5 (Preț Nordicamoto)
    (2, 5, scrape_nordicamoto_search, "Nordicamoto"),   
]

# Coloana pentru Timestamp-ul general (Coloana F)
TIMESTAMP_COL_INDEX = 6

# ----------------------------------------------------
## 2. 🔑 Funcțiile de Conexiune și Alertă (Logica se păstrează de la proiectul anterior)

def get_public_ip():
    # ... (corpul funcției) ...
    try:
        response = requests.get('https://ifconfig.me/ip', timeout=5)
        if response.status_code == 200:
            return response.text.strip()
        return "N/A (Eroare de raspuns)"
    except requests.exceptions.RequestException:
        return "N/A (Eroare de retea)"

def setup_sheets_client():
    # ... (corpul funcției) ...
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open(SPREADSHEET_NAME)
        sheet = spreadsheet.worksheet(WORKSHEET_NAME)
        
        print(f"✅ Conexiune reușită la foaia de lucru '{WORKSHEET_NAME}'.")

        current_ip = get_public_ip()
        print(f"🌐 IP-ul public de ieșire al Runner-ului: **{current_ip}**")
        
        return sheet
    except Exception as e:
        print(f"❌ Eroare la inițializarea Google Sheets client: {e}")
        return None
    
def send_alert_email(subject, body):
    # ... (corpul funcției) ...
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
        return False
    
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
        
        if not your_price_str or your_price_str.strip() == "":
            continue
            
        competitor_alerts = [] 
        
        for i in range(len(COMPETITOR_NAMES)):
            difference_index = FIRST_DIFFERENCE_INDEX + i
            competitor_name = COMPETITOR_NAMES[i]
            
            try:
                diff_value_str = row_data[difference_index]
                
                if diff_value_str and diff_value_str.strip() != "":
                    # Sheets returnează numerele formatate regional (ex: 123,45)
                    difference = float(diff_value_str.replace(",", ".")) 
                    
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
        
        email_body = "Bună ziua,<br><br>Am detectat următoarele prețuri **mai mici la concurență** pentru echipamente:<br>"
        email_body += "<table border='1' cellpadding='8' cellspacing='0' style='width: 70%; border-collapse: collapse; font-family: Arial;'>"
        email_body += "<tr style='background-color: #f2f2f2; font-weight: bold;'><th>Produs</th><th>Cod Produs</th><th>Prețul Tău (RON)</th><th>Concurent</th><th>Diferență (RON)</th></tr>"
        
        YOUR_CODE_INDEX = 1 # Coloana B
        
        for product_alert in alert_products:
            is_first_alert = True
            
            # Recitirea rândului complet pentru a obține Codul Produsului
            # Aici presupunem că row_data este încă disponibil, dar cel mai sigur ar fi să-l extragem din nou
            # Sau să includem Codul Produsului în alert_products
            
            # Deoarece nu am re-citit datele, vom folosi un placeholder. 
            # Pentru simplitate, presupunem că prima linie din sheet (index 1) este Titlu
            product_code = "N/A" # Va trebui să extrageți codul din coloana B
            
            # Căutăm codul produsului în datele brute
            for row in all_data:
                if row[0] == product_alert['product']:
                    product_code = row[YOUR_CODE_INDEX]
                    break
            
            for alert in product_alert['alerts']:
                if is_first_alert:
                    row_span = len(product_alert['alerts'])
                    email_body += f"<tr>"
                    email_body += f"<td rowspan='{row_span}'><b>{product_alert['product']}</b></td>"
                    email_body += f"<td rowspan='{row_span}' style='color: blue;'>{product_code}</td>"
                    email_body += f"<td rowspan='{row_span}' style='color: green;'>{product_alert['your_price']}</td>"
                    is_first_alert = False
                else:
                    email_body += f"<tr>"
                    
                email_body += f"<td>{alert['name']}</td>"
                email_body += f"<td style='color: red; font-weight: bold;'>{alert['difference']:.0f} RON mai mic</td>" 
                email_body += f"</tr>"

        email_body += "</table>"
        email_body += "<br>Vă rugăm să revizuiți strategia de preț."
        
        subject = f"🚨 [ALERTĂ ECHIPAMENTE] {len(alert_products)} Produse cu Preț Mai Mic la Concurență"
        
        send_alert_email(subject, email_body) 

    else:
        print("\n✅ Nu s-au găsit echipamente cu prețuri mai mici la concurență.")


def monitor_and_update_sheet(sheet):
    """Citește Codurile Produsului (B), extrage prețurile concurenților (D, E) și actualizează Timestamp-ul (F)."""
    if sheet is None:
        print("Oprire. Foaia de lucru nu a putut fi inițializată.")
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
            continue 

        product_code = row_data[product_code_index]

        print(f"\n➡️ Procesează: {product_name} (Cod: {product_code}) la rândul {gsheet_row_num}")

        # Iterăm prin noua listă de mapări
        for src_col_idx, dest_col_idx, extractor_func, scraper_name in COMPETITOR_MAPPINGS:
            
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
                
            time.sleep(1) 
            
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
        monitor_and_update_sheet(sheet_client)
        send_price_alerts(sheet_client)

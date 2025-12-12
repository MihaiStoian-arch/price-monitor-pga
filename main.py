import os
import json
import re
import gspread # Biblioteca pentru Google Sheets
from datetime import datetime

# Importăm funcțiile de scraping (Păstrăm funcția clean_and_convert_price aici)
from monitor.sites.nordicamoto import scrape_nordicamoto_search
from monitor.sites.moto24 import scrape_moto24_search

# --- FUNCTII DE UTILITATE ---
def clean_and_convert_price(price_text):
    """Curăță textul prețului și îl convertește în float (gestionând formatele RON)."""
    # ... Păstrați codul funcției clean_and_convert_price aici, este identic cu cel anterior
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


def setup_google_sheet(sheet_name, worksheet_name="Preturi"):
    """Autentifică gspread folosind secretul din GitHub și deschide foaia de lucru."""
    try:
        # 1. Obține credentialele din variabila de mediu (Secretul GitHub)
        creds_json = os.environ.get('GSPREAD_SA_CREDENTIALS')
        if not creds_json:
            raise ValueError("Variabila de mediu GSPREAD_SA_CREDENTIALS nu a fost setată.")

        # 2. Creează un fișier temporar cu credențialele
        creds = json.loads(creds_json)
        
        # 3. Autentifică gspread
        gc = gspread.service_account_from_dict(creds)
        
        # 4. Deschide Spreadsheet-ul și Foaia de lucru
        spreadsheet = gc.open(sheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        
        return worksheet
        
    except Exception as e:
        print(f"❌ EROARE GSPREAD: Nu s-a putut conecta/deschide foaia: {e}")
        return None


# --- FUNCTIA PRINCIPALĂ DE MONITORIZARE ---
def run_monitor():
    
    # !!! ATENȚIE: MODIFICAȚI ACESTEA !!!
    GOOGLE_SHEET_NAME = "Monitor Echipamente Moto" # Numele foii dvs.
    WORKSHEET_NAME = "Preturi" # Numele foii de lucru (tab-ul din partea de jos)
    # !!! ASIGURAȚI-VĂ că adresa de email a Service Account-ului este invitată ca editor la acest Google Sheet!

    # Coloane: A = Cod Produs | B = Pret Nordicamoto | C = Pret Moto24 | D = Data
    
    worksheet = setup_google_sheet(GOOGLE_SHEET_NAME, WORKSHEET_NAME)
    if not worksheet:
        return

    print(f"✅ Conectat la Google Sheet: {GOOGLE_SHEET_NAME} / {WORKSHEET_NAME}")
    
    try:
        # 1. Obține toate codurile de produs din coloana A (Cod Produs)
        # Să presupunem că antetul este pe linia 1. Începem de la linia 2.
        product_codes_list = worksheet.col_values(1)[1:] 
        
        # 2. Pregătește datele de actualizare
        update_data = []
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"Încep procesarea pentru {len(product_codes_list)} coduri de produs...")
        
        # Iterăm prin fiecare cod de produs, începând cu linia 2 (index 0)
        for index, product_code in enumerate(product_codes_list):
            
            row_number = index + 2 # Rândul din Google Sheet (începe de la 2)
            product_code = product_code.strip()
            
            if not product_code:
                update_data.append(["", "", current_date]) # Lasă rândul gol dacă nu are cod
                continue

            print(f"\n[{row_number}] Procesez Codul: {product_code}")
            
            # --- SCRAPING NORDICAMOTO ---
            price_nordicamoto = scrape_nordicamoto_search(product_code, clean_and_convert_price)
            
            # --- SCRAPING MOTO24 ---
            price_moto24 = scrape_moto24_search(product_code, clean_and_convert_price)

            # 3. Adaugă rezultatele la lista de actualizare
            # Coloana B (Nordicamoto), Coloana C (Moto24), Coloana D (Data)
            
            # Formatează prețul pentru GSheets (înlocuiește None cu text)
            price_nordicamoto_str = f"{price_nordicamoto} RON" if price_nordicamoto is not None else "N/A"
            price_moto24_str = f"{price_moto24} RON" if price_moto24 is not None else "N/A"
            
            update_data.append([
                price_nordicamoto_str,  # Coloana B
                price_moto24_str,       # Coloana C
                current_date            # Coloana D
            ])
        
        # 4. Trimite datele înapoi la Google Sheet (Actualizare în masă)
        
        # Definirea range-ului de actualizat: B2:D[Ultimul rând]
        end_row = len(product_codes_list) + 1 
        range_to_update = f'B2:D{end_row}'
        
        print(f"\n📦 Trimit {len(update_data)} rânduri către Google Sheet, range: {range_to_update}")
        
        worksheet.update(
            range_to_update,
            update_data,
            value_input_option='USER_ENTERED' # Păstrează formatarea GSheet
        )
        
        print("🎉 Monitorizarea a fost finalizată cu succes!")


    except Exception as e:
        print(f"❌ EROARE CRITICĂ la rularea monitorului: {e}")


if __name__ == "__main__":
    run_monitor()

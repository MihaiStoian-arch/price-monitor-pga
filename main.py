from monitor.sites.nordicamoto import scrape_nordicamoto_search
from monitor.sites.moto24 import scrape_moto24_search
import re

# Această funcție este esențială și trebuie să fie definită undeva,
# cel mai bine în main.py sau într-un fișier utility.
def clean_and_convert_price(price_text):
    """Curăță textul prețului și îl convertește în float (gestionând formatele RON)."""
    if not price_text: return None
    
    price_text = price_text.upper().replace('LEI', '').replace('RON', '').replace('&NBSP;', '').strip()
    
    # Eliminăm spațiile
    price_text = price_text.replace(' ', '')
    
    # Dacă conține și punct și virgulă, eliminăm punctele (separator de mii)
    if price_text.count('.') > 0 and price_text.count(',') > 0: price_text = price_text.replace('.', '')
        
    # Standardizăm separatorul zecimal la punct
    cleaned_price_str = price_text.replace(',', '.')
    
    # Eliminăm orice alt caracter non-numeric sau non-punct
    cleaned_price_str = re.sub(r'[^\d.]', '', cleaned_price_str)
    
    try:
        if cleaned_price_str:
            return float(cleaned_price_str)
        return None
    except ValueError:
        return None

# --- EXECUTIE TEST ---
# Folosim codul care știm că ar trebui să existe pe site-uri
PRODUCT_CODE = 'HJC100530-XS'

if __name__ == "__main__":
    print("--- INCEP TESTUL DE SCRAPING (PLAYWRIGHT) ---")
    
    # Nordicamoto (Folosește funcția din monitor/sites/nordicamoto.py)
    print(f"\n--- TEST NORDICAMOTO ---")
    price_nordicamoto = scrape_nordicamoto_search(PRODUCT_CODE)
    print(f"REZULTAT NORDICAMOTO FINAL: {price_nordicamoto}")

    # Moto24 (Folosește funcția din monitor/sites/moto24.py)
    print(f"\n--- TEST MOTO24 ---")
    price_moto24 = scrape_moto24_search(PRODUCT_CODE)
    print(f"REZULTAT MOTO24 FINAL: {price_moto24}")

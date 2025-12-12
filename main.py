import re
from monitor.sites.nordicamoto import scrape_nordicamoto_search
from monitor.sites.moto24 import scrape_moto24_search

# Funcția de curățare a prețului este necesară pentru toate site-urile
def clean_and_convert_price(price_text):
    """Curăță textul prețului și îl convertește în float (gestionând formatele RON)."""
    if not price_text: return None
    
    price_text = price_text.upper().replace('LEI', '').replace('RON', '').replace('&NBSP;', '').strip()
    
    # 1. Eliminăm spațiile
    price_text = price_text.replace(' ', '')
    
    # 2. Dacă conține și punct și virgulă, eliminăm punctele (separator de mii)
    if price_text.count('.') > 0 and price_text.count(',') > 0: price_text = price_text.replace('.', '')
        
    # 3. Standardizăm separatorul zecimal la punct
    cleaned_price_str = price_text.replace(',', '.')
    
    # 4. Eliminăm orice alt caracter non-numeric sau non-punct
    cleaned_price_str = re.sub(r'[^\d.]', '', cleaned_price_str)
    
    try:
        if cleaned_price_str:
            return float(cleaned_price_str)
        return None
    except ValueError:
        return None

# --- EXECUTIE TEST ---
# Codul produsului de testat
PRODUCT_CODE = 'HJC100530-XS'

if __name__ == "__main__":
    print("--- INCEP TESTUL DE SCRAPING (PLAYWRIGHT) ---")
    
    # Nordicamoto
    print(f"\n--- TEST NORDICAMOTO ---")
    price_nordicamoto = scrape_nordicamoto_search(PRODUCT_CODE, clean_and_convert_price)
    print(f"REZULTAT NORDICAMOTO FINAL: {price_nordicamoto}")

    # Moto24
    print(f"\n--- TEST MOTO24 ---")
    price_moto24 = scrape_moto24_search(PRODUCT_CODE, clean_and_convert_price)
    print(f"REZULTAT MOTO24 FINAL: {price_moto24}")

from bs4 import BeautifulSoup
import requests
import re
import time

def clean_and_convert_price(price_text):
    """Curăță textul prețului și îl convertește în float (gestionând formatele RON)."""
    if not price_text:
        return None
    
    price_text = price_text.upper().replace('LEI', '').replace('RON', '').replace('&NBSP;', '').strip()
    
    # 1. Eliminăm spațiile
    price_text = price_text.replace(' ', '')
    
    # 2. Dacă conține și punct și virgulă, eliminăm punctele (separator de mii)
    if price_text.count('.') > 0 and price_text.count(',') > 0:
        # Ex: 1.234,50 -> 1234,50
        price_text = price_text.replace('.', '')
        
    # 3. Standardizăm separatorul zecimal la punct (Ex: 1234,50 -> 1234.50)
    cleaned_price_str = price_text.replace(',', '.')
    
    # 4. Eliminăm orice alt caracter non-numeric sau non-punct
    cleaned_price_str = re.sub(r'[^\d.]', '', cleaned_price_str)
    
    try:
        if cleaned_price_str:
            return float(cleaned_price_str)
        return None
    except ValueError:
        return None


def scrape_nordicamoto_search(product_code):
    """
    Caută produsul pe Nordicamoto, navighează pe pagina produsului și extrage prețul.
    """
    if not product_code:
        return None

    # URL-ul de căutare
    search_url = f"https://www.nordicamoto.ro/?s={product_code}"
    
    try:
        print(f"Încerc căutarea Nordicamoto pentru codul: {product_code}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # PASUL 1: Caută produsul și extrage link-ul
        response_search = requests.get(search_url, headers=headers, timeout=10)
        response_search.raise_for_status()
        soup_search = BeautifulSoup(response_search.content, 'html.parser')

        # Selector robust pentru link-ul produsului
        product_link_element = soup_search.select_one(f'.products a[href*="{product_code.lower()}"]')
        
        if not product_link_element:
            print(f"❌ EROARE: Nu a fost găsit un link direct către produsul Nordicamoto (Cod: {product_code}).")
            return None

        product_url = product_link_element.get('href')
        
        # PASUL 2: Navighează la link-ul produsului și extrage prețul
        print(f"      Navighez la pagina produsului: {product_url}")
        
        response_product = requests.get(product_url, headers=headers, timeout=10)
        response_product.raise_for_status()
        soup_product = BeautifulSoup(response_product.content, 'html.parser')
        
        # Selectori pentru pagina de produs (foarte robuști pe WooCommerce)
        price_selectors = [
            '.summary .woocommerce-Price-amount', # Cel mai specific în zona de summary
            '.product-info .price',              # Wrapper general
            'p.price',                           # Tag-ul de preț
            '.price .amount',                    # Clasa amount
            '.summary .price .amount',           # Combinație
        ]
        
        price_element = None
        for selector in price_selectors:
            price_element = soup_product.select_one(selector)
            if price_element:
                break
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            price_ron = clean_and_convert_price(price_text)
            
            if price_ron is not None:
                print(f"      ✅ Preț Nordicamoto extras: {price_ron} RON")
                return price_ron
            
        print(f"❌ EROARE: Elementul de preț nu a fost găsit pe pagina produsului Nordicamoto.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Eroare de rețea/request la Nordicamoto: {e}")
        return None
    except Exception as e:
        print(f"❌ Eroare generală la scraping Nordicamoto: {e}")
        return None

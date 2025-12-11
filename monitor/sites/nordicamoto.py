from bs4 import BeautifulSoup
import requests
import re
import time

def scrape_nordicamoto_search(product_code):
    """
    Caută prețul unui produs pe nordicamoto.ro folosind codul produsului.
    Folosește selectori robuști pentru paginile de căutare WooCommerce.
    """
    if not product_code:
        return None

    search_url = f"https://www.nordicamoto.ro/?s={product_code}"
    
    try:
        print(f"Încerc căutarea Nordicamoto pentru codul: {product_code}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Selectori Robuști (De la cel mai specific la cel mai general) ---
        
        # 1. Selectorul WooCommerce standard (cel mai precis)
        price_element = soup.select_one('.product .woocommerce-Price-amount') 

        # 2. Selectorul care vizează elementul <b> din structura de preț
        # Acest lucru ajută dacă prețul este marcat cu bold într-un span.
        if not price_element:
            price_element = soup.select_one('.product .price b')
            
        # 3. Selectorul general de preț în interiorul unui produs (elementul <span>.amount)
        if not price_element:
            price_element = soup.select_one('.product .amount')

        # 4. Selectorul pentru clasa 'price' (cel mai generic)
        if not price_element:
            price_element = soup.select_one('.product .price')


        if price_element:
            price_text = price_element.get_text(strip=True)
            
            # Curățarea și Conversia Prețului
            price_text = price_text.replace('.', '') 
            price_text = price_text.replace(',', '.') 
            cleaned_price = re.sub(r'[^\d.]', '', price_text)
            
            if cleaned_price:
                price_ron = float(cleaned_price)
                print(f"      ✅ Preț Nordicamoto extras: {price_ron} RON")
                return price_ron
            
        print(f"❌ EROARE: Prețul nu a fost găsit în rezultatele căutării Nordicamoto pentru {product_code}.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Eroare de rețea/request la Nordicamoto: {e}")
        return None
    except Exception as e:
        print(f"❌ Eroare generală la scraping Nordicamoto: {e}")
        return None

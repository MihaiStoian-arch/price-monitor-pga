from bs4 import BeautifulSoup
import requests
import re
import time

def scrape_nordicamoto_search(product_code):
    """
    Caută prețul unui produs pe nordicamoto.ro folosind codul produsului, 
    folosind selectori robuști pentru paginile de căutare WooCommerce.
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
        
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Selectori Robuști (De la cel mai specific la cel mai general) ---
        
        # 1. Caută prețul în cardul de produs (cel mai comun selector WooCommerce)
        price_element = soup.select_one('.product-small .woocommerce-Price-amount') 

        # 2. Caută doar clasa generică de preț (amount) în card
        if not price_element:
            price_element = soup.select_one('.product-small .amount')
            
        # 3. Caută cel mai general selector de preț WooCommerce pe toată pagina
        if not price_element:
            price_element = soup.select_one('.woocommerce-Price-amount')

        # 4. Selectorul pentru elementul 'price' (poate conține prețul)
        if not price_element:
            price_element = soup.select_one('.price')

        if price_element:
            price_text = price_element.get_text(strip=True)
            
            # --- Curățarea și Conversia Prețului ---
            price_text = price_text.replace('.', '') 
            price_text = price_text.replace(',', '.') 
            cleaned_price = re.sub(r'[^\d.]', '', price_text)
            
            if cleaned_price:
                price_ron = float(cleaned_price)
                print(f"✅ Preț Nordicamoto extras: {price_ron} RON")
                return price_ron
            
        print(f"❌ EROARE: Prețul nu a fost găsit în rezultatele căutării Nordicamoto pentru {product_code}.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Eroare de rețea/request la Nordicamoto: {e}")
        return None
    except Exception as e:
        print(f"❌ Eroare generală la scraping Nordicamoto: {e}")
        return None

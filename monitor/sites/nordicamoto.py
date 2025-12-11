from bs4 import BeautifulSoup
import requests
import re
import time

def scrape_nordicamoto_search(product_code):
    """
    Caută prețul unui produs pe nordicamoto.ro folosind codul produsului.
    """
    if not product_code:
        return None

    # URL-ul de căutare al site-ului (de obicei /?s=...)
    search_url = f"https://www.nordicamoto.ro/?s={product_code}"
    
    try:
        print(f"Încerc căutarea Nordicamoto pentru codul: {product_code}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Selector robust care vizează prețul din rezultatele căutării:
        price_element = soup.select_one('.product-small .amount') 

        if not price_element:
            # Selector general de rezervă
            price_element = soup.select_one('.price .amount')

        if price_element:
            price_text = price_element.get_text(strip=True)
            
            # Curățarea și Conversia Prețului
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

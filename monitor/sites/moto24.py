from playwright.sync_api import sync_playwright
import re
from bs4 import BeautifulSoup



# FUNCTIA PRINCIPALĂ CU PLAYWRIGHT
def scrape_moto24_search(product_code):
    """
    Caută produsul pe Moto24 (care ar trebui să redirecționeze direct la produs) și extrage prețul.
    """
    # URL CORECTAT V9 (deși Playwright ar trebui să gestioneze redirectul oricum)
    search_url = f"https://www.moto24.ro/module/wkelasticsearch/wkelasticsearchlist?s={product_code}"
    print(f"Încerc Playwright (Moto24) pentru căutarea codului: {product_code}")
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navighează la URL-ul de căutare; Playwright așteaptă automat redirectul.
            page.goto(search_url, wait_until="domcontentloaded", timeout=40000)
            
            # Așteptăm 5 secunde suplimentare pentru finalizarea oricărui JS post-redirect
            page.wait_for_timeout(5000)

            # --- PASUL 1: VERIFICARE PAGINĂ ---
            
            # Verificăm dacă suntem pe o pagină goală
            no_results = page.locator('.alert.alert-warning, .no-products').is_visible()
            if no_results:
                print(f"❌ PAGINĂ GOALĂ: Căutarea Moto24 pentru codul '{product_code}' nu a returnat produse.")
                return None

            # --- PASUL 2: EXTRAGERE PREȚ (De pe URL-ul curent, post-redirect) ---

            price_selectors = [
                '#center_column .price',
                '.product-price',
                '.current-price',
                '[itemprop="price"]', 
            ]

            price_element_locator = None
            for selector in price_selectors:
                locator = page.locator(selector)
                if locator.count() > 0:
                    price_element_locator = locator.first
                    break
            
            if price_element_locator:
                # Așteptăm ca elementul să fie vizibil și extragem textul
                price_text = price_element_locator.inner_text()
                price_ron = clean_and_convert_price(price_text)
                
                if price_ron is not None:
                    print(f"      ✅ Preț Moto24 extras: {price_ron} RON")
                    return price_ron
                
            print(f"❌ EROARE: Elementul de preț nu a fost găsit pe pagina produsului Moto24.")
            return None

        except Exception as e:
            print(f"❌ EROARE GENERALĂ Playwright (Moto24): {e}")
            return None
        finally:
            browser.close()

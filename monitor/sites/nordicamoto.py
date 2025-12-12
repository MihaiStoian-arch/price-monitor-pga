from playwright.sync_api import sync_playwright
import re
from bs4 import BeautifulSoup


# FUNCTIA PRINCIPALĂ CU PLAYWRIGHT
def scrape_nordicamoto_search(product_code):
    """
    Caută produsul pe Nordicamoto, navighează pe pagina produsului și extrage prețul folosind Playwright.
    """
    search_url = f"https://www.nordicamoto.ro/search?search={product_code}"
    print(f"Încerc Playwright (Nordicamoto) pentru căutarea codului: {product_code}")
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(search_url, wait_until="domcontentloaded", timeout=40000)

            # --- PASUL 1: EXTRAGERE LINK PRODUS ---
            
            # Așteptăm ca lista de produse să apară (implicit auto-wait)
            page.wait_for_selector('.product_list', timeout=10000)

            # Selector Playwright: Găsește primul link de produs din lista de rezultate
            product_link_selector = f'a[href*="{product_code.lower()}"], .product_list .product-name a, .product_list .product-image a'
            
            product_link_element = page.locator(product_link_selector).first
            
            # Verificăm dacă există rezultate vizibile
            if not product_link_element.is_visible():
                no_results = page.locator('.alert.alert-warning, .no-results').is_visible()
                if no_results:
                    print(f"❌ PAGINĂ GOALĂ: Căutarea Nordicamoto pentru codul '{product_code}' nu a returnat produse.")
                    return None
                
                print(f"❌ EROARE: Nu a fost găsit un link de produs în rezultatele căutării Nordicamoto (Cod: {product_code}).")
                return None

            product_link = product_link_element.get_attribute("href")
            
            if not product_link:
                 print(f"❌ EROARE: Link de produs găsit dar URL-ul este invalid (Nordicamoto).")
                 return None

            # --- PASUL 2: NAVIGARE ȘI EXTRAGERE PREȚ ---
            print(f"      Navighez la pagina produsului: {product_link}")
            
            page.goto(product_link, wait_until="domcontentloaded", timeout=40000)

            # Selectori pentru preț pe pagina de produs (auto-wait)
            price_selectors = [
                '#center_column .price', 
                '.product-price',
                '.summary .woocommerce-Price-amount', 
                'p.price', 
                '[itemprop="price"]', 
            ]

            price_element_locator = None
            for selector in price_selectors:
                # Încercăm să găsim un locator
                locator = page.locator(selector)
                if locator.count() > 0:
                    price_element_locator = locator.first
                    break
            
            if price_element_locator:
                # Așteptăm ca elementul să fie vizibil și extragem textul
                price_text = price_element_locator.inner_text()
                price_ron = clean_and_convert_price(price_text)
                
                if price_ron is not None:
                    print(f"      ✅ Preț Nordicamoto extras: {price_ron} RON")
                    return price_ron
                
            print(f"❌ EROARE: Elementul de preț nu a fost găsit pe pagina produsului Nordicamoto.")
            return None

        except Exception as e:
            print(f"❌ EROARE GENERALĂ Playwright (Nordicamoto): {e}")
            return None
        finally:
            browser.close()

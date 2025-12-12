from playwright.sync_api import sync_playwright

# FUNCTIA PRINCIPALĂ CU PLAYWRIGHT (V20)
def scrape_moto24_search(product_code, clean_and_convert_price):
    """
    Caută produsul pe Moto24 (care ar trebui să redirecționeze direct la produs) și extrage prețul.
    """
    search_url = f"https://www.moto24.ro/module/wkelasticsearch/wkelasticsearchlist?s={product_code}"
    print(f"Încerc Playwright (Moto24) pentru căutarea codului: {product_code}")
    
    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36')
            page = context.new_page()
            
            # Navighează la URL-ul de căutare; Playwright gestionează redirecționarea.
            page.goto(search_url, wait_until="load", timeout=40000)
            
            # --- PASUL 1: VERIFICARE PAGINĂ ---
            
            no_results = page.locator('.alert.alert-warning, .no-products').is_visible()
            if no_results:
                print(f"❌ PAGINĂ GOALĂ: Căutarea Moto24 pentru codul '{product_code}' nu a returnat produse.")
                return None

            # --- PASUL 2: EXTRAGERE PREȚ (De pe URL-ul curent, post-redirect) ---

            # Selectori pentru preț (PrestaShop/modul)
            price_selectors = [
                '#center_column .price',
                '.product-price',
                '.current-price',
                '[itemprop="price"]', 
            ]

            price_element_locator = None
            for selector in price_selectors:
                locator = page.locator(selector).first
                if locator.count() > 0:
                    price_element_locator = locator
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
            if browser:
                browser.close()

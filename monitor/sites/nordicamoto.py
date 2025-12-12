from playwright.sync_api import sync_playwright

# FUNCTIA PRINCIPALĂ CU PLAYWRIGHT (V21 - Selector Mai Generic)
def scrape_nordicamoto_search(product_code, clean_and_convert_price):
    """
    Caută produsul pe Nordicamoto, navighează pe pagina produsului și extrage prețul folosind Playwright.
    """
    search_url = f"https://www.nordicamoto.ro/search?search={product_code}"
    print(f"Încerc Playwright (Nordicamoto) pentru căutarea codului: {product_code}")
    
    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36')
            page = context.new_page()
            
            page.goto(search_url, wait_until="load", timeout=40000)

            # --- PASUL 1: EXTRAGERE LINK PRODUS (SELECTOR AGRESIV) ---
            
            # Selector V21: Încearcă să găsească link-ul imaginii/titlului primului produs din listă,
            # fără a se baza pe codul produsului în URL, ci pe structura paginii.
            product_link_selector = 'ul.product_list a, .products > div:first-child a, .product-container:first-child a'
            
            product_link_element = None
            try:
                # Așteptăm ca lista de produse să se încarce
                page.wait_for_selector('ul.product_list, .products', timeout=10000)
                
                # Căutăm link-ul
                link_locator = page.locator(product_link_selector)
                if link_locator.count() > 0:
                     product_link_element = link_locator.first
                
            except Exception:
                pass # Dacă lista nu se încarcă în 10s, continuăm cu verificarea paginii goale

            if product_link_element and product_link_element.is_visible():
                product_link = product_link_element.get_attribute("href")
            else:
                product_link = None
            
            # Verificare pagină goală
            if not product_link:
                no_results = page.locator('.alert.alert-warning, .no-results').is_visible()
                if no_results:
                    print(f"❌ PAGINĂ GOALĂ: Căutarea Nordicamoto pentru codul '{product_code}' nu a returnat produse.")
                    return None
                
                print(f"❌ EROARE: Nu a fost găsit un link de produs în rezultatele căutării Nordicamoto (Cod: {product_code}).")
                return None

            # --- PASUL 2: NAVIGARE ȘI EXTRAGERE PREȚ ---
            print(f"      Navighez la pagina produsului: {product_link}")
            
            page.goto(product_link, wait_until="load", timeout=40000)

            # Selectori pentru preț (aceiași, Playwright gestionează auto-wait)
            price_selectors = [
                '#center_column .price', 
                '.product-price',
                '.summary .woocommerce-Price-amount', 
                'p.price', 
                '[itemprop="price"]', 
            ]

            price_element_locator = None
            for selector in price_selectors:
                locator = page.locator(selector).first
                if locator.count() > 0:
                    price_element_locator = locator
                    break
            
            if price_element_locator:
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
            if browser:
                browser.close()

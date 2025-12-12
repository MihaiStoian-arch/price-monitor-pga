from playwright.sync_api import sync_playwright

# FUNCTIA PRINCIPALĂ CU PLAYWRIGHT (V22 - OPTIMIZARE TIMEOUT)
def scrape_moto24_search(product_code, clean_and_convert_price):
    """
    Caută produsul pe Moto24 și extrage prețul.
    """
    # Adresa de căutare
    search_url = f"https://www.moto24.ro/module/wkelasticsearch/wkelasticsearchlist?s={product_code}"
    print(f"Încerc Playwright (Moto24) pentru căutarea codului: {product_code}")
    
    with sync_playwright() as p:
        browser = None
        try:
            # Setați headless=True pentru producție
            browser = p.chromium.launch(headless=True) 
            context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36')
            page = context.new_page()
            
            # Navighează la URL-ul de căutare
            page.goto(search_url, wait_until="load", timeout=40000)
            
            # --- 1. AȘTEPTARE OPTIMIZATĂ ---
            # Așteptăm ca elementul de preț să fie VIZIBIL, cu un timeout mai lung (20s)
            
            PRICE_SELECTOR = '.current-price-value, [itemprop="price"], .product-prices'
            
            try:
                # Folosim wait_for_selector cu un timeout dublu
                page.wait_for_selector(PRICE_SELECTOR, state="visible", timeout=20000) # 20 secunde
                print("    ✅ Randare preț confirmată.")
            except Exception as e:
                # Dacă dă timeout, continuăm cu warning, dar nu eșuăm
                print(f"    ⚠️ Timp de așteptare expirat ({20}s), continuăm cu extragerea.")

            # --- PASUL 2: VERIFICARE PAGINĂ ȘI EXTRAGERE PREȚ ---
            
            no_results_locator = page.locator('.alert.alert-warning, #main p.products-sort-order').filter(has_text="Nu există produse")
            if no_results_locator.is_visible():
                print(f"❌ PAGINĂ GOALĂ: Căutarea Moto24 pentru codul '{product_code}' nu a returnat produse.")
                return None

            price_selectors = [
                '.current-price-value', 
                '[itemprop="price"]', 
                '.product-prices .price', 
                '.product-prices',
            ]

            price_text = None
            
            for selector in price_selectors:
                locator = page.locator(selector).first
                
                if locator.count() > 0:
                    # Folosim inner_text()
                    extracted_text = locator.inner_text().strip()
                    
                    if len(extracted_text) > 2:
                        price_text = extracted_text
                        break
            
            if price_text:
                price_ron = clean_and_convert_price(price_text)
                
                if price_ron is not None:
                    # Verificare prag (pentru a filtra erorile de tip 2.95)
                    if price_ron >= 10:
                        print(f"      ✅ Preț Moto24 extras: {price_ron:.2f} RON (Din text: '{price_text}')")
                        return price_ron
                    else:
                         print(f"      ⚠️ Preț sub prag ({price_ron} RON). Selectorul a preluat o valoare greșită/parțială.")
                         return None
                
            print(f"❌ EROARE: Prețul nu a putut fi extras sau convertit (Text extras: {price_text}).")
            return None

        except Exception as e:
            # Dacă Playwright eșuează din motive mai grave (e.g., problemă de rețea)
            print(f"❌ EROARE GENERALĂ Playwright (Moto24): {e}")
            return None
        finally:
            if browser:
                browser.close()

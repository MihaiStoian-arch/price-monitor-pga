from playwright.sync_api import sync_playwright

# FUNCTIA PRINCIPALĂ CU PLAYWRIGHT (V26 - Finalizare Preț Promoțional)
def scrape_moto24_search(product_code, clean_and_convert_price):
    """
    Cauta produsul pe Moto24 și extrage prețul.
    Logică optimizată pentru a prioritiza prețul redus/promoțional.
    """
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
            
            # Așteptăm titlul paginii de produs, care ar trebui să apară înainte de preț (15s)
            try:
                page.wait_for_selector('h1.product-title, .page-header', state="visible", timeout=15000)
            except:
                print(f"    ⚠️ Timp de așteptare pentru titlu expirat (15s), continuăm cu extragerea.")

            # --- PASUL 1: VERIFICARE PAGINĂ ---
            
            no_results = page.locator('.alert.alert-warning, .no-products').is_visible()
            if no_results:
                print(f"❌ PAGINĂ GOALĂ: Căutarea Moto24 pentru codul '{product_code}' nu a returnat produse.")
                return None

            # --- PASUL 2: EXTRAGERE PREȚ (PRIORITIZARE) ---

            # Selectori pentru preț. ORDONARE: Promoțional > Normal > Metadata
            price_selectors = [
                # 1. Preț final/promoțional (clase comune PrestaShop/module)
                '.current-price-value', 
                '.product-prices .current-price-value',
                '.price-final',
                
                # 2. Preț normal (fallback dacă nu e promoție)
                '.product-price',
                '.current-price',
                
                # 3. Selector larg (prinde tot textul, dar poate necesita curățare mai strictă)
                '#product-prices .price', 
                
                # 4. Selector bazat pe schema.org
                '[itemprop="price"]',
            ]

            price_element_locator = None
            price_text = None
            
            for selector in price_selectors:
                locator = page.locator(selector).first
                
                if locator.count() > 0:
                    # Dacă găsim o valoare în itemprop="price", încercăm să extragem atributul 'content'
                    if selector == '[itemprop="price"]':
                        price_text = locator.get_attribute('content')
                    else:
                        price_text = locator.inner_text().strip()
                        
                    # Încercăm conversia imediată pentru a vedea dacă valoarea este validă
                    price_ron = clean_and_convert_price(price_text)
                    
                    # Verificăm dacă prețul este rezonabil (pentru a evita valorile parțiale tip 2.947)
                    if price_ron is not None and price_ron >= 50:
                        print(f"      ✅ Preț Moto24 extras (Selector: {selector}): {price_ron:.2f} RON (Din text: '{price_text}')")
                        return price_ron
                    
                    # Dacă prețul extras este valid, dar sub prag (e.g. un pret 5.00), nu ne bazam pe el
                    
            print(f"❌ EROARE: Prețul nu a putut fi extras sau nu este valid (Text extras: {price_text}).")
            return None

        except Exception as e:
            print(f"❌ EROARE GENERALĂ Playwright (Moto24): {e}")
            return None
        finally:
            if browser:
                browser.close()

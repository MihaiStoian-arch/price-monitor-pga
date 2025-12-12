from playwright.sync_api import sync_playwright

# FUNCTIA PRINCIPALĂ CU PLAYWRIGHT (V21 - OPTIMIZAT PENTRU PRESTASHOP)
def scrape_moto24_search(product_code, clean_and_convert_price):
    """
    Caută produsul pe Moto24 (care ar trebui să redirecționeze direct la produs) și extrage prețul.
    Logică optimizată pentru a prelua prețul redus/final.
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
            
            # Navighează la URL-ul de căutare; Playwright gestionează redirecționarea.
            page.goto(search_url, wait_until="load", timeout=40000)
            
            # Așteptăm elementele de preț pentru a ne asigura că pagina este randată
            # Folosim un selector care acoperă majoritatea prețurilor PrestaShop
            page.wait_for_selector('.current-price-value, .product-prices', timeout=10000) 
            
            # --- PASUL 1: VERIFICARE PAGINĂ ---
            
            # Selector mai bun pentru lipsa de rezultate în PrestaShop
            no_results_locator = page.locator('.alert.alert-warning, #main p.products-sort-order').filter(has_text="Nu există produse care să corespundă criteriilor dumneavoastră")
            if no_results_locator.is_visible():
                print(f"❌ PAGINĂ GOALĂ: Căutarea Moto24 pentru codul '{product_code}' nu a returnat produse.")
                return None

            # --- PASUL 2: EXTRAGERE PREȚ (STRATEGIE PRIORITARĂ) ---
            
            # Selectori optimizați: prioritizează prețul final afișat (Promoțional sau Normal)
            price_selectors = [
                # 1. Prețul curent/final (în PrestaShop, cel mai des un span cu valoarea)
                '.current-price-value', 
                # 2. Selectorul vechi (un fallback bun)
                '[itemprop="price"]', 
                # 3. Selector pentru prețul afișat pe pagina de produs
                '.product-prices .price', 
                # 4. Selector general de fallback (poate fi prea larg, dar acoperă tot)
                '.product-prices',
            ]

            price_text = None
            
            for selector in price_selectors:
                locator = page.locator(selector).first
                
                # Așteptăm maxim 2 secunde pentru ca selectorul să apară, doar pentru a fi siguri
                if locator.count() > 0:
                    # Folosim inner_text() care e mai sigur decât text_content()
                    extracted_text = locator.inner_text().strip()
                    
                    # Verificăm dacă textul extras pare a fi un preț valid
                    if len(extracted_text) > 2:
                        price_text = extracted_text
                        break
            
            if price_text:
                # Folosim funcția robustă de curățare
                price_ron = clean_and_convert_price(price_text)
                
                if price_ron is not None:
                    # Verificare finală pentru a evita erorile de tip 2.95 (care e o rotunjire)
                    # Prețul trebuie să fie peste un prag rezonabil (e.g., 50 RON)
                    if price_ron > 50 or price_ron >= 10:
                        print(f"      ✅ Preț Moto24 extras: {price_ron:.2f} RON (Din text: '{price_text}')")
                        return price_ron
                    else:
                         print(f"      ⚠️ Preț sub prag ({price_ron} RON). Selectorul a preluat o valoare greșită/parțială.")
                         return None
                
            print(f"❌ EROARE: Prețul nu a putut fi extras sau convertit (Text extras: {price_text}).")
            return None

        except Exception as e:
            print(f"❌ EROARE GENERALĂ Playwright (Moto24): {e}")
            return None
        finally:
            if browser:
                browser.close()

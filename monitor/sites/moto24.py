from playwright.sync_api import sync_playwright

# FUNCTIA PRINCIPALĂ CU PLAYWRIGHT (V24 - FINALIZARE)
def scrape_moto24_search(product_code, clean_and_convert_price):
    """
    Cauta produsul pe Moto24 si extrage prețul.
    Strategie optimizată pentru a gestiona timeout-urile și extragerea valorilor complete.
    """
    search_url = f"https://www.moto24.ro/module/wkelasticsearch/wkelasticsearchlist?s={product_code}"
    print(f"Încerc Playwright (Moto24) pentru căutarea codului: {product_code}")
    
    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(headless=True) 
            context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36')
            page = context.new_page()
            
            # Navighează la URL-ul de căutare
            page.goto(search_url, wait_until="load", timeout=40000)
            
            # 1. ELIMINAREA BLOCULUI DE WAIT_FOR_SELECTOR
            # Ne bazăm pe faptul că page.goto așteaptă suficient și trecem direct la locator.
            
            # Așteptăm doar o fracțiune de secundă (simulare input uman)
            page.wait_for_timeout(500) 

            # --- PASUL 2: VERIFICARE PAGINĂ ȘI EXTRAGERE PREȚ ---
            
            no_results_locator = page.locator('.alert.alert-warning, #main p.products-sort-order').filter(has_text="Nu există produse")
            if no_results_locator.is_visible():
                print(f"❌ PAGINĂ GOALĂ: Căutarea Moto24 pentru codul '{product_code}' nu a returnat produse.")
                return None

            price_text = None
            price_ron = None

            # STRATEGIA A (Nouă, Forțată): Extragem textul din cel mai larg container de preț.
            # Aceasta ar trebui să ne ofere tot textul, de exemplu: "2 947,00 Lei"
            price_container_locator = page.locator('#product-prices, .product-prices').first
            
            if price_container_locator.count() > 0:
                price_text = price_container_locator.inner_text().strip()

            # STRATEGIA B (Fallback): Dacă nu găsim prețul complet, încercăm valoarea brută din itemprop
            if price_text is None or len(price_text) < 3:
                locator_price_content = page.locator('[itemprop="price"]').first
                if locator_price_content.count() > 0:
                    price_content_attr = locator_price_content.get_attribute('content')
                    if price_content_attr:
                        price_text = price_content_attr
                        
            
            # --- PASUL 3: CONVERSIE ȘI VALIDARE ---
            if price_text:
                price_ron = clean_and_convert_price(price_text)
                
                if price_ron is not None:
                    # Pragul rămâne la 50 RON pentru a filtra erorile de tip 2.947 (care e acum un float)
                    if price_ron >= 50: 
                        print(f"      ✅ Preț Moto24 extras: {price_ron:.2f} RON (Din text: '{price_text}')")
                        return price_ron
                    else:
                         # Acum știm că 2.947 RON era o valoare parțială, dar convertită corect la 2.947
                         # Nu ne mai bazăm pe ea, ci pe valoarea completă.
                         print(f"      ⚠️ Preț sub prag ({price_ron:.3f} RON). Extragerea prețului complet a eșuat.")
                         return None
                
            print(f"❌ EROARE: Prețul nu a putut fi extras sau convertit (Text extras: {price_text}).")
            return None

        except Exception as e:
            print(f"❌ EROARE GENERALĂ Playwright (Moto24): {e}")
            return None
        finally:
            if browser:
                browser.close()

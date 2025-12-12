from playwright.sync_api import sync_playwright

# FUNCTIA PRINCIPALĂ CU PLAYWRIGHT (V25 - EXTRAGERE BRUTE FORCE)
def scrape_moto24_search(product_code, clean_and_convert_price):
    """
    Caută produsul pe Moto24 și extrage prețul.
    Strategie finală: Așteptare generică + extragere din cel mai larg container de preț.
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
            
            # --- 1. AȘTEPTARE ROBUSTĂ ---
            # Așteptăm titlul paginii de produs, care ar trebui să apară înainte de preț.
            try:
                page.wait_for_selector('#product_info, h1.product-title', state="visible", timeout=15000) 
                print("    ✅ Pagina de produs este randată (Așteptare după titlu).")
            except:
                print(f"    ⚠️ Timp de așteptare pentru titlu expirat (15s), continuăm cu extragerea.")

            # --- PASUL 2: VERIFICARE PAGINĂ ȘI EXTRAGERE PREȚ ---
            
            no_results_locator = page.locator('.alert.alert-warning, #main p.products-sort-order').filter(has_text="Nu există produse")
            if no_results_locator.is_visible():
                print(f"❌ PAGINĂ GOALĂ: Căutarea Moto24 pentru codul '{product_code}' nu a returnat produse.")
                return None

            price_text = None
            price_ron = None

            # STRATEGIA A (Extragere Brute Force): Extragem textul din cel mai larg container de preț (CSS + ID).
            # Acesta ar trebui să cuprindă atât prețul normal, cât și pe cel promoțional.
            price_container_locator = page.locator('#product-prices, .product-prices, .price-main').first
            
            if price_container_locator.count() > 0:
                # Folosim text_content() pentru a prinde tot textul, inclusiv din sub-elemente
                price_text = price_container_locator.text_content().strip()

            # STRATEGIA B (Fallback Metada/Itemprop)
            if price_text is None or len(price_text) < 3:
                locator_price_content = page.locator('[itemprop="price"]').first
                if locator_price_content.count() > 0:
                    # Preferăm valoarea din atributul content (dacă există)
                    price_content_attr = locator_price_content.get_attribute('content')
                    if price_content_attr:
                        price_text = price_content_attr
                        
            
            # --- PASUL 3: CONVERSIE ȘI VALIDARE ---
            if price_text:
                price_ron = clean_and_convert_price(price_text)
                
                if price_ron is not None:
                    # Pragul de 50 RON ramane pentru a filtra valorile eronate de tip 2.947
                    if price_ron >= 50: 
                        print(f"      ✅ Preț Moto24 extras: {price_ron:.2f} RON (Din text: '{price_text}')")
                        return price_ron
                    else:
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

from playwright.sync_api import sync_playwright

# FUNCTIA PRINCIPALĂ CU PLAYWRIGHT (V23 - Extracție Extrem de Agresivă, Fără Căutare Explicită de Listă)
def scrape_nordicamoto_search(product_code, clean_and_convert_price):
    """
    Caută produsul pe Nordicamoto și extrage prețul bazându-se pe elemente generale.
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

            # Așteptăm cel puțin 5 secunde, lăsând timp pentru orice JS să randeze
            page.wait_for_timeout(5000)

            # 1. Verificare pagină goală
            no_results = page.locator('.alert.alert-warning, .no-results').is_visible()
            if no_results:
                print(f"❌ PAGINĂ GOALĂ: Căutarea Nordicamoto pentru codul '{product_code}' nu a returnat produse.")
                return None
            
            # 2. Selectori pentru preț (caută oriunde pe pagină, asociat cu codul)
            price_selectors = [
                # Caută prețul în jurul unui element care conține codul produsului
                f':text("{product_code}") >> xpath=./following::p[contains(@class, "price")]', 
                f':text("{product_code}") >> xpath=./following::span[contains(@class, "amount")]',
                
                # Caută cel mai general preț vizibil pe pagină
                '.price .amount, p.price .amount, .woocommerce-Price-amount',
                
                # Caută orice text care arată ca un preț RON
                'body :text("RON"):visible',
            ]

            price_element_locator = None
            price_text = None
            
            # Iterație pe selectori
            for selector in price_selectors:
                locator = page.locator(selector).first
                if locator.count() > 0 and locator.is_visible():
                    price_text = locator.inner_text()
                    # Dacă prețul a fost găsit cu un selector, încercăm să-l curățăm
                    price_ron = clean_and_convert_price(price_text)
                    if price_ron is not None:
                        print(f"      ✅ Preț Nordicamoto extras (V23 - Selector: {selector}): {price_ron} RON")
                        return price_ron
            
            # Dacă am ajuns aici, prețul nu a fost găsit sau curățat
            print(f"❌ EROARE: Nu a fost găsit prețul (sau link-ul) pentru codul: {product_code}.")
            return None

        except Exception as e:
            print(f"❌ EROARE GENERALĂ Playwright (Nordicamoto): {e}")
            return None
        finally:
            if browser:
                browser.close()

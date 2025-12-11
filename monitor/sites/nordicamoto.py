from bs4 import BeautifulSoup
import re
import asyncio
from pyppeteer import launch
import time

def clean_and_convert_price(price_text):
    """Curăță textul prețului și îl convertește în float (gestionând formatele RON)."""
    if not price_text: return None
    
    price_text = price_text.upper().replace('LEI', '').replace('RON', '').replace('&NBSP;', '').strip()
    price_text = price_text.replace(' ', '')
    if price_text.count('.') > 0 and price_text.count(',') > 0: price_text = price_text.replace('.', '')
    cleaned_price_str = price_text.replace(',', '.')
    cleaned_price_str = re.sub(r'[^\d.]', '', cleaned_price_str)
    
    try:
        if cleaned_price_str: return float(cleaned_price_str)
        return None
    except ValueError: return None

# FUNCTIA WRAPPER
def scrape_nordicamoto_search(product_code):
    """
    Caută produsul pe Nordicamoto, navighează pe pagina produsului și extrage prețul.
    """
    if not product_code: return None
    # URL CORECTAT V9
    search_url = f"https://www.nordicamoto.ro/search?search={product_code}"
    try:
        return asyncio.get_event_loop().run_until_complete(_scrape_nordicamoto_async_search(search_url, product_code))
    except Exception as e:
        print(f"❌ EROARE GENERALĂ la Nordicamoto (Wrapper/Async): {e}")
        return None

# FUNCTIA ASINCRONĂ PRINCIPALĂ (NORDICAMOTO - V15: Caută prețul direct în lista de rezultate)
async def _scrape_nordicamoto_async_search(search_url, product_code):
    print(f"Încerc randarea JS (Nordicamoto) pentru căutarea codului: {product_code}")
    browser = None
    try:
        browser = await launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox'] 
        )
        page = await browser.newPage()
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        # PASUL 1: Caută produsul și extrage conținutul paginii de rezultate
        await page.goto(search_url, {'timeout': 40000, 'waitUntil': 'networkidle2'})
        await asyncio.sleep(8) 

        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        # --- TENTATIVA 1: EXTRAGERE PREȚ DIRECT DIN PAGINA DE CĂUTARE ---
        
        # Selectori pentru preț în lista de rezultate (Ex: .product-container .price)
        list_price_selectors = [
            'ul.product_list li:first-child .price',
            '.product-container:first-child .price',
            '#center_column .ajax_block_product:first-child .price',
            '.product_list .price',
        ]
        
        price_element = None
        for selector in list_price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                break
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            price_ron = clean_and_convert_price(price_text)
            
            if price_ron is not None:
                print(f"      ✅ Preț Nordicamoto extras (din Lista de Căutare): {price_ron} RON")
                return price_ron
        
        # --- TENTATIVA 2: DACA NU AM GASIT PRETUL, CĂUTĂM LINK-UL ȘI NAVIGĂM ---
        
        # Caută link-ul (Logica V14 pentru a ne asigura că ajungem la pagina produsului)
        product_link = await page.evaluate('''
            (code) => {
                // Selectorul primar: link-ul imaginii din primul produs
                const productLink = document.querySelector('#center_column .product_img_link[href], #columns .product_img_link[href]');
                
                if (productLink) {
                    return productLink.href;
                }
                
                // Fallback: Caută linkul titlului de produs
                const productTitleLink = document.querySelector('.product-name a[href], .product-title a[href]');
                if (productTitleLink) {
                    return productTitleLink.href;
                }

                // Verificăm dacă pagina de căutare este goală
                const noResults = document.querySelector('.alert.alert-warning, .no-results, .woocommerce-info'); 
                if (noResults) {
                    return "NO_RESULTS_FOUND"; 
                }
                
                return null;
            }
        ''', product_code) 


        if product_link == "NO_RESULTS_FOUND":
            print(f"❌ PAGINĂ GOALĂ: Căutarea Nordicamoto pentru codul '{product_code}' nu a returnat produse.")
            return None
        
        if not product_link:
            print(f"❌ EROARE: Nu a fost găsit un link de produs în rezultatele căutării Nordicamoto (Cod: {product_code}).")
            return None
        
        # PASUL 3: Navighează la link-ul produsului și extrage prețul (Dacă Tentativa 1 a eșuat)
        print(f"      Navighez la pagina produsului: {product_link}")
        await page.goto(product_link, {'timeout': 40000, 'waitUntil': 'networkidle2'})
        await asyncio.sleep(5) 

        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        price_selectors = [
            '#center_column .price', 
            '.price .current-price', 
            '.summary .woocommerce-Price-amount', 
            'p.price', 
            '[itemprop="price"]', 
        ]
        
        price_element = None
        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                break
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            price_ron = clean_and_convert_price(price_text)
            
            if price_ron is not None:
                print(f"      ✅ Preț Nordicamoto extras: {price_ron} RON")
                return price_ron
            
        print(f"❌ EROARE: Elementul de preț nu a fost găsit pe pagina produsului Nordicamoto.")
        return None

    finally:
        if browser:
            await browser.close()

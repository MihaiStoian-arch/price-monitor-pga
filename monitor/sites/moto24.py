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
def scrape_moto24_search(product_code):
    """
    Caută produsul pe Moto24, navighează pe pagina produsului și extrage prețul.
    """
    if not product_code: return None
    # URL CORECTAT V9
    search_url = f"https://www.moto24.ro/module/wkelasticsearch/wkelasticsearchlist?s={product_code}"
    try:
        return asyncio.get_event_loop().run_until_complete(_scrape_moto24_async_search(search_url, product_code))
    except Exception as e:
        print(f"❌ EROARE GENERALĂ la Moto24 (Wrapper/Async): {e}")
        return None

# FUNCTIA ASINCRONĂ PRINCIPALĂ
async def _scrape_moto24_async_search(search_url, product_code):
    print(f"Încerc randarea JS (Moto24) pentru căutarea codului: {product_code}")
    browser = None
    try:
        browser = await launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox'] 
        )
        page = await browser.newPage()
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        # PASUL 1: Caută produsul și extrage link-ul
        await page.goto(search_url, {'timeout': 40000, 'waitUntil': 'networkidle2'})
        await asyncio.sleep(5) 

        # Logica de căutare a link-ului (V10: Selector specific Moto24 Elastic Search)
        product_link = await page.evaluate('''
            (code) => {
                const codeUpper = code.toUpperCase();
                
                // 1. Selector care vizează link-ul din TITLUL primului produs
                const productTitleLink = document.querySelector('.wkelasticsearchlist-product-container:first-child .product-name a[href]');
                
                if (productTitleLink) {
                    return productTitleLink.href;
                }
                
                // 2. Fallback: Caută link-ul principal al întregului card de produs
                const productCardLink = document.querySelector('.wkelasticsearchlist-product-container:first-child a.product_img_link[href]');

                if (productCardLink) {
                    return productCardLink.href;
                }

                // Verificăm dacă pagina de căutare este goală
                const noResults = document.querySelector('.alert.alert-warning, .no-results, .wk_search_list:empty, .no-products'); 
                if (noResults) {
                    return "NO_RESULTS_FOUND"; 
                }
                
                return null;
            }
        ''', product_code) 

        if product_link == "NO_RESULTS_FOUND":
            print(f"❌ PAGINĂ GOALĂ: Căutarea Moto24 pentru codul '{product_code}' nu a returnat produse.")
            return None
        
        if not product_link:
            print(f"❌ EROARE: Nu a fost găsit un link de produs în rezultatele căutării Moto24 (Cod: {product_code}).")
            return None
        
        # PASUL 2: Navighează la link-ul produsului și extrage prețul
        print(f"      Navighez la pagina produsului: {product_link}")
        await page.goto(product_link, {'timeout': 40000, 'waitUntil': 'networkidle2'})
        await asyncio.sleep(5) 

        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        price_selectors = [
            '.single-product-wrapper .woocommerce-Price-amount', 
            '.price ins .amount', 
            'p.price', 
            '.summary .price',
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
                print(f"      ✅ Preț RON extras (Pyppeteer/Pagina Produs): {price_ron} RON")
                return price_ron
            
        print(f"❌ EROARE: Elementul de preț nu a fost găsit pe pagina produsului Moto24.")
        return None

    finally:
        if browser:
            await browser.close()

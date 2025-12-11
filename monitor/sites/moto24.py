from bs4 import BeautifulSoup
import re
import asyncio
from pyppeteer import launch
import time

def clean_and_convert_price(price_text):
    """Curăță textul prețului și îl convertește în float (gestionând formatele RON)."""
    if not price_text:
        return None
    
    price_text = price_text.upper().replace('LEI', '').replace('RON', '').replace('&NBSP;', '').strip()
    
    # 1. Eliminăm spațiile
    price_text = price_text.replace(' ', '')
    
    # 2. Dacă conține și punct și virgulă, eliminăm punctele (separator de mii)
    if price_text.count('.') > 0 and price_text.count(',') > 0:
        # Ex: 1.234,50 -> 1234,50
        price_text = price_text.replace('.', '')
        
    # 3. Standardizăm separatorul zecimal la punct (Ex: 1234,50 -> 1234.50)
    cleaned_price_str = price_text.replace(',', '.')
    
    # 4. Eliminăm orice alt caracter non-numeric sau non-punct
    cleaned_price_str = re.sub(r'[^\d.]', '', cleaned_price_str)
    
    try:
        return float(cleaned_price_str)
    except ValueError:
        return None

def scrape_moto24_search(product_code):
    """
    Caută produsul pe Moto24, navighează pe pagina produsului și extrage prețul.
    """
    if not product_code:
        return None
        
    # URL-ul de căutare
    search_url = f"https://dealer.moto24.ro/?s={product_code}&post_type=product"
    
    try:
        return asyncio.get_event_loop().run_until_complete(_scrape_moto24_async_search(search_url, product_code))
    except Exception as e:
        print(f"❌ EROARE GENERALĂ la Moto24 (Wrapper/Async): {e}")
        return None

async def _scrape_moto24_async_search(search_url, product_code):
    print(f"Încerc randarea JS (Moto24) pentru căutarea codului: {product_code}")
    browser = None
    try:
        # Lansarea browser-ului headless
        browser = await launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox'] 
        )
        page = await browser.newPage()
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        # PASUL 1: Caută produsul și extrage link-ul
        await page.goto(search_url, {'timeout': 40000, 'waitUntil': 'networkidle2'})
        await asyncio.sleep(3) 

        # Selector pentru link-ul produsului. Caută un link care conține codul de produs.
        link_selector = f'a[href*="{product_code.lower()}"]'
        
        # Extrage href-ul primului link găsit care se potrivește
        product_link = await page.evaluate(f'document.querySelector("{link_selector}") ? document.querySelector("{link_selector}").href : null')

        if not product_link:
            print(f"❌ EROARE: Nu a fost găsit un link direct către produsul Moto24 (Cod: {product_code}).")
            return None
        
        # PASUL 2: Navighează la link-ul produsului și extrage prețul
        print(f"      Navighez la pagina produsului: {product_link}")
        await page.goto(product_link, {'timeout': 40000, 'waitUntil': 'networkidle2'})
        await asyncio.sleep(3) # Așteaptă randarea completă a prețului

        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        # Selectori pentru pagina de produs (mult mai specifici pe structura produsului unic)
        price_selectors = [
            '.single-product-wrapper .woocommerce-Price-amount', 
            '.product-info-wrap .price',                        
            '.summary .price',                                  
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

    except Exception as e:
        print(f"❌ EXCEPȚIE la Pyppeteer/Randare Moto24: {e}")
        return None
    finally:
        if browser:
            await browser.close()

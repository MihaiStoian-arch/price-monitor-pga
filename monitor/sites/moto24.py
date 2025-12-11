from bs4 import BeautifulSoup
import re
import asyncio
from pyppeteer import launch
import time

def clean_and_convert_price(price_text):
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

def scrape_moto24_search(product_code):
    if not product_code: return None
    search_url = f"https://dealer.moto24.ro/?s={product_code}&post_type=product"
    try:
        return asyncio.get_event_loop().run_until_complete(_scrape_moto24_async_search(search_url, product_code))
    except Exception as e:
        print(f"❌ EROARE GENERALĂ la Moto24 (Wrapper/Async): {e}")
        return None

async def _scrape_moto24_async_search(search_url, product_code):
    # ... (pașii de lansare browser și goto) ...
    
    # PASUL 1: Caută produsul și extrage link-ul
    await page.goto(search_url, {'timeout': 40000, 'waitUntil': 'networkidle2'})
    await asyncio.sleep(5) 

    # Selector mai flexibil pentru a găsi orice link de produs
    product_link = await page.evaluate(f'''
        (code) => {{
            // Caută orice link <a> care se află într-un element care conține clasa 'product'
            const productElement = document.querySelector('.product a[href]');
            
            // Dacă primul link de produs a fost găsit
            if (productElement) {{
                return productElement.href;
            }}
            
            // Fallback: Caută primul link care conține codul produsului în URL (mai riscant, dar util)
            const allLinks = Array.from(document.querySelectorAll('a[href*="' + code + '"]'));
            if (allLinks.length > 0) {{
                return allLinks[0].href;
            }}
            
            return null;
        }}
    ''', product_code) # Trimitem codul produsului ca argument

    if not product_link:
        print(f"❌ EROARE: Nu a fost găsit un link de produs în rezultatele căutării Moto24 (Cod: {product_code}).")
        return None
        
        # PASUL 2: Navighează la link-ul produsului și extrage prețul (logica BeautifulSoup)
        print(f"      Navighez la pagina produsului: {product_link}")
        await page.goto(product_link, {'timeout': 40000, 'waitUntil': 'networkidle2'})
        await asyncio.sleep(5) 

        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        price_selectors = [
            '.single-product-wrapper .woocommerce-Price-amount', 
            '.price ins .amount', 'p.price', '.summary .price', '[itemprop="price"]', 
        ]
        
        price_element = None
        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element: break
                
        if price_element:
            price_text = price_element.get_text(strip=True)
            price_ron = clean_and_convert_price(price_text)
            
            if price_ron is not None:
                print(f"      ✅ Preț RON extras (Pyppeteer/Pagina Produs): {price_ron} RON")
                return price_ron
            
        print(f"❌ EROARE: Elementul de preț nu a fost găsit pe pagina produsului Moto24.")
        return None

    except Exception as e:
        # Aici prindem erorile din Pyppeteer
        print(f"❌ EXCEPȚIE la Pyppeteer/Randare Moto24: {e}")
        return None
    finally:
        if browser: 
            await browser.close()

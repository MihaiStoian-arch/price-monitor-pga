from bs4 import BeautifulSoup
import re
import asyncio
from pyppeteer import launch
import time

# Selectorul precis anterior
# PRICE_SELECTOR_SEARCH = 'p.product-price span[data-nosnippet]' 

def scrape_moto24_search(product_code):
    """
    Caută prețul unui produs pe dealer.moto24.ro folosind Pyppeteer și codul produsului.
    """
    if not product_code:
        return None
        
    search_url = f"https://dealer.moto24.ro/?s={product_code}&post_type=product"
    
    try:
        return asyncio.get_event_loop().run_until_complete(_scrape_moto24_async_search(search_url, product_code))
    except Exception as e:
        # Eroare de wrapper/async
        print(f"❌ EROARE GENERALĂ la Moto24 (Wrapper/Async): {e}")
        return None

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
        
        await page.goto(search_url, {'timeout': 30000, 'waitUntil': 'networkidle2'})
        await asyncio.sleep(3) 

        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # --- Selectori Stratificați pentru a prinde prețul ---

        # 1. Selectorul precis din cardul de produs (cel mai probabil)
        price_element = soup.select_one('p.product-price span[data-nosnippet]') 
        
        # 2. Selectorul WooCommerce standard (din orice card de produs)
        if not price_element:
            price_element = soup.select_one('.products .woocommerce-Price-amount') 

        # 3. Selectorul generic de preț din card
        if not price_element:
            price_element = soup.select_one('.products .price')


        if price_element:
            price_text = price_element.get_text(strip=True)
            
            # Curățarea și Conversia Prețului
            price_text = price_text.replace('.', '') 
            price_text = price_text.replace(',', '.') 
            cleaned_price = re.sub(r'[^\d.]', '', price_text) 
            
            if cleaned_price:
                price_ron = float(cleaned_price)
                print(f"      ✅ Preț RON extras (Pyppeteer/JS): {price_ron} RON")
                return price_ron
            
        print(f"❌ EROARE: Elementul de preț nu a fost găsit în rezultatele căutării Moto24.")
        return None

    except Exception as e:
        print(f"❌ EXCEPȚIE la Pyppeteer/Randare Moto24: {e}")
        return None
    finally:
        if browser:
            await browser.close()

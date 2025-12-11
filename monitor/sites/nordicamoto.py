# ... (restul codului, inclusiv funcția clean_and_convert_price și scrape_nordicamoto_search) ...

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
        
        # PASUL 1: Caută produsul și extrage link-ul
        await page.goto(search_url, {'timeout': 40000, 'waitUntil': 'networkidle2'})
        await asyncio.sleep(5) 

        link_selector = '.products .product:first-child a[href]'
        
        # 🛑 CORECȚIE SINTAXĂ JAVASCRIPT FINALĂ
        product_link = await page.evaluate(f'''
            {{
                const linkElement = document.querySelector('{link_selector}');
                if (linkElement) {{
                    return linkElement.href;
                }}
                const fallbackLink = document.querySelector('.product a');
                if (fallbackLink) {{
                    return fallbackLink.href;
                }}
                return null;
            }}
        ''')

        if not product_link:
            print(f"❌ EROARE: Nu a fost găsit un link de produs în rezultatele căutării Nordicamoto (Cod: {product_code}).")
            return None
        
        # ... (restul logicii de scraping) ...
        # (Lăsați neschimbat de aici încolo)
        print(f"      Navighez la pagina produsului: {product_link}")
        await page.goto(product_link, {'timeout': 40000, 'waitUntil': 'networkidle2'})
        await asyncio.sleep(5) 

        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        price_selectors = [
            '.summary .woocommerce-Price-amount', 
            '.product-info .price',                   
            'p.price',                           
            '.price .amount',                    
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

    except Exception as e:
        print(f"❌ EXCEPȚIE la Pyppeteer/Randare Nordicamoto: {e}")
        return None
    finally:
        if browser:
            await browser.close()

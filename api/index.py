from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import random
import time

app = FastAPI(title="ZenScraper Clone", version="3.0.0")

# --- PATH CONFIG ---
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_file_dir)
templates_dir = os.path.join(project_root, "templates")
templates = Jinja2Templates(directory=templates_dir)

# --- REAL USER AGENTS (Agar dianggap manusia) ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
]

class ScrapeRequest(BaseModel):
    url: HttpUrl
    selector: Optional[str] = None
    premium_proxy: bool = False
    anti_bot: bool = True
    render_js: bool = False # Note: Full JS render butuh Headless Browser (berat untuk serverless), ini flag logic.

def get_headers(anti_bot: bool):
    """Membuat Headers palsu agar terlihat seperti browser asli"""
    if not anti_bot:
        return {'User-Agent': 'ProScraper/1.0'}
    
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }

def fix_assets(soup, base_url):
    """Memperbaiki asset untuk visual preview"""
    for tag in soup.find_all(['img', 'script', 'link', 'a']):
        attr = 'href' if tag.name in ['a', 'link'] else 'src'
        if tag.get(attr):
            # Biarkan data URI atau anchor link
            if tag[attr].startswith(('data:', '#', 'javascript:')):
                continue
            tag[attr] = urljoin(str(base_url), tag[attr])
    
    # Inject base tag
    if not soup.head:
        soup.insert(0, soup.new_tag("head"))
    if not soup.find("base"):
        base_tag = soup.new_tag("base", href=str(base_url))
        soup.head.insert(0, base_tag)
    return str(soup)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/scrape")
async def scrape(payload: ScrapeRequest):
    target_url = str(payload.url)
    
    # 1. Konfigurasi Request Real
    headers = get_headers(payload.anti_bot)
    
    # Simulasi Proxy (Logic only, karena kita butuh kredensial proxy asli untuk rotating IP)
    proxies = None
    if payload.premium_proxy:
        # Jika punya proxy rotation service, masukkan disini.
        # proxies = {"http": "http://user:pass@gate.zenrows.com:8001", ...}
        pass 

    try:
        start_time = time.time()
        
        # 2. EKSEKUSI REQUEST
        response = requests.get(
            target_url, 
            headers=headers, 
            proxies=proxies, 
            timeout=15,
            allow_redirects=True
        )
        
        elapsed = round(time.time() - start_time, 2)
        
        # 3. Handle Encoding
        response.encoding = response.apparent_encoding

        # 4. Parsing Data
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Data Extraction
        extracted_data = {
            "title": soup.title.string.strip() if soup.title else None,
            "description": soup.find("meta", attrs={"name": "description"})["content"] if soup.find("meta", attrs={"name": "description"}) else None,
            "h1": [h.get_text(strip=True) for h in soup.find_all("h1")],
            "links_count": len(soup.find_all("a")),
            "images_count": len(soup.find_all("img")),
        }

        # Custom Selector
        if payload.selector:
            selection = soup.select(payload.selector)
            extracted_data["custom_selector_results"] = [el.get_text(strip=True) for el in selection]

        # 5. Siapkan Output
        return {
            "success": True,
            "status_code": response.status_code,
            "time_taken": f"{elapsed}s",
            "original_url": target_url,
            "response_headers": dict(response.headers),
            "data": extracted_data,
            "html_preview": fix_assets(soup, target_url)
        }

    except Exception as e:
        return {
            "success": False, 
            "error": str(e),
            "status_code": 500
        }

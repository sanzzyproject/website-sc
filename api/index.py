from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
from typing import Optional
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import random
import time
import ujson
from loguru import logger
from cachetools import TTLCache
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

# Setup Logging
logger.add("scraper.log", rotation="1 MB", level="INFO")

app = FastAPI(title="SannScraper Lite", version="4.0.0")

# --- PATH CONFIG ---
# Konfigurasi path agar kompatibel dengan Local dan Vercel
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_file_dir)
templates_dir = os.path.join(project_root, "templates")

# Fallback jika folder templates ada di folder yang sama (untuk struktur simple)
if not os.path.exists(templates_dir):
    templates_dir = os.path.join(current_file_dir, "templates")

templates = Jinja2Templates(directory=templates_dir)

# --- CACHE SETUP (Max 100 items, 5 min TTL) ---
request_cache = TTLCache(maxsize=100, ttl=300)

# --- REAL USER AGENTS ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
]

class ScrapeRequest(BaseModel):
    url: HttpUrl
    selector: Optional[str] = None
    premium_proxy: bool = False
    anti_bot: bool = True
    render_js: bool = False # Note: Fitur JS Render dinonaktifkan demi kestabilan Vercel

def get_headers(anti_bot: bool):
    """Membuat Headers palsu agar request diterima website target"""
    if not anti_bot:
        return {'User-Agent': 'SannScraper/1.0'}
    
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

def fix_assets(html_content, base_url):
    """Memperbaiki link gambar/css agar bisa dipreview"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Inject Base Tag agar relative link (seperti /style.css) bekerja
        if not soup.head:
            soup.insert(0, soup.new_tag("head"))
        if not soup.find("base"):
            base_tag = soup.new_tag("base", href=str(base_url))
            soup.head.insert(0, base_tag)

        return str(soup)
    except Exception:
        return html_content

# --- ASYNC SCRAPING ENGINE (HTTPX) ---
# Retry 3x kalau gagal koneksi, jeda 1 detik
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1), retry=retry_if_exception_type(httpx.RequestError))
async def fetch_url(url: str, headers: dict, proxies: dict = None):
    async with httpx.AsyncClient(http2=True, proxies=proxies, timeout=15.0, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.content, response.headers, response.status_code

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/scrape")
async def scrape(payload: ScrapeRequest):
    target_url = str(payload.url)
    
    # 1. Cek Cache (Agar hemat resource)
    if target_url in request_cache:
        return request_cache[target_url]

    headers = get_headers(payload.anti_bot)
    
    # Logic Proxy Placeholder (Siapkan tempatnya jika nanti punya proxy premium)
    proxies = None
    if payload.premium_proxy:
        pass 
    
    try:
        start_time = time.time()
        
        # 2. JALANKAN REQUEST (HTTPX - Aman & Cepat)
        content, res_headers, status_code = await fetch_url(target_url, headers, proxies)
        
        elapsed = round(time.time() - start_time, 2)
        
        # 3. Parsing Data
        soup = BeautifulSoup(content, 'html.parser')
        
        extracted_data = {
            "title": soup.title.string.strip() if soup.title else None,
            "description": soup.find("meta", attrs={"name": "description"})["content"] if soup.find("meta", attrs={"name": "description"}) else None,
            "h1_tags": [h.get_text(strip=True) for h in soup.find_all("h1")],
            "links_found": len(soup.find_all("a")),
            "images_found": len(soup.find_all("img")),
        }

        # Custom Selector
        if payload.selector:
            selection = soup.select(payload.selector)
            extracted_data["selector_data"] = [el.get_text(strip=True) for el in selection]

        result = {
            "success": True,
            "status": status_code,
            "time": f"{elapsed}s",
            "method": "HTTP/2 Async", # Metode yang digunakan
            "url": target_url,
            "data": extracted_data,
            "html_preview": fix_assets(content, target_url),
            "headers": dict(res_headers)
        }

        # Simpan ke cache
        request_cache[target_url] = result
        return result

    except httpx.HTTPStatusError as e:
        return {
            "success": False, 
            "error": f"Website Error: {e.response.status_code}", 
            "status_code": e.response.status_code
        }
    except Exception as e:
        logger.error(f"Error scraping {target_url}: {str(e)}")
        return {
            "success": False, 
            "error": str(e), 
            "status_code": 500
        }

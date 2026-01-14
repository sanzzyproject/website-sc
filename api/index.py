from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
from typing import Optional
import httpx
from bs4 import BeautifulSoup
import os
import random
import time
import logging # Pengganti Loguru
import json # Pengganti Ujson

# Setup Logging Standard
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scraper")

app = FastAPI(title="SannScraper Lite", version="4.0.0")

# --- PATH CONFIG ---
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_file_dir)
templates_dir = os.path.join(project_root, "templates")

if not os.path.exists(templates_dir):
    templates_dir = os.path.join(current_file_dir, "templates")

templates = Jinja2Templates(directory=templates_dir)

# --- SIMPLE CACHE ---
# Di serverless, complex cache library itu overkill karena memory reset tiap function sleep.
# Kita pakai Dictionary biasa.
request_cache = {} 

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
    render_js: bool = False 

def get_headers(anti_bot: bool):
    """Membuat Headers palsu"""
    if not anti_bot:
        return {'User-Agent': 'SannScraper/1.0'}
    
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

def fix_assets(html_content, base_url):
    """Memperbaiki link gambar/css"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        if not soup.head:
            soup.insert(0, soup.new_tag("head"))
        if not soup.find("base"):
            base_tag = soup.new_tag("base", href=str(base_url))
            soup.head.insert(0, base_tag)
        return str(soup)
    except Exception:
        return html_content

# --- ASYNC SCRAPING (Manual Retry) ---
# Pengganti library Tenacity untuk mengurangi beban
async def fetch_url(url: str, headers: dict, proxies: dict = None):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(http2=False, proxies=proxies, timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.content, response.headers, response.status_code
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            if attempt == max_retries - 1: # Jika ini attempt terakhir
                raise e
            time.sleep(1) # Tunggu 1 detik sebelum retry
    return None, None, None

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/scrape")
async def scrape(payload: ScrapeRequest):
    target_url = str(payload.url)
    
    # 1. Cek Cache Simple
    if target_url in request_cache:
        return request_cache[target_url]

    headers = get_headers(payload.anti_bot)
    proxies = None # Placeholder proxy
    
    try:
        start_time = time.time()
        
        # 2. REQUEST
        content, res_headers, status_code = await fetch_url(target_url, headers, proxies)
        
        elapsed = round(time.time() - start_time, 2)
        
        # 3. PARSING
        soup = BeautifulSoup(content, 'html.parser')
        
        extracted_data = {
            "title": soup.title.string.strip() if soup.title else None,
            "description": soup.find("meta", attrs={"name": "description"})["content"] if soup.find("meta", attrs={"name": "description"}) else None,
            "h1_tags": [h.get_text(strip=True) for h in soup.find_all("h1")],
            "links_found": len(soup.find_all("a")),
            "images_found": len(soup.find_all("img")),
        }

        if payload.selector:
            selection = soup.select(payload.selector)
            extracted_data["selector_data"] = [el.get_text(strip=True) for el in selection]

        result = {
            "success": True,
            "status": status_code,
            "time": f"{elapsed}s",
            "method": "HTTP Async",
            "url": target_url,
            "data": extracted_data,
            "html_preview": fix_assets(content, target_url),
            "headers": dict(res_headers)
        }

        # Simpan ke cache (batasi memori dengan hapus jika terlalu besar)
        if len(request_cache) > 50: 
            request_cache.clear()
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

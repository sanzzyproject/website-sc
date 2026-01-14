from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict

# --- NEW IMPORTS ---
import httpx
from requests_html import AsyncHTMLSession
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from loguru import logger
from cachetools import TTLCache
import ujson

# --- STANDARD IMPORTS ---
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import random
import time
import asyncio

# Setup Logging
logger.add("scraper.log", rotation="1 MB", level="INFO")

app = FastAPI(title="ZenScraper Clone", version="3.5.0")

# --- PATH CONFIG ---
current_file_dir = os.path.dirname(os.path.abspath(__file__))
# Asumsi struktur folder: project/api/index.py atau project/main.py
# Sesuaikan templates dir jika perlu
project_root = os.path.dirname(current_file_dir) 
templates_dir = os.path.join(project_root, "templates")

# Fallback jika templates dir tidak ketemu (untuk single file run)
if not os.path.exists(templates_dir):
    templates_dir = os.path.join(current_file_dir, "templates")
    if not os.path.exists(templates_dir):
        # Buat dummy agar tidak error saat init, tapi HTML akan error jika file tidak ada
        os.makedirs(templates_dir, exist_ok=True)

templates = Jinja2Templates(directory=templates_dir)

# --- CACHE SETUP (In-Memory, Max 100 items, 5 min TTL) ---
request_cache = TTLCache(maxsize=100, ttl=300)

# --- REAL USER AGENTS ---
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
    render_js: bool = False

def get_headers(anti_bot: bool):
    """Membuat Headers palsu agar terlihat seperti browser asli"""
    if not anti_bot:
        return {'User-Agent': 'ProScraper/2.0'}
    
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

def fix_assets(html_content, base_url):
    """Memperbaiki asset untuk visual preview menggunakan lxml (lebih cepat)"""
    try:
        soup = BeautifulSoup(html_content, 'lxml') # Gunakan lxml parser
    except:
        soup = BeautifulSoup(html_content, 'html.parser')

    for tag in soup.find_all(['img', 'script', 'link', 'a']):
        attr = 'href' if tag.name in ['a', 'link'] else 'src'
        if tag.get(attr):
            if tag[attr].startswith(('data:', '#', 'javascript:')):
                continue
            tag[attr] = urljoin(str(base_url), tag[attr])
    
    if not soup.head:
        soup.insert(0, soup.new_tag("head"))
    if not soup.find("base"):
        base_tag = soup.new_tag("base", href=str(base_url))
        soup.head.insert(0, base_tag)
    return str(soup)

# --- CORE SCRAPING LOGIC WITH RETRY ---
# Retry 3 kali jika terjadi error koneksi/timeout, jeda 1 detik
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1), retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)))
async def fetch_url_httpx(url: str, headers: dict, proxies: dict = None):
    async with httpx.AsyncClient(http2=True, proxies=proxies, timeout=20.0, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.content, response.headers, response.status_code

async def fetch_url_render_js(url: str, headers: dict):
    """Render JS menggunakan requests-html"""
    asession = AsyncHTMLSession()
    # Note: requests-html browser args mungkin perlu disesuaikan di serverless (sandbox disabled)
    try:
        r = await asession.get(url, headers=headers, timeout=20)
        await r.html.arender(timeout=20, sleep=1) # Render JS
        return r.html.html, r.headers, r.status_code
    except Exception as e:
        logger.error(f"Render JS Error: {e}")
        # Fallback ke httpx jika render gagal (misal tidak ada chromium)
        return await fetch_url_httpx(url, headers)
    finally:
        await asession.close()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Langsung return HTML di bawah (agar single file ready) jika template tidak ditemukan
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/scrape")
async def scrape(payload: ScrapeRequest):
    target_url = str(payload.url)
    logger.info(f"Scraping Request: {target_url} | JS: {payload.render_js} | Proxy: {payload.premium_proxy}")
    
    # 1. Check Cache (Simple URL based)
    cache_key = f"{target_url}_{payload.render_js}"
    if cache_key in request_cache:
        logger.info("Serving from cache")
        return request_cache[cache_key]

    headers = get_headers(payload.anti_bot)
    
    # Logic Proxy Placeholder
    proxies = None
    if payload.premium_proxy:
        # Example: proxies = "http://user:pass@gate.premium-proxy.com:8000"
        pass 

    try:
        start_time = time.time()
        
        # 2. EKSEKUSI REQUEST (HTTPX atau Requests-HTML)
        if payload.render_js:
            content, res_headers, status_code = await fetch_url_render_js(target_url, headers)
        else:
            content, res_headers, status_code = await fetch_url_httpx(target_url, headers, proxies)
        
        elapsed = round(time.time() - start_time, 2)
        
        # 3. Parsing Data (Menggunakan lxml via BS4)
        try:
            soup = BeautifulSoup(content, 'lxml')
        except:
            soup = BeautifulSoup(content, 'html.parser')
        
        # Data Extraction
        extracted_data = {
            "title": soup.title.string.strip() if soup.title else None,
            "description": soup.find("meta", attrs={"name": "description"})["content"] if soup.find("meta", attrs={"name": "description"}) else None,
            "h1": [h.get_text(strip=True) for h in soup.find_all("h1")],
            "links_count": len(soup.find_all("a")),
            "images_count": len(soup.find_all("img")),
            "meta_tags": len(soup.find_all("meta"))
        }

        # Custom Selector
        if payload.selector:
            selection = soup.select(payload.selector)
            extracted_data["custom_selector_results"] = [el.get_text(strip=True) for el in selection]

        # 4. Siapkan Output
        result = {
            "success": True,
            "status_code": status_code,
            "time_taken": f"{elapsed}s",
            "method": "JS Render" if payload.render_js else "HTTP/2 Async",
            "original_url": target_url,
            "response_headers": dict(res_headers),
            "data": extracted_data,
            "html_preview": fix_assets(content, target_url)
        }

        # Simpan ke cache
        request_cache[cache_key] = result
        return result

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP Error: {e}")
        return {
            "success": False,
            "error": f"HTTP Error: {e.response.status_code}",
            "status_code": e.response.status_code
        }
    except Exception as e:
        logger.exception("Scraping Failed")
        return {
            "success": False, 
            "error": str(e),
            "status_code": 500
        }

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
from typing import Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os

app = FastAPI(
    title="ProScraper Ultimate",
    description="Advanced Serverless Web Scraper",
    version="2.0.0"
)

# --- KONFIGURASI PATH (SAMA SEPERTI SEBELUMNYA) ---
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_file_dir)
templates_dir = os.path.join(project_root, "templates")

templates = Jinja2Templates(directory=templates_dir)

# Model data input diperbarui
class ScrapeRequest(BaseModel):
    url: HttpUrl
    selector: Optional[str] = None # Fitur baru: Custom CSS Selector

def fix_relative_urls(soup, base_url):
    """Memperbaiki link relative agar preview visual tetap jalan"""
    tags = {'img': 'src', 'script': 'src', 'link': 'href', 'a': 'href', 'iframe': 'src'}
    for tag_name, attribute in tags.items():
        for element in soup.find_all(tag_name):
            val = element.get(attribute)
            if val and not val.startswith(('http', 'https', 'data:', '#')):
                element[attribute] = urljoin(str(base_url), val)
    
    if not soup.head:
        soup.insert(0, soup.new_tag("head"))
    base_tag = soup.new_tag("base", href=str(base_url))
    if soup.head.find("base"):
        soup.head.find("base").replace_with(base_tag)
    else:
        soup.head.insert(0, base_tag)
    return str(soup)

def extract_data(soup, base_url, custom_selector=None):
    """Fungsi inti scraping data"""
    data = {
        "metadata": {},
        "links": [],
        "images": [],
        "custom_data": []
    }

    # 1. Extract Metadata
    data["metadata"]["title"] = soup.title.string if soup.title else "No Title"
    meta_desc = soup.find("meta", attrs={"name": "description"})
    data["metadata"]["description"] = meta_desc["content"] if meta_desc else ""
    
    # 2. Extract All Links
    for link in soup.find_all('a', href=True):
        full_url = urljoin(str(base_url), link['href'])
        data["links"].append({
            "text": link.get_text(strip=True),
            "url": full_url
        })

    # 3. Extract All Images
    for img in soup.find_all('img', src=True):
        full_src = urljoin(str(base_url), img['src'])
        data["images"].append({
            "alt": img.get('alt', ''),
            "src": full_src
        })

    # 4. Custom CSS Selector Extraction (Fitur Power User)
    if custom_selector:
        try:
            elements = soup.select(custom_selector)
            for el in elements:
                data["custom_data"].append(el.get_text(strip=True))
        except Exception:
            data["custom_data"] = ["Error: Invalid CSS Selector"]

    return data

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/scrape")
async def scrape_url(payload: ScrapeRequest):
    target_url = str(payload.url)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(target_url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Logic Scrape Data
        extracted_data = extract_data(soup, target_url, payload.selector)

        # Logic Preview Visual (HTML yang sudah dibersihkan)
        cleaned_html = fix_relative_urls(soup, target_url)

        return {
            "status": "success",
            "url": target_url,
            "status_code": response.status_code,
            "data": extracted_data, # Hasil Scrape JSON
            "html": cleaned_html    # Hasil Preview Visual
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

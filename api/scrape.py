from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os

app = FastAPI(
    title="SaaS Web Scraper",
    description="Serverless Web Scraper for Vercel",
    version="1.0.0"
)

# Konfigurasi Template
# Menggunakan path relative untuk kompatibilitas Vercel/Local
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(base_dir, "templates"))

# Model data untuk input
class ScrapeRequest(BaseModel):
    url: HttpUrl

def fix_relative_urls(soup, base_url):
    """
    Mengubah semua relative link (img, css, script, a) menjadi absolute URL
    agar preview bisa tampil benar di iframe.
    """
    tags = {
        'img': 'src',
        'script': 'src',
        'link': 'href',
        'a': 'href',
        'iframe': 'src'
    }

    for tag_name, attribute in tags.items():
        for element in soup.find_all(tag_name):
            val = element.get(attribute)
            if val and not val.startswith(('http', 'https', 'data:')):
                element[attribute] = urljoin(str(base_url), val)
                
    # Tambahkan base tag sebagai fail-safe
    if not soup.head:
        soup.insert(0, soup.new_tag("head"))
    
    base_tag = soup.new_tag("base", href=str(base_url))
    if soup.head.find("base"):
        soup.head.find("base").replace_with(base_tag)
    else:
        soup.head.insert(0, base_tag)

    return str(soup)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Render halaman utama UI."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/scrape")
async def scrape_url(payload: ScrapeRequest):
    """Endpoint backend untuk melakukan scraping."""
    target_url = str(payload.url)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # 1. Request ke target website
        response = requests.get(target_url, headers=headers, timeout=10)
        response.raise_for_status()

        # 2. Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # 3. Cleanup & Fix Links (PENTING untuk preview)
        cleaned_html = fix_relative_urls(soup, target_url)

        return {
            "status": "success",
            "url": target_url,
            "status_code": response.status_code,
            "html": cleaned_html
        }

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Request Timeout. Website target terlalu lambat.")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=502, detail="Gagal terhubung ke website target.")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error scraping: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# Handler untuk Vercel Serverless (WSGI wrapper tidak diperlukan untuk FastAPI versi baru di Vercel)
# Tapi jika dibutuhkan debugging local:
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

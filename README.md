# SannScraper 🚀

![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green?style=flat-square&logo=fastapi)
![Uvicorn](https://img.shields.io/badge/Uvicorn-0.27.0-orange?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square)
![Vercel](https://img.shields.io/badge/deploy-vercel-000000?style=flat-square&logo=vercel)
![GitHub Workflow](https://img.shields.io/github/workflow/status/username/sannscraper/CI?style=flat-square)
![Stars](https://img.shields.io/github/stars/username/sannscraper?style=social)
![Forks](https://img.shields.io/github/forks/username/sannscraper?style=social)

**SannScraper** adalah serverless **Python Web Scraper** berbasis FastAPI, siap digunakan untuk ekstraksi data web cepat, aman, dan efisien. Mendukung preview HTML interaktif, anti-bot headers, proxy, dan CSS selector kustom.

---

## ✨ Fitur Utama

- **Anti-Bot Headers:** Auto-rotate User-Agent agar request terlihat seperti browser asli (Chrome/Firefox).  
- **Premium Proxy (Logic Placeholder):** Siap dikonfigurasi untuk rotating IP.  
- **Render JS (Flag Logic):** Opsi untuk future headless browser rendering (React/Vue/Angular).  
- **Custom CSS Selector:** Ekstraksi spesifik elemen (misal `div.product-price`).  
- **JSON Result & HTML Preview:** Otomatis ekstraksi title, description, h1, jumlah link, gambar, plus visual preview halaman dengan asset diperbaiki.  
- **Response Headers:** Menampilkan headers asli dari request.  

---

## Instalasi

1. Clone repository:
```bash
git clone https://github.com/username/sannscraper.git
cd sannscraper
```

2. Buat virtual environment (opsional tapi disarankan):
```bash
python -m venv venv
source venv/bin/activate  # Linux / Mac
venv\Scripts\activate     # Windows
```

3. Install dependency:
```bash
pip install -r requirements.txt
```

4. Jalankan server FastAPI:
```bash
uvicorn api.index:app --reload
```

5. Akses di browser:
```bash
http://localhost:8000
```

## 📁Struktur Peoject:
```text
sannscraper/
├─ api/
│  └─ index.py          # FastAPI main application
├─ templates/
│  └─ index.html        # UI HTML + CSS + JS
├─ public/              # Static files (icons, images, dll)
├─ utils/               # Utility functions (kosong, siap dikembangkan)
├─ types/               # Type definitions (kosong, siap dikembangkan)
├─ requirements.txt     # Dependency Python
└─ vercel.json          # Konfigurasi deploy Vercel
```



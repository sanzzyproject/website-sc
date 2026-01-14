# SannScraper 🚀

![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green?style=flat-square&logo=fastapi)
![Uvicorn](https://img.shields.io/badge/Uvicorn-0.27.0-orange?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square)

**SannScraper** adalah serverless **Python Web Scraper** berbasis FastAPI yang memungkinkan Anda melakukan ekstraksi data web secara cepat, aman, dan efisien. Alat ini memiliki preview HTML interaktif, opsi anti-bot, proxy, dan dukungan selector CSS kustom.

---

## Fitur Utama

- **Anti-Bot Headers:** Memutar User-Agent agar request terlihat berasal dari browser asli.
- **Premium Proxy (Logic Only):** Siap dikonfigurasi untuk proxy rotasi.
- **Render JS:** Flag untuk future headless browser rendering (React/Vue/Angular).
- **Custom CSS Selector:** Ekstraksi elemen tertentu sesuai selector.
- **HTML Preview:** Preview halaman hasil scraping dengan asset diperbaiki.
- **JSON Result:** Ekstraksi otomatis title, description, h1, jumlah link, dan gambar.

---

## Instalasi

1. Clone repository:
```bash
git clone https://github.com/username/sannscraper.git
cd sannscraper

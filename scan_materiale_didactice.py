import os
import time
import random
import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook

SITEMAP_URL = "https://materialedidactice.ro/sitemap_index.xml"

# descarcă o pagină și întoarce soup
def get_soup(url):
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

# colectează toate linkurile de produse din cele 3 sitemap-uri
def get_all_links():
    sitemap = get_soup(SITEMAP_URL)
    links = []
    for loc in sitemap.find_all("loc"):
        url = loc.text.strip()
        if "product-sitemap" in url and "product_cat" not in url:
            sm = get_soup(url)
            for l in sm.find_all("loc"):
                links.append(l.text.strip())
    return links

# parsează o pagină de produs
def parse_product(url):
    try:
        soup = get_soup(url)
        title = soup.find("h1", class_="product_title").get_text(strip=True)

        # SKU
        sku = None
        sku_tag = soup.find("span", class_="sku")
        if sku_tag:
            sku = sku_tag.get_text(strip=True)

        # prețuri
        price_current = None
        price_original = None

        price_current_tag = soup.find("ins")
        if price_current_tag:
            price_current = price_current_tag.get_text(strip=True)
        else:
            # dacă nu există reducere, prețul e direct
            price_current_tag = soup.find("span", class_="woocommerce-Price-amount")
            if price_current_tag:
                price_current = price_current_tag.get_text(strip=True)

        price_original_tag = soup.find("del")
        if price_original_tag:
            price_original = price_original_tag.get_text(strip=True)

        return {
            "title": title,
            "sku": sku,
            "price_original": price_original,
            "price_current": price_current,
            "url": url,
        }
    except Exception as e:
        print(f"Eroare la {url}: {e}")
        return None

def main():
    start_index = int(os.getenv("START_INDEX", 0))
    end_index = int(os.getenv("END_INDEX", 50))

    print("=== Încep scanarea site-ului prin sitemap ===")
    links = get_all_links()
    print(f"✅ Am găsit {len(links)} linkuri în sitemap.")
    print(f"📦 Procesez produsele {start_index+1} → {end_index}")

    wb = Workbook()
    ws = wb.active
    ws.append(["Titlu", "SKU", "Preț inițial", "Preț curent", "Link"])

    for i, url in enumerate(links[start_index:end_index], start=start_index+1):
        print(f"[{i}/{end_index}] {url}")
        data = parse_product(url)
        if data:
            ws.append([
                data["title"],
                data["sku"],
                data["price_original"],
                data["price_current"],
                data["url"]
            ])
        # delay random 6–8 secunde
        time.sleep(random.uniform(6, 8))

    filename = f"produse_{start_index+1}_{end_index}.xlsx"
    wb.save(filename)
    print(f"📊 Datele au fost salvate în {filename}")

if __name__ == "__main__":
    main()


import requests
from bs4 import BeautifulSoup
import time
import random
import os
import openpyxl

SITEMAP_URL = "https://materialedidactice.ro/sitemap_index.xml"

# === helper să descarce și să parseze un URL ===
def get_soup(url):
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

# === ia toate linkurile de produs din sitemap ===
def get_product_links():
    print("📥 Descarc sitemap principal:", SITEMAP_URL)
    sitemap = get_soup(SITEMAP_URL)
    loc_tags = sitemap.find_all("loc")

    product_sitemaps = [
        loc.get_text()
        for loc in loc_tags
        if "product-sitemap" in loc.get_text()
    ]

    links = []
    for sm in product_sitemaps:
        print("   ↳ verific", sm)
        sm_soup = get_soup(sm)
        for loc in sm_soup.find_all("loc"):
            links.append(loc.get_text())

    print(f"✅ Am găsit {len(links)} linkuri în sitemap.")
    return links

# === extrage info produs ===
def parse_product(url):
    try:
        soup = get_soup(url)

        # titlu
        title_tag = soup.find("h1", class_="product_title")
        title = title_tag.get_text(strip=True) if title_tag else "N/A"

        # sku
        sku_tag = soup.find("span", class_="sku")
        sku = sku_tag.get_text(strip=True) if sku_tag else "N/A"

        # preț curent
        price_tag = soup.find("p", class_="price")
        current_price = "N/A"
        original_price = "N/A"
        if price_tag:
            ins = price_tag.find("ins")
            del_tag = price_tag.find("del")

            if ins:  # redus
                current_price = ins.get_text(strip=True).replace("Lei", "").replace(".", "").replace(",", ".")
                if del_tag:
                    original_price = del_tag.get_text(strip=True).replace("Lei", "").replace(".", "").replace(",", ".")
            else:  # fără reducere
                current_price = price_tag.get_text(strip=True).replace("Lei", "").replace(".", "").replace(",", ".")
                original_price = current_price

        return {
            "title": title,
            "sku": sku,
            "price_original": original_price,
            "price_current": current_price,
            "url": url
        }

    except Exception as e:
        print(f"Eroare la {url}: {e}")
        return None

# === salvează în XLSX ===
def save_to_excel(data, filename):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Titlu", "SKU", "Preț inițial", "Preț curent", "Link"])
    for item in data:
        ws.append([
            item["title"],
            item["sku"],
            item["price_original"],
            item["price_current"],
            item["url"]
        ])
    wb.save(filename)
    print(f"📊 Datele au fost salvate în {filename}")

# === main ===
def main():
    links = get_product_links()

    start_index = int(os.getenv("START_INDEX", 0))
    end_index = int(os.getenv("END_INDEX", len(links)))
    batch_links = links[start_index:end_index]

    print(f"📦 Procesez produsele {start_index+1} → {end_index}")

    data = []
    for i, link in enumerate(batch_links, start=1):
        print(f"[{i}/{len(batch_links)}] {link}")
        product = parse_product(link)
        if product:
            data.append(product)
        time.sleep(random.uniform(6, 8))

    filename = f"produse_{start_index+1}_{end_index}.xlsx"
    save_to_excel(data, filename)

if __name__ == "__main__":
    main()

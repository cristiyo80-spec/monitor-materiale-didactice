import os
import time
import random
import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook

SITEMAP_URL = "https://materialedidactice.ro/sitemap_index.xml"

def get_soup(url):
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def get_all_links():
    sitemap = get_soup(SITEMAP_URL)
    links = []
    for loc in sitemap.find_all("loc"):
        url = loc.text.strip()
        # luăm doar sitemap-urile de produse (nu categorii, nu local)
        if "product-sitemap" in url and "product_cat" not in url:
            sm = get_soup(url)
            for l in sm.find_all("loc"):
                links.append(l.text.strip())
    return links

def extract_prices(soup):
    """
    Extrage prețul inițial și prețul curent dintr-o pagină de produs.
    - Dacă există <del> → acesta e prețul inițial.
    - Dacă există <ins> → acesta e prețul curent.
    - Dacă NU există <del>/<ins> → prețul unic se salvează ca preț inițial și curent.
    """
    pret_initial = ""
    pret_curent = ""

    price_block = soup.find("p", class_="price")
    if not price_block:
        return pret_initial, pret_curent

    del_tag = price_block.find("del")
    if del_tag:
        pret_initial = del_tag.get_text(strip=True).replace("\xa0", " ")

    ins_tag = price_block.find("ins")
    if ins_tag:
        pret_curent = ins_tag.get_text(strip=True).replace("\xa0", " ")

    if not del_tag and not ins_tag:
        single_price = price_block.find("span", class_="woocommerce-Price-amount")
        if single_price:
            pret_curent = single_price.get_text(strip=True).replace("\xa0", " ")
            pret_initial = pret_curent

    return pret_initial, pret_curent

def parse_product(url):
    try:
        soup = get_soup(url)
        title_tag = soup.find("h1", class_="product_title")
        if not title_tag:
            print(f"Eroare la {url}: nu am găsit titlu produs")
            return None
        title = title_tag.get_text(strip=True)

        sku = ""
        sku_tag = soup.find("span", class_="sku")
        if sku_tag:
            sku = sku_tag.get_text(strip=True)

        pret_initial, pret_curent = extract_prices(soup)

        return {
            "title": title,
            "sku": sku,
            "price_original": pret_initial,
            "price_current": pret_curent,
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
        time.sleep(random.uniform(6, 8))  # delay safe

    filename = f"produse_{start_index+1}_{end_index}.xlsx"
    wb.save(filename)
    print(f"📊 Datele au fost salvate în {filename}")

if __name__ == "__main__":
    main()

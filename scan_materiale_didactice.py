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

def clean_price_text(txt: str) -> str:
    if not txt:
        return ""
    # eliminăm NBSP și spații redundante
    txt = txt.replace("\xa0", "").replace(" ", "")
    return txt

def extract_prices_from_block(price_block):
    pret_initial = ""
    pret_curent = ""

    if not price_block:
        return pret_initial, pret_curent

    del_tag = price_block.find("del")
    if del_tag:
        pret_initial = clean_price_text(del_tag.get_text(strip=True))

    ins_tag = price_block.find("ins")
    if ins_tag:
        pret_curent = clean_price_text(ins_tag.get_text(strip=True))

    if not del_tag and not ins_tag:
        single = price_block.find("span", class_="woocommerce-Price-amount")
        if single:
            val = clean_price_text(single.get_text(strip=True))
            pret_initial = val
            pret_curent = val

    return pret_initial, pret_curent

def extract_prices(soup, title_tag=None):
    """
    IA PREȚUL DOAR DIN ZONA PRODUSULUI:
    - după <h1 class="product_title">, următorul <p class="price">
    - fallback: în summary .price
    - fallback final: primul <p class="price">
    """
    price_block = None

    if title_tag:
        price_block = title_tag.find_next("p", class_="price")

    if not price_block:
        pb = soup.select_one("div.summary p.price")
        if pb:
            price_block = pb

    if not price_block:
        price_block = soup.find("p", class_="price")

    return extract_prices_from_block(price_block)

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

        pret_initial, pret_curent = extract_prices(soup, title_tag=title_tag)

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

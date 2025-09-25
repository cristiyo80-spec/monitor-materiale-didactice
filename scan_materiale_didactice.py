import requests
from bs4 import BeautifulSoup
import time
import random
import os
from openpyxl import Workbook

# Variabile pentru batch-uri
START_INDEX = int(os.getenv("START_INDEX", 0))
END_INDEX = int(os.getenv("END_INDEX", 100))

# Funcție pentru request cu retry
def get_soup(url):
    for _ in range(3):
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                return BeautifulSoup(r.text, "lxml")
        except Exception as e:
            print(f"Eroare la {url}: {e}")
            time.sleep(5)
    return None

# Preia linkurile din sitemap
def get_sitemap_links():
    sitemap_index = "https://materialedidactice.ro/sitemap_index.xml"
    r = requests.get(sitemap_index)
    soup = BeautifulSoup(r.text, "xml")

    product_sitemaps = [
        loc.text for loc in soup.find_all("loc") if "product-sitemap" in loc.text
    ]
    all_links = []
    for sm in product_sitemaps:
        r = requests.get(sm)
        sm_soup = BeautifulSoup(r.text, "xml")
        links = [loc.text for loc in sm_soup.find_all("loc")]
        all_links.extend(links)

    print(f"✅ Am găsit {len(all_links)} linkuri în sitemap.")
    return all_links

# Extrage date produs
def scrape_product(url):
    soup = get_soup(url)
    if not soup:
        return None

    try:
        # Titlu
        title = soup.find("h1", class_="product_title").get_text(strip=True)

        # SKU
        sku_tag = soup.find("span", class_="sku")
        sku = sku_tag.get_text(strip=True) if sku_tag else ""

        # Preturi
        regular_price = ""
        sale_price = ""

        # Preț redus (are <del> și <ins>)
        price_wrapper = soup.find("p", class_="price")
        if price_wrapper:
            del_tag = price_wrapper.find("del")
            ins_tag = price_wrapper.find("ins")

            if del_tag:
                regular_price = del_tag.get_text(strip=True)
            if ins_tag:
                sale_price = ins_tag.get_text(strip=True)

            # Dacă nu există <ins>, atunci produsul nu e redus → prețul actual e "regular"
            if not ins_tag:
                sale_price = regular_price
                regular_price = ""

        return {
            "title": title,
            "sku": sku,
            "regular_price": regular_price,
            "sale_price": sale_price,
            "url": url,
        }
    except Exception as e:
        print(f"Eroare la {url}: {e}")
        return None

def main():
    print("=== Încep scanarea site-ului prin sitemap ===")
    all_links = get_sitemap_links()

    # Selectează batch-ul
    batch_links = all_links[START_INDEX:END_INDEX]
    print(f"📦 Procesez produsele {START_INDEX+1} → {END_INDEX}")

    produse = []

    for idx, link in enumerate(batch_links, start=1):
        print(f"[{idx}/{len(batch_links)}] {link}")
        data = scrape_product(link)
        if data:
            produse.append(data)

        # Delay între cereri
        time.sleep(random.uniform(6, 8))

    # Salvare XLSX
    file_suffix = f"{START_INDEX+1}_{END_INDEX}"
    file_name = f"produse_{file_suffix}.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.append(["Denumire produs", "Cod produs (SKU)", "Preț inițial", "Preț curent", "Link"])

    for p in produse:
        ws.append([p["title"], p["sku"], p["regular_price"], p["sale_price"], p["url"]])

    wb.save(file_name)
    print(f"📊 Datele au fost salvate în {file_name}")

if __name__ == "__main__":
    main()

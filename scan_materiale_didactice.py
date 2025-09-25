import requests
from bs4 import BeautifulSoup
import time
import os
import openpyxl

# ================== CONFIG ==================
BASE_URL = "https://materialedidactice.ro"
SITEMAP_URL = f"{BASE_URL}/sitemap_index.xml"

# Citește batch range din variabilele de mediu
START_INDEX = int(os.getenv("START_INDEX", 0))
END_INDEX = int(os.getenv("END_INDEX", 100))

# Delay între cereri (ca să nu blocheze serverul)
REQUEST_DELAY = 5

# Telegram
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
# ============================================

def send_telegram_message(msg: str):
    """Trimite mesaj pe Telegram."""
    if not TG_TOKEN or not TG_CHAT_ID:
        print("⚠️ Lipsesc credențiale Telegram, nu trimit mesaj.")
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg})
    except Exception as e:
        print(f"⚠️ Eroare Telegram: {e}")

def get_soup(url: str):
    """Ia conținut HTML și returnează BeautifulSoup sau None dacă eșuează."""
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")
    except Exception as e:
        print(f"Eroare acces {url}: {e}")
        return None

def parse_sitemap(url: str):
    """Returnează toate linkurile dintr-un sitemap XML."""
    soup = get_soup(url)
    if not soup:
        return []
    return [loc.get_text() for loc in soup.find_all("loc")]

def get_all_product_links():
    """Adună toate linkurile din sitemap-urile de produse."""
    print(f"📥 Descarc sitemap principal: {SITEMAP_URL}")
    main_soup = get_soup(SITEMAP_URL)
    if not main_soup:
        return []
    links = []
    for loc in main_soup.find_all("loc"):
        sub_url = loc.get_text()
        if "product-sitemap" in sub_url:
            print(f"   ↳ verific {sub_url}")
            links.extend(parse_sitemap(sub_url))
    return links

def extract_product_info(url: str):
    """Extrage titlul și SKU-ul produsului dintr-o pagină."""
    soup = get_soup(url)
    if not soup:
        return None, None

    # Titlu
    title_tag = soup.find("h1", class_="product_title")
    title = title_tag.get_text(strip=True) if title_tag else "Fără titlu"

    # SKU
    sku_tag = soup.find("span", class_="sku")
    sku = sku_tag.get_text(strip=True) if sku_tag else "N/A"

    return title, sku

def main():
    print("=== Încep scanarea site-ului prin sitemap ===")
    product_links = get_all_product_links()
    print(f"✅ Am găsit {len(product_links)} linkuri în sitemap.")

    # Limitează la batch-ul curent
    batch_links = product_links[START_INDEX:END_INDEX]

    # Excel all products
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Produse"
    ws.append(["Titlu", "Cod produs (SKU)", "Link"])

    # Excel new products (pentru test păstrăm aceeași structură)
    wb_nou = openpyxl.Workbook()
    ws_nou = wb_nou.active
    ws_nou.title = "Produse Noi"
    ws_nou.append(["Titlu", "Cod produs (SKU)", "Link"])

    for idx, url in enumerate(batch_links, start=START_INDEX + 1):
        print(f"➡️ Cer {url}")
        title, sku = extract_product_info(url)
        if title:
            print(f"[{idx}/{END_INDEX}] {title} (SKU: {sku})")
            ws.append([title, sku, url])
            ws_nou.append([title, sku, url])
        else:
            print(f"[{idx}/{END_INDEX}] ❌ Nu am găsit informații")

        time.sleep(REQUEST_DELAY)

    # Salvare fișiere batch
    file_suffix = f"{START_INDEX+1}_{END_INDEX}"
    produse_file = f"produse_{file_suffix}.xlsx"
    produse_noi_file = f"produse_noi_{file_suffix}.xlsx"

    wb.save(produse_file)
    wb_nou.save(produse_noi_file)

    print(f"📊 Datele au fost salvate în {produse_file} și {produse_noi_file}")

    send_telegram_message(
        f"✅ Batch {file_suffix} finalizat.\n"
        f"Produse procesate: {len(batch_links)}"
    )

if __name__ == "__main__":
    main()

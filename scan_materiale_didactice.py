import os
import time
import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
import xml.etree.ElementTree as ET

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
HEADERS = {"User-Agent": "Mozilla/5.0"}

SITEMAP_URL = "https://materialedidactice.ro/sitemap_index.xml"

# ================= HELPER FUNCTIONS =================

def send_telegram_message(msg: str):
    """Trimite alertă pe Telegram"""
    if not TG_TOKEN or not TG_CHAT_ID:
        print("⚠️ TG_TOKEN sau TG_CHAT_ID lipsesc.")
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg})
        print("✅ Alertă trimisă pe Telegram")
    except Exception as e:
        print(f"❌ Eroare la trimiterea alertei: {e}")


def get_soup(url):
    """Returnează BeautifulSoup pentru o pagină"""
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")


def get_sitemap_links():
    """Citește sitemap_index și returnează linkurile din product-sitemap"""
    print(f"📥 Descarc sitemap principal: {SITEMAP_URL}")
    r = requests.get(SITEMAP_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    links = []
    for loc in root.findall("ns:sitemap/ns:loc", ns):
        url = loc.text.strip()
        if "product-sitemap" in url:
            print(f"   ↳ verific {url}")
            r2 = requests.get(url, headers=HEADERS, timeout=20)
            r2.raise_for_status()
            subroot = ET.fromstring(r2.content)
            for u in subroot.findall("ns:url/ns:loc", ns):
                links.append(u.text.strip())
    return links


def parse_product(url):
    """Extrage datele unui produs, inclusiv codul SKU"""
    # sărim peste fișiere media
    if any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".webp"]):
        raise ValueError("Link media, nu produs")

    soup = get_soup(url)
    title_tag = soup.select_one("h1.product_title")
    if not title_tag:
        raise ValueError("Nu e pagină de produs")

    title = title_tag.get_text(strip=True)

    # Cod produs (SKU)
    sku_elem = soup.select_one("span.sku")
    cod = sku_elem.get_text(strip=True) if sku_elem else ""

    # Prețuri
    pret_initial, pret_curent = "", ""
    price_block = soup.select_one("p.price")
    if price_block:
        ins = price_block.select_one("ins .woocommerce-Price-amount")
        del_tag = price_block.select_one("del .woocommerce-Price-amount")
        if ins:
            pret_curent = ins.get_text(" ", strip=True)
        else:
            span = price_block.select_one(".woocommerce-Price-amount")
            pret_curent = span.get_text(" ", strip=True) if span else ""
        if del_tag:
            pret_initial = del_tag.get_text(" ", strip=True)

    # Descriere
    descriere = ""
    desc_block = soup.select_one("#tab-description")
    if desc_block:
        descriere = desc_block.get_text(" ", strip=True)

    return {
        "Denumire": title,
        "Cod produs": cod,
        "Preț inițial": pret_initial,
        "Preț curent": pret_curent,
        "Descriere": descriere,
        "URL": url
    }


def save_to_excel(data, filename):
    """Salvează datele într-un fișier Excel"""
    wb = Workbook()
    ws = wb.active
    ws.append(["Denumire", "Cod produs", "Preț inițial", "Preț curent", "Descriere", "URL"])
    for row in data:
        ws.append([
            row.get("Denumire", ""),
            row.get("Cod produs", ""),
            row.get("Preț inițial", ""),
            row.get("Preț curent", ""),
            row.get("Descriere", ""),
            row.get("URL", "")
        ])
    wb.save(filename)
    print(f"📊 Datele au fost salvate în {filename}")


# ================= MAIN =================

def main():
    print("=== Încep scanarea site-ului prin sitemap ===")
    links = get_sitemap_links()
    print(f"✅ Am găsit {len(links)} linkuri în sitemap.")

    produse = []
    for i, url in enumerate(links, 1):
        print(f"➡️ Cer {url}")
        try:
            produs = parse_product(url)
            produse.append(produs)
            print(f"[{i}/{len(links)}] {produs['Denumire']} (SKU: {produs['Cod produs']})")
        except Exception as e:
            print(f"Eroare la {url}: {e}")

        # delay pentru siguranță
        time.sleep(5)

        # salvare parțială la fiecare 1000 produse
        if i % 1000 == 0:
            fname = f"produse_partial_{i}.xlsx"
            save_to_excel(produse, fname)
            print(f"💾 Salvare parțială la {i} produse.")

    # salvăm fișierele finale
    save_to_excel(produse, "produse.xlsx")
    save_to_excel(produse, "produse_noi.xlsx")

    send_telegram_message("✅ Scanare completă. Produse procesate: %d" % len(produse))


if __name__ == "__main__":
    main()

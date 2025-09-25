#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import random
import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook, load_workbook
import xml.etree.ElementTree as ET

BASE_URL = "https://materialedidactice.ro"
SITEMAP_URL = f"{BASE_URL}/sitemap_index.xml"
OUTPUT_FILE = "produse.xlsx"
NEW_FILE = "produse_noi.xlsx"
MAX_LINKS = 100  # ⬅️ limita pentru test

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; SiteMonitor/1.0)"
}

# ---------------- ALERTA TELEGRAM -----------------
def send_telegram_alert(message: str):
    tg_token = os.getenv("TG_TOKEN")
    tg_chat_id = os.getenv("TG_CHAT_ID")

    if not (tg_token and tg_chat_id):
        print("⚠️ Lipsesc variabilele TG_TOKEN sau TG_CHAT_ID.", flush=True)
        return

    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    r = requests.post(url, data={"chat_id": tg_chat_id, "text": message})
    if r.status_code == 200:
        print("✅ Alertă trimisă pe Telegram", flush=True)
    else:
        print("⚠️ Eroare la trimiterea alertei Telegram:", r.text, flush=True)

# ---------------- HELPERI -----------------
def get_soup(url):
    print(f"➡️ Cer {url}", flush=True)
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def get_sitemap_links(url):
    """Returnează toate linkurile dintr-un sitemap XML"""
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    tree = ET.fromstring(r.text)
    links = [el.text for el in tree.iter() if el.tag.endswith("loc")]
    return links

def get_all_product_links():
    """Parcurge sitemap-urile de produse și ia linkurile produselor"""
    product_links = []
    print(f"📥 Descarc sitemap principal: {SITEMAP_URL}", flush=True)
    submaps = get_sitemap_links(SITEMAP_URL)

    for sm in submaps:
        if "product-sitemap" in sm and "product_cat" not in sm:
            print(f"   ↳ verific {sm}", flush=True)
            product_links.extend(get_sitemap_links(sm))

    print(f"✅ Am găsit {len(product_links)} linkuri în sitemap.", flush=True)

    # limităm la MAX_LINKS pentru test
    return product_links[:MAX_LINKS]

def parse_product(url):
    """Extrage datele unui produs, ignoră linkurile non-produse"""
    if any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".pdf"]):
        raise ValueError("Link media, nu produs")

    soup = get_soup(url)
    title_tag = soup.select_one("h1.product_title")
    if not title_tag:
        raise ValueError("Nu e pagină de produs")

    title = title_tag.get_text(strip=True)

    cod_elem = soup.find(string=lambda t: t and "Cod produs:" in t)
    cod = cod_elem.strip().replace("Cod produs:", "").strip() if cod_elem else ""

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
    wb = Workbook()
    ws = wb.active
    ws.append(list(data[0].keys()))
    for row in data:
        ws.append(list(row.values()))
    wb.save(filename)

def load_existing_products(filename):
    if not os.path.exists(filename):
        return set()
    wb = load_workbook(filename)
    ws = wb.active
    codes = set()
    for row in ws.iter_rows(min_row=2, values_only=True):
        codes.add(row[1])  # coloana "Cod produs"
    return codes

# ---------------- MAIN -----------------
def main():
    print("=== Încep scanarea site-ului prin sitemap ===", flush=True)
    links = get_all_product_links()

    data = []
    for i, link in enumerate(links, 1):
        try:
            produs = parse_product(link)
            data.append(produs)
            print(f"[{i}/{len(links)}] {produs['Denumire']}", flush=True)
        except Exception as e:
            print(f"Eroare la {link}: {e}", flush=True)

        time.sleep(random.uniform(4, 6))

    if data:
        save_to_excel(data, OUTPUT_FILE)
        print(f"📊 Datele au fost salvate în {OUTPUT_FILE}", flush=True)

        existente = load_existing_products(OUTPUT_FILE)
        noi = [p for p in data if p["Cod produs"] not in existente]

        if noi:
            save_to_excel(noi, NEW_FILE)
            msg = f"🚨 Au apărut {len(noi)} produse noi pe {BASE_URL}!\nVezi fișierul {NEW_FILE} în repo."
            send_telegram_alert(msg)
        else:
            print("ℹ️ Nu există produse noi față de ultima scanare.", flush=True)

if __name__ == "__main__":
    main()

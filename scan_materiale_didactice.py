def get_all_product_links():
    """Parcurge sitemap-urile de produse și ia linkurile produselor"""
    product_links = []
    print(f"📥 Descarc sitemap principal: {SITEMAP_URL}")
    submaps = get_sitemap_links(SITEMAP_URL)

    for sm in submaps:
        # luăm doar sitemap-urile care încep cu product-sitemap, nu product_cat
        if "product-sitemap" in sm and "product_cat" not in sm:
            print(f"   ↳ verific {sm}")
            product_links.extend(get_sitemap_links(sm))

    print(f"✅ Am găsit {len(product_links)} produse în sitemap.")
    return product_links

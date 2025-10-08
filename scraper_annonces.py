import time
from bs4 import BeautifulSoup
import pandas as pd
import requests
import os

# Dossier data
os.makedirs("data", exist_ok=True)

liens = []
pages = 3  # Nombre de pages à scraper

for i in range(1, pages + 1):
    url = f"https://www.etreproprio.com/annonces/tf.odd.g{i}#list"
    page = requests.get(url)
    print(f"Scraping page {i}: {url}")

    soup = BeautifulSoup(page.content, "html.parser")

    annonces = soup.find("div", class_="ep-search-list-wrapper").find_all("a")
    for a in annonces:
        href = a.get("href")
        if not href:
            continue

        # ✅ On garde uniquement les liens valides
        if "https://www.etreproprio.com/immobilier-" in href.lower():

            # 🚫 On exclut les liens contenant "immeuble-de-rapport"
            if "immeuble-de-rapport" in href.lower():
                print(f"   → Lien ignoré (immeuble de rapport) : {href}")
                continue

            liens.append(href)

print(f"👉 {len(liens)} annonces collectées après filtrage")

# Extraire détails pour chaque annonce
data = []
for link in liens:
    page_ = requests.get(link)
    soup_page = BeautifulSoup(page_.content, "html.parser")

    # Price
    try:
        prix = soup_page.find("div", class_="ep-price").text.strip().replace(" ", "")
    except:
        prix = None

    #Surface
    try:
        m2 = soup_page.find("div", class_="ep-area").text.strip()
    except:
        m2 = None

    #Chambre
    try:
        chambres = soup_page.find("div", class_="ep-room").text.strip()
    except:
        chambres = None

    #DPE
    try:
        dpe_div = soup_page.select_one("div.dpe-letter.selected")
        DPE = dpe_div.get_text(strip=True) if dpe_div else None
    except:
        DPE = None
        
    #GES
    try:
        ges_div = soup_page.select_one("div.ges-letter.selected")
        GES = ges_div.get_text(strip=True) if ges_div else None
    except:
        GES = None

    #Lieux
    try:
        lieu = soup_page.find("div", class_="ep-loc").text.strip()
    except:
        lieu = None
    
    # Chopper l'image
    try:
        ref = soup_page.find("img", class_="horizontal-img")
        # Only get the first image
        Image = ref['src'] if ref and 'src' in ref.attrs else None
    except:
        Image = None

    # Terrasse ou balcon
    try:
        ref = soup_page.find("div", class_="ep-desc ep-a ep-desc-truncated")
        if ref.find(string=lambda text: "Terrasse" in text):
            Exterieur = "Terrasse"
        # Or balcon
        if not Exterieur:
            if ref.find(string=lambda text: "Balcon" in text):
                Exterieur = "Balcon"
    except:
        Exterieur = None

    # Stationnement
    Stationnement = None
    try:
        ref = soup_page.find("div", class_="ep-desc ep-a ep-desc-truncated")
        if ref:
            text = ref.get_text()
            if "Stationnement" in text:
                Stationnement = "Stationnement"
            elif "Parking" in text:
                Stationnement = "Parking"
            elif "Garage" in text:
                Stationnement = "Garage"
    except:
        Stationnement = None

    # Référence
    try:
        ref = soup_page.find("div", class_="ep-desc ep-generated ep-a")
        if ref:
            br = ref.find("br")
            if br and br.next_sibling:
                text = br.next_sibling.strip()
                if text.startswith("Référence:"):
                    Référence = text
                else:
                    Référence = None
            else:
                Référence = None
        else:
            Référence = None
    except:
        Référence = None
        
    data.append({
        "link": link,
        "price": prix,
        "surface": m2,
        "rooms": chambres,
        "DPE": DPE,
        "GES": GES,
        "location": lieu,
        "reference": Référence,
        "exterieur": Exterieur,
        "stationnement": Stationnement,
        "image": Image
    })


# Sauvegarde CSV
df = pd.DataFrame(data)
df.to_csv("data/raw_data.csv", index=False, encoding="utf-8-sig")
print("✅ Scraping terminé : data/raw_data.csv créé")
import pandas as pd
import re
import os
import requests
import time
from functools import lru_cache
from scraper_wiki import get_ville_infos
from tqdm import tqdm

# Dossier data
raw_file = "data/raw_data.csv"
clean_file = "data/cleaned_data.csv"

# Vérifie si le fichier existe
if not os.path.exists(raw_file):
    raise FileNotFoundError(f"❌ Le fichier {raw_file} est introuvable. Lance d'abord scraper.py")

df = pd.read_csv(raw_file)
print(f"📊 Lignes brutes importées : {len(df)}")

# --- Nettoyage prix ---
if "price" in df.columns:
    df["price"] = (
        df["price"].astype(str)
        .str.replace("€", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace("\xa0", "", regex=False)
        .str.strip()
    )
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

# --- Nettoyage surface ---
if "surface" in df.columns:
    df["surface"] = (
        df["surface"].astype(str)
        .str.replace("m²", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace("\xa0", "", regex=False)
        .str.strip()
    )
    df["surface"] = pd.to_numeric(df["surface"], errors="coerce")

# --- Nettoyage rooms ---
def extract_rooms(val):
    if pd.isna(val):
        return None
    text = str(val).lower()
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None

if "rooms" in df.columns:
    df["rooms"] = df["rooms"].apply(extract_rooms)

# --- Séparation code postal et ville ---
def extract_postal_and_city(text):
    if pd.isna(text):
        return pd.Series([None, None])
    s = str(text).strip()
    m = re.search(r"(\d{5})", s)
    if not m:
        cleaned = re.sub(r'[\(\)\[\]\-–—_:,\/]', ' ', s).replace('\xa0', ' ')
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return pd.Series([None, cleaned if cleaned else None])
    postal = m.group(1)
    city = re.sub(re.escape(postal), '', s)
    city = re.sub(r'[\(\)\[\]\-–—_:,\/]', ' ', city).replace('\xa0', ' ')
    city = re.sub(r'\s+', ' ', city).strip()
    if city == "":
        city = None
    return pd.Series([postal, city])

if "location" in df.columns:
    df[["postal_code", "city"]] = df["location"].apply(lambda x: extract_postal_and_city(x))

# --- Infos villes via Wikipedia ---

def enrich_city_infos(city):
    if not city or pd.isna(city):
        return pd.Series([None, None, None, None])
    try:
        infos = get_ville_infos(city)
        # Petite pause pour ne pas surcharger Wikipédia
        time.sleep(0.1)
        return pd.Series([
            infos.get("population"),
            infos.get("superficie"),
            infos.get("densité"),
            infos.get("infos")
        ])
    except Exception as e:
        print(f"⚠️ Erreur récupération Wikipédia pour {city}: {e}")
        return pd.Series([None, None, None, None])

# Ajout des colonnes
tqdm.pandas(desc="Enrichissement villes Wikipédia")
df[["Population", "Superficie", "Densité", "Infos_ville"]] = df["city"].progress_apply(enrich_city_infos)


# --- Géocodage (lat, lon) ---
@lru_cache(maxsize=1000)
def get_lat_lon(postal_code, city):
    try:
        if pd.isna(postal_code) or pd.isna(city):
            return None, None
        url = f"https://api-adresse.data.gouv.fr/search/?q={city}&postcode={postal_code}&limit=1"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data["features"]:
                coords = data["features"][0]["geometry"]["coordinates"]
                return coords[1], coords[0]
    except Exception as e:
        print(f"Erreur géocodage : {e}")
    return None, None

if {"postal_code", "city"}.issubset(df.columns):
    lats, lons = [], []
    for idx, row in df.iterrows():
        lat, lon = get_lat_lon(row["postal_code"], row["city"])
        lats.append(lat)
        lons.append(lon)
    df["latitude"] = lats
    df["longitude"] = lons

# --- Ajout prix/m² ---
if "price" in df.columns and "surface" in df.columns:
    df["price_per_m2"] = df["price"] / df["surface"]

# --- Indicateur de complétude ---
required_fields = ["price", "surface", "rooms", "reference", "DPE", "GES"]
df["is_complete"] = df[required_fields].notna().all(axis=1)

# --- Nettoyage minimal (garde les annonces exploitables) ---
df.dropna(subset=["price", "surface", "rooms"], inplace=True)

# Sauvegarde finale
df.to_csv(clean_file, index=False, encoding="utf-8-sig")
print(f"✅ Nettoyage terminé : {clean_file} créé ({len(df)} lignes après nettoyage)")
print(f"ℹ️ Annonces complètes : {df['is_complete'].sum()} / {len(df)}")
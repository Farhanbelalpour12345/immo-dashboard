import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import time
from functools import lru_cache

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0 Safari/537.36",
    "Referer": "https://www.google.com/"
}

def _empty_scores():
    return {
        "🌿 Environnement": None,
        "🚦 Transports": None,
        "🛡️ Sécurité": None,
        "🩺 Santé": None,
        "⚽ Sports & loisirs": None,
        "🎨 Culture": None,
        "📚 Enseignement": None,
        "🛒 Commerces": None,
        "❤️ Qualité de vie": None,
    }

@lru_cache(maxsize=None)
def get_ville_ideale_scores(ville):
    """Scrape les notes de Ville Idéale pour une ville donnée."""
    base_url = "https://www.ville-ideale.fr"
    search_url = f"{base_url}/recherche.php?query={quote(ville)}"

    try:
        r = requests.get(search_url, headers=HEADERS, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Erreur de recherche pour {ville}: {e}")
        return _empty_scores()

    soup = BeautifulSoup(r.text, "html.parser")
    link = soup.select_one("a[href*='_']")

    if not link:
        print(f"⚠️ Ville non trouvée sur Ville Idéale : {ville}")
        return _empty_scores()

    ville_url = base_url + "/" + link["href"].lstrip("/")
    time.sleep(1)

    try:
        r = requests.get(ville_url, headers=HEADERS, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Erreur chargement page {ville}: {e}")
        return _empty_scores()

    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table", {"id": "tablonotes"})
    if not table:
        print(f"⚠️ Pas de tableau trouvé pour {ville}")
        return _empty_scores()

    mapping = {
        "Environnement": "🌿 Environnement",
        "Transports": "🚦 Transports",
        "Sécurité": "🛡️ Sécurité",
        "Santé": "🩺 Santé",
        "Sports et loisirs": "⚽ Sports & loisirs",
        "Culture": "🎨 Culture",
        "Enseignement": "📚 Enseignement",
        "Commerces": "🛒 Commerces",
        "Qualité de vie": "❤️ Qualité de vie",
    }

    scores = _empty_scores()
    for tr in table.find_all("tr"):
        th = tr.find("th")
        td = tr.find("td")
        if not th or not td:
            continue
        critere = th.get_text(strip=True)
        note_txt = td.get_text(strip=True).replace(",", ".")
        try:
            note = float(note_txt)
        except ValueError:
            note = None

        for key, emoji_key in mapping.items():
            if key.lower() in critere.lower():
                scores[emoji_key] = note

    return scores

# === Exemple d’utilisation ===
if __name__ == "__main__":
    villes = ["Bordeaux", "Toulouse", "La Rochelle"]
    for v in villes:
        print(f"\n🏙️ {v}")
        print(get_ville_ideale_scores(v))

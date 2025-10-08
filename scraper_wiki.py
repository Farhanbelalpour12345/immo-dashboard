import requests
from bs4 import BeautifulSoup
import re
from functools import lru_cache
from urllib.parse import quote

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CityScraper/1.5; +https://example.com)"
}

@lru_cache(maxsize=None)
def get_ville_infos(nom_ville):
    """Récupère les infos principales d'une ville sur Wikipédia (français)."""

    # 🧹 1. Nettoyage du nom : enlever arrondissement / chiffres / suffixes "e", "ème", etc.
    ville_clean = (
        str(nom_ville)
        .strip()
        .title()
        .replace("Arrondissement", "")
        .replace("Arrond.", "")
        .replace("Arrond", "")
        .replace("ᵉᵐᵉ", "")
        .replace("ᵉ", "")
        .replace("Eme", "")
        .replace("Ème", "")
        .replace("Er", "")
    )

    # Supprimer chiffres et suffixes type "e", "ᵉ", "eme" qui suivent un chiffre
    ville_clean = re.sub(r"\d+\s*(?:er|eme|ème|e)?", "", ville_clean, flags=re.IGNORECASE).strip()

    nom_enc = quote(ville_clean.replace(" ", "_"))
    url = f"https://fr.wikipedia.org/wiki/{nom_enc}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Page Wikipedia non trouvée pour {nom_ville} (tentative avec {ville_clean})")
            return _empty_ville(nom_ville)
    except Exception as e:
        print(f"❌ Erreur lors de la requête pour {nom_ville}: {e}")
        return _empty_ville(nom_ville)

    soup = BeautifulSoup(response.text, "html.parser")

    infobox = soup.find("table", {"class": "infobox"})
    population = superficie = densite = None

    if infobox:
        text = infobox.get_text(" ", strip=True).lower()
        text = text.replace("\xa0", " ").replace(",", ".").replace("  ", " ")

        pop_match = re.search(r"population[^\d]*([\d\s]{4,})", text)
        sup_match = re.search(r"superficie[^\d]*([\d\.]+)", text)
        den_match = re.search(r"densité[^\d]*([\d\s\.]+)", text)

        if pop_match:
            population = f"{_clean_number(pop_match.group(1))} hab."
        if sup_match:
            superficie = f"{_clean_number(sup_match.group(1))} km²"
        if den_match:
            densite = f"{_clean_number(den_match.group(1))} hab/km²"

    # 🔹 Court résumé (nettoyé + suppression prononciation)
    resume = ""
    for p in soup.select("p"):
        txt = p.get_text(" ", strip=True)
        if len(txt) > 100 and not txt.startswith("Cet article"):
            resume = _clean_resume(txt)
            break

    if not resume:
        resume = "ℹ️ Aucune information disponible."

    return {
        "ville": nom_ville,
        "population": population,
        "superficie": superficie,
        "densité": densite,
        "infos": resume,
    }


def _clean_number(s):
    """Nettoie un nombre : supprime espaces et caractères parasites."""
    return s.replace("\xa0", "").replace(" ", "").replace(".", ",")


def _clean_resume(txt):
    """Nettoie le paragraphe Wikipédia pour un texte lisible."""
    # Enlever les références [1], [ 1 ], etc.
    txt = re.sub(r"\[\s*\d+\s*\]", "", txt)
    # Enlever les prononciations ou phonétiques
    txt = re.sub(r"\[.*?\]", "", txt)
    txt = re.sub(r"\(.*?prononc[ée]?\s.*?\)", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\(.*?pronon[çc]er.*?\)", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"prononc[ée]?\s.*?(,|—|-)", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"—\s*", "", txt)
    txt = re.sub(r"/.*?/", "", txt)
    txt = re.sub(r"Écouter", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"ⓘ", "", txt)
    txt = re.sub(r"\s*\[a\]\s*", "", txt)

    # 🔹 Supprimer les parenthèses vides (comme "( )")
    txt = re.sub(r"\(\s*\)", "", txt)

    # 🔹 Corriger doublons de mots ("est est", "la la", etc.)
    txt = re.sub(r"\b(\w+)\s+\1\b", r"\1", txt, flags=re.IGNORECASE)

    # Corriger les collages de mots
    txt = re.sub(r"([a-zéèêëàâîïôöûüç])([A-ZÉÈÊËÀÂÎÏÔÖÛÜÇ])", r"\1 \2", txt)
    txt = txt.replace("Villede", "Ville de ")
    txt = txt.replace("Franceainsi", "France ainsi ")
    txt = txt.replace("lacapitale", "la capitale ")
    txt = txt.replace("unecollectivité", "une collectivité ")
    txt = txt.replace("vingtarrondissements", "vingt arrondissements ")

    # Espaces et ponctuation
    txt = re.sub(r"\s+([,.;!?])", r"\1", txt)
    txt = re.sub(r"\s+", " ", txt).strip()

    # Tronquer à 2 phrases max
    sentences = re.split(r"(?<=[.!?]) +", txt)
    return " ".join(sentences[:2]).strip()


def _empty_ville(nom_ville):
    return {
        "ville": nom_ville,
        "population": None,
        "superficie": None,
        "densité": None,
        "infos": "ℹ️ Aucune information disponible.",
    }


if __name__ == "__main__":
    print(get_ville_infos("Paris 15e arrondissement"))
    print(get_ville_infos("Marseille 3e"))
    print(get_ville_infos("Montpellier"))
    print(get_ville_infos("Lyon 7eme"))
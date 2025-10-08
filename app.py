import re
import io
import streamlit as st
import pandas as pd
import pydeck as pdk
import altair as alt
import requests
import subprocess
import time
import os
from datetime import datetime

@st.cache_data
def load_data():
    """Charge le CSV nettoyé (avec cache Streamlit)"""
    return pd.read_csv("data/cleaned_data.csv")

st.set_page_config(page_title="Tableau de bord Streamlit", layout="wide")
st.title("📊 Tableau de bord des annonces immobilières")

# --- Bouton de mise à jour ---
st.sidebar.markdown("### ⚙️ Actualisation des données")

if st.sidebar.button("🔄 Actualiser les données"):
    with st.spinner("Scraping et nettoyage en cours... ⏳"):
        try:
            subprocess.run(["python", "scripts/scraper_annonces.py"], check=True)
            subprocess.run(["python", "scripts/scraper_ville_ideale.py"], check=True)  # ← اضافه شد
            subprocess.run(["python", "scripts/cleaner.py"], check=True)
            st.success("✅ Données mises à jour avec succès !")
        except Exception as e:
            st.error(f"❌ Erreur lors de la mise à jour : {e}")
        time.sleep(1)
        st.cache_data.clear()

# --- Chargement des données ---
df = load_data()

# st.header("🏙️ Notes de qualité de vie (Ville Idéale)")

# try:
#     df_villes = pd.read_csv("data/villes_scores.csv")
#     st.dataframe(df_villes, use_container_width=True)
# except FileNotFoundError:
#     st.warning("⚠️ Les données Ville Idéale ne sont pas encore disponibles. Cliquez sur Actualiser pour les générer.")


try:
    ts = os.path.getmtime("data/cleaned_data.csv")
    date_update = datetime.fromtimestamp(ts).strftime("%d/%m/%Y à %H:%M")
    st.sidebar.info(f"🕒 Dernière mise à jour : {date_update}")
except:
    st.sidebar.warning("⚠️ Aucune donnée disponible pour le moment.")



# 1. Charger les données
df = pd.read_csv("data/cleaned_data.csv")

# ---- Aperçu des données (head) ----
st.write("Aperçu des données :")
st.data_editor(
    df.head(),
    use_container_width=True,
    column_config={
        "latitude": None,
        "longitude": None,
        "postal_code": None,
        "city": None,
        "is_complete": None,
        "exterieur": None,
        "stationnement": None,
        "image": st.column_config.ImageColumn("Aperçu", width=200),
    },
    row_height=50,
    disabled=True
)

# 2. Filtres interactifs
st.sidebar.header("🔍 Filtres")

def safe_slider(label, series, unit=""):
    """Crée un slider Streamlit si plusieurs valeurs existent, sinon affiche la valeur unique."""
    if series.dropna().empty:
        st.sidebar.write(f"Aucune donnée pour {label}")
        return (None, None)

    min_val = int(series.min())
    max_val = int(series.max())

    if min_val == max_val:
        # st.sidebar.write(f"{label} unique : {min_val}{unit}")
        return (min_val, max_val)
    else:
        return st.sidebar.slider(label, min_val, max_val, (min_val, max_val))


# --- Ville ---
if "city" in df.columns:
    villes = sorted(df["city"].dropna().unique())

    paris_arr = [v for v in villes if v.startswith("Paris")]
    autres_villes = [v for v in villes if not v.startswith("Paris")]

    options_villes = ["Toutes"] + ["Paris"] + autres_villes
    ville_selectionnee = st.sidebar.selectbox("Ville 🏙️", options=options_villes)

    if ville_selectionnee == "Toutes":
        pass
    elif ville_selectionnee == "Paris":
        arr_opt = ["Tous arrondissements"] + paris_arr
        arr_selection = st.sidebar.selectbox("Arrondissement", options=arr_opt)
        if arr_selection != "Tous arrondissements":
            df = df[df["city"] == arr_selection]
        else:
            df = df[df["city"].isin(paris_arr)]
    else:
        df = df[df["city"] == ville_selectionnee]
else:
    ville_selectionnee = None

# --- Filtre Prix ---
if "price" in df.columns:
    prix_range = safe_slider("Prix 💶", df["price"], " €")
    if prix_range[0] is not None:
        df = df[(df["price"] >= prix_range[0]) & (df["price"] <= prix_range[1])]

# --- Filtre Surface ---
if "surface" in df.columns:
    surface_range = safe_slider("Surface 📐(m²)", df["surface"], " m²")
    if surface_range[0] is not None:
        df = df[(df["surface"] >= surface_range[0]) & (df["surface"] <= surface_range[1])]

# --- Filtre Nombre de pièces ---
if "rooms" in df.columns:
    rooms_range = safe_slider("Nombre de pièces 🛏️", df["rooms"])
    if rooms_range[0] is not None:
        df = df[(df["rooms"] >= rooms_range[0]) & (df["rooms"] <= rooms_range[1])]
        
# --- Filtre DPE ---
if "DPE" in df.columns:
    dpe_options = sorted(df["DPE"].dropna().unique())
    dpe_selection = st.sidebar.multiselect("Classe DPE ♻️", options=dpe_options, default=[])
    if dpe_selection:
        df = df[df["DPE"].isin(dpe_selection)]

# --- Filtre GES ---
if "GES" in df.columns:
    ges_options = sorted(df["GES"].dropna().unique())
    ges_selection = st.sidebar.multiselect("Classe GES 🌱", options=ges_options, default=[])
    if ges_selection:
        df = df[df["GES"].isin(ges_selection)]

# --- Filtre Extérieur ---
if "exterieur" in df.columns:
    ext_options = sorted(df["exterieur"].dropna().unique())
    ext_selection = st.sidebar.multiselect("Type d'extérieur 🏘️", options=ext_options, default=[])
    if ext_selection:
        df = df[df["exterieur"].isin(ext_selection)]

# --- Filtre Stationnement ---
if "stationnement" in df.columns:
    park_options = sorted(df["stationnement"].dropna().unique())
    park_selection = st.sidebar.multiselect("Type de stationnement 🅿️", options=park_options, default=[])
    if park_selection:
        df = df[df["stationnement"].isin(park_selection)]

# 3. Onglets
tab1, tab2, tab3 = st.tabs(["📊 Statistiques", "🗺️ Carte", "🗃️ Données"])

with tab1:
    st.subheader("📈 Quelques données clés :")
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Prix moyen", f"{df['price'].mean():.0f} €" if not df.empty else "N/A")
    col2.metric("📐 Surface moyenne", f"{df['surface'].mean():.1f} m²" if not df.empty else "N/A")
    col3.metric("📌 Nombre d'annonces", f"{len(df)}")

    st.subheader("🌇 Informations sur la ville sélectionnée :")
    
    villes_selectionnees = df["city"].dropna().unique().tolist()

    # Afficher seulement si UNE seule ville est sélectionnée
    if len(villes_selectionnees) == 1:
        ville = villes_selectionnees[0]
        st.markdown(f"### 🏙️ {ville}")

        # Récupérer les infos wiki depuis le DF
        infos_ville = df[df["city"] == ville][["Population", "Superficie", "Densité", "Infos_ville"]].iloc[0]

        # Colonnes population / superficie / densité
        col4, col5, col6 = st.columns(3)
        col4.metric("👥 Population", infos_ville["Population"] if pd.notna(infos_ville["Population"]) else "N/A")
        col5.metric("📏 Superficie", infos_ville["Superficie"] if pd.notna(infos_ville["Superficie"]) else "N/A")
        col6.metric("🏙️ Densité", infos_ville["Densité"] if pd.notna(infos_ville["Densité"]) else "N/A")

        # Texte descriptif court
        st.markdown("---")
        st.markdown("**ℹ️ À propos de la ville :**")
        st.write(infos_ville["Infos_ville"] if pd.notna(infos_ville["Infos_ville"]) else "Aucune information disponible.")
    
    else:
        st.info("🗺️ Sélectionnez une seule ville pour afficher ses informations détaillées.")
 

    st.subheader("📋 Tableau de synthèse par ville")

    # Simulation de futures notes (exemple)
    df_summary = (
        df.groupby("city")
        .agg(
            prix_moyen=("price", "mean"),
            surface_moyenne=("surface", "mean"),
            nb_annonces=("reference", "count"),
            dpe_moyen=("DPE", lambda x: x.mode().iloc[0] if not x.mode().empty else None),
        )
        .reset_index()
    )

    # Placeholder pour les futures colonnes issues du scraper "ville"
    df_summary["🌿 Environnement"] = [None] * len(df_summary)
    df_summary["🚦 Transports"] = [None] * len(df_summary)
    df_summary["🛡️ Sécurité"] = [None] * len(df_summary)
    df_summary["🩺 Santé"] = [None] * len(df_summary)
    df_summary["⚽ Sports & loisirs"] = [None] * len(df_summary)
    df_summary["🎨 Culture"] = [None] * len(df_summary)
    df_summary["📚 Enseignement"] = [None] * len(df_summary)
    df_summary["🛒 Commerces"] = [None] * len(df_summary)
    df_summary["❤️ Qualité de vie"] = [None] * len(df_summary)

    st.dataframe(
        df_summary.style.format({
            "prix_moyen": "{:,.0f} €",
            "surface_moyenne": "{:.1f} m²",
        }),
        use_container_width=True,
        height=500,
    )


with tab2:
    st.subheader("📍 Carte interactive des annonces")

    if {"latitude", "longitude"}.issubset(df.columns) and not df.empty:
        df_map = df.dropna(subset=["latitude", "longitude"]).copy()
        df_map["price_per_m2_fmt"] = df_map["price_per_m2"].apply(lambda x: f"{x:.2f}")
        # Vérification qu'on a les colonnes nécessaires pour le tooltip
        for col in ["price", "surface", "price_per_m2", "DPE", "GES"]:
            if col not in df_map.columns:
                df_map[col] = None

        # Conversion des colonnes pour éviter les NaN dans le tooltip
        df_map["price"] = df_map["price"].fillna(0).astype(int)
        df_map["surface"] = df_map["surface"].fillna(0).astype(float)
        df_map["price_per_m2"] = df_map["price_per_m2"].fillna(0).astype(float)

        if df_map.empty:
            st.warning("⚠️ Aucune annonce à afficher avec les filtres actuels.")
        else:
            import pydeck as pdk

            layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_map,
                get_position=["longitude", "latitude"],
                get_color="[255, 140, 0, 180]",
                get_radius="price_per_m2 / 3 + 200",  # bulle lisible même à bas prix
                pickable=True,
            )

            view_state = pdk.ViewState(
                latitude=float(df_map["latitude"].mean()),
                longitude=float(df_map["longitude"].mean()),
                zoom=6 if len(df_map) > 5 else 9,
                pitch=0,
            )

            # 🧭 Fond de carte open-source (pas besoin de clé Mapbox)
            map_style = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"

            # ✅ Tooltip corrigé (affiche toutes les infos)
            tooltip = {
                "html": """
                    <b>{city}</b><br/>
                    💰 Prix : {price} €<br/>
                    📏 Surface : {surface} m²<br/>
                    💶 Prix/m² : {price_per_m2_fmt} €/m²<br/>
                    ⚡ DPE : {DPE}<br/>
                    🌿 GES : {GES}
                """,
                "style": {
                    "backgroundColor": "rgba(0, 0, 0, 0.75)",
                    "color": "white",
                    "fontSize": "12px",
                },
            }

            st.pydeck_chart(
                pdk.Deck(
                    map_style=map_style,
                    initial_view_state=view_state,
                    layers=[layer],
                    tooltip=tooltip,
                ),
                use_container_width=True,
            )
    else:
        st.warning("⚠️ Pas de colonnes de latitude/longitude dans les données.")
        

with tab3:
    st.subheader("📥 Télécharger les données filtrées")
    st.data_editor(
        df,
        use_container_width=True,
        column_config={
            "latitude": None,
            "longitude": None,
            "image": st.column_config.ImageColumn("Aperçu", width="small"),
        },
        disabled=True
    )

    st.download_button(
        "Télécharger CSV filtré",
        df.to_csv(index=False).encode("utf-8-sig"),
        "annonces_filtrees.csv",
        "text/csv",
        key="download-csv"
    )




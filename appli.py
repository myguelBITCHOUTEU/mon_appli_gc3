import streamlit as st
import pandas as pd
import plotly.express as px
import os
import threading
import time
import urllib.request
from datetime import date, datetime

# ==============================================================================
# 1. CONFIGURATION ET OPTIMISATION
# ==============================================================================
st.set_page_config(
    page_title="BTP EcoWaste Pro - Import & Performance",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

PLOT_CONFIG = {
    "displayModeBar": False,
    "responsive": True
}

DATA_FILE = "dechets_data.csv"
DATA_DIRECTORY = "data"
os.makedirs(DATA_DIRECTORY, exist_ok=True)

# ==============================================================================
# 2. MODULE ANTI-SOMMEIL CONSERVÉ
# ==============================================================================
APP_URL = os.getenv("STREAMLIT_APP_URL", "")


def background_keep_alive(target_url, interval_sec=600):
    """Effectue un ping HTTP toutes les 10 minutes."""
    while True:
        try:
            if target_url:
                req = urllib.request.Request(
                    target_url,
                    headers={"User-Agent": "Mozilla/5.0 KeepAlive-Bot"}
                )
                with urllib.request.urlopen(req, timeout=10):
                    pass
        except Exception:
            pass
        time.sleep(interval_sec)


if "keep_alive_started" not in st.session_state and APP_URL:
    keep_alive_thread = threading.Thread(
        target=background_keep_alive,
        args=(APP_URL, 600),
        daemon=True
    )
    keep_alive_thread.start()
    st.session_state["keep_alive_started"] = True

# ==============================================================================
# 3. REFERENTIELS BTP CONSERVÉS
# ==============================================================================
REFERENTIEL_MATERIAUX = {
    "Béton résiduel": {"prix": 75000, "unite": "m3", "co2_facteur": 240},
    "Chutes de fer / Acier": {"prix": 800, "unite": "kg", "co2_facteur": 1.8},
    "Bois de coffrage": {"prix": 2500, "unite": "Planche", "co2_facteur": 0.5},
    "Parpaings / Agglos cassés": {"prix": 500, "unite": "Unité (U)", "co2_facteur": 1.2},
    "Gravats / Remblais": {"prix": 10000, "unite": "Tonne", "co2_facteur": 15},
    "Plâtre / Chutes de placo": {"prix": 12000, "unite": "Tonne", "co2_facteur": 120},
    "Plastiques & Gainages": {"prix": 1500, "unite": "kg", "co2_facteur": 2.5},
    "Cartons & Emballages": {"prix": 300, "unite": "kg", "co2_facteur": 0.9},
    "Déchets Dangereux (Peintures/Huiles)": {"prix": 5000, "unite": "Litre", "co2_facteur": 3.0}
}

FILIERES_VALORISATION = [
    "Réemploi sur site",
    "Recyclage / Filière externe",
    "Revalorisation Énergétique",
    "Mise en Décharge / CET (Non Valorisé)"
]

CAUSES_FREQUENTES = [
    "Sur-commande / Surplus de stock",
    "Erreur de découpe / Mise en œuvre",
    "Casse à la manutention / Transport",
    "Intempéries / Stockage inadéquat",
    "Fin de péremption (Mortier/Ciment)",
    "Non-conformité / Défaut livraison"
]

CHANTIERS_DISPONIBLES = [
    "Chantier Tour Horizon (GC)",
    "Chantier Riviera",
    "Pont Autoroutier Est"
]

ZONES_CHANTIER = [
    "Zone A - Gros Œuvre",
    "Zone B - Second Œuvre",
    "Zone C - Base Vie / Stockage",
    "Voirie & Réseaux (VRD)"
]

COLONNES_ATTENDUES = [
    "Chantier", "Zone", "Date", "Type", "Quantite", "Unite",
    "Cout_Estime", "Filiere", "Cause", "CO2_Impact_kg"
]

# ==============================================================================
# 4. CHARGEMENT ET STOCKAGE CSV ORIGINAL CONSERVÉS
# ==============================================================================
@st.cache_data(show_spinner=False, ttl=3600)
def load_cached_data():
    """Charge les données existantes de l'application."""
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE, parse_dates=["Date"])
            for col in COLONNES_ATTENDUES:
                if col not in df.columns:
                    df[col] = None
            return df[COLONNES_ATTENDUES]
        except Exception:
            pass
    return pd.DataFrame(columns=COLONNES_ATTENDUES)


def save_and_invalidate_cache(df):
    """Sauvegarde les données dans le fichier CSV principal."""
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
    st.session_state.df = df
    load_cached_data.clear()


# ==============================================================================
# 5. AJOUT : NORMALISATION DES CSV
# ============================================================================
def normaliser_dataframe(df):
    """Complète les colonnes manquantes et calcule les valeurs nécessaires."""
    df = df.copy()

    for col in ["Chantier", "Zone", "Type"]:
        if col not in df.columns:
            df[col] = "Non spécifié"

    if "Date" not in df.columns:
        df["Date"] = pd.Timestamp.today().normalize()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Date"] = df["Date"].fillna(pd.Timestamp.today().normalize())

    if "Quantite" not in df.columns:
        df["Quantite"] = 0
    df["Quantite"] = pd.to_numeric(df["Quantite"], errors="coerce").fillna(0)

    if "Unite" not in df.columns:
        df["Unite"] = df["Type"].map(
            lambda x: REFERENTIEL_MATERIAUX.get(x, {}).get("unite", "U")
        )

    if "Cout_Estime" not in df.columns:
        df["Cout_Estime"] = df.apply(
            lambda row: row["Quantite"] * REFERENTIEL_MATERIAUX.get(
                row["Type"], {}
            ).get("prix", 0), axis=1
        )
    df["Cout_Estime"] = pd.to_numeric(
        df["Cout_Estime"], errors="coerce"
    ).fillna(0)

    if "CO2_Impact_kg" not in df.columns:
        df["CO2_Impact_kg"] = df.apply(
            lambda row: row["Quantite"] * REFERENTIEL_MATERIAUX.get(
                row["Type"], {}
            ).get("co2_facteur", 0), axis=1
        )
    df["CO2_Impact_kg"] = pd.to_numeric(
        df["CO2_Impact_kg"], errors="coerce"
    ).fillna(0)

    for col in ["Filiere", "Cause"]:
        if col not in df.columns:
            df[col] = "Non spécifié"
        df[col] = df[col].fillna("Non spécifié").astype(str)

    for col in ["Chantier", "Zone", "Type", "Unite"]:
        df[col] = df[col].fillna("Non spécifié").astype(str)

    return df[COLONNES_ATTENDUES]


def lire_fichier_csv(path):
    try:
        return normaliser_dataframe(pd.read_csv(path))
    except Exception:
        return pd.DataFrame(columns=COLONNES_ATTENDUES)


def liste_fichiers_csv():
    """Retourne le fichier historique et tous les fichiers du dossier data."""
    fichiers = []
    if os.path.exists(DATA_FILE):
        fichiers.append(DATA_FILE)
    if os.path.exists(DATA_DIRECTORY):
        fichiers.extend(
            os.path.join(DATA_DIRECTORY, file_name)
            for file_name in sorted(os.listdir(DATA_DIRECTORY))
            if file_name.lower().endswith(".csv")
        )
    return fichiers

# ==============================================================================
# 6. DONNÉES DE DÉMONSTRATION ORIGINALES CONSERVÉES
# ==============================================================================
def create_demo_data():
    """Crée un jeu de données réaliste pour tester le tableau de bord."""
    demo_rows = [
        {
            "Chantier": "Chantier Tour Horizon (GC)",
            "Zone": "Zone A - Gros Œuvre",
            "Date": pd.Timestamp("2026-01-15"),
            "Type": "Béton résiduel",
            "Quantite": 3.5,
            "Unite": "m3",
            "Cout_Estime": 262500,
            "Filiere": "Réemploi sur site",
            "Cause": "Sur-commande / Surplus de stock",
            "CO2_Impact_kg": 840
        },
        {
            "Chantier": "Chantier Riviera",
            "Zone": "Zone B - Second Œuvre",
            "Date": pd.Timestamp("2026-02-04"),
            "Type": "Bois de coffrage",
            "Quantite": 25,
            "Unite": "Planche",
            "Cout_Estime": 62500,
            "Filiere": "Recyclage / Filière externe",
            "Cause": "Erreur de découpe / Mise en œuvre",
            "CO2_Impact_kg": 12.5
        },
        {
            "Chantier": "Pont Autoroutier Est",
            "Zone": "Voirie & Réseaux (VRD)",
            "Date": pd.Timestamp("2026-03-12"),
            "Type": "Gravats / Remblais",
            "Quantite": 8,
            "Unite": "Tonne",
            "Cout_Estime": 80000,
            "Filiere": "Mise en Décharge / CET (Non Valorisé)",
            "Cause": "Casse à la manutention / Transport",
            "CO2_Impact_kg": 120
        },
        {
            "Chantier": "Chantier Tour Horizon (GC)",
            "Zone": "Zone C - Base Vie / Stockage",
            "Date": pd.Timestamp("2026-04-20"),
            "Type": "Cartons & Emballages",
            "Quantite": 120,
            "Unite": "kg",
            "Cout_Estime": 36000,
            "Filiere": "Recyclage / Filière externe",
            "Cause": "Sur-commande / Surplus de stock",
            "CO2_Impact_kg": 108
        },
        {
            "Chantier": "Chantier Riviera",
            "Zone": "Zone A - Gros Œuvre",
            "Date": pd.Timestamp("2026-05-08"),
            "Type": "Chutes de fer / Acier",
            "Quantite": 180,
            "Unite": "kg",
            "Cout_Estime": 144000,
            "Filiere": "Recyclage / Filière externe",
            "Cause": "Non-conformité / Défaut livraison",
            "CO2_Impact_kg": 324
        },
        {
            "Chantier": "Pont Autoroutier Est",
            "Zone": "Zone B - Second Œuvre",
            "Date": pd.Timestamp("2026-06-17"),
            "Type": "Plâtre / Chutes de placo",
            "Quantite": 2.4,
            "Unite": "Tonne",
            "Cout_Estime": 28800,
            "Filiere": "Mise en Décharge / CET (Non Valorisé)",
            "Cause": "Casse à la manutention / Transport",
            "CO2_Impact_kg": 288
        }
    ]
    return pd.DataFrame(demo_rows, columns=COLONNES_ATTENDUES)


if "df" not in st.session_state:
    st.session_state.df = load_cached_data()

if "source_file" not in st.session_state:
    st.session_state.source_file = DATA_FILE

# ==============================================================================
# 7. INTERFACE VISUELLE AMÉLIORÉE : ENTITÉS HTML CORRIGÉES
# ==============================================================================
st.markdown(
    """
    <style>
        .stApp { background: #f8fafc; }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px; }
        .title-banner {
            background: linear-gradient(135deg, #059669 0%, #1e3a8a 100%);
            padding: 28px 32px; border-radius: 18px; color: white;
            margin-bottom: 25px; box-shadow: 0 8px 24px rgba(15, 23, 42, .16);
        }
        .title-banner h1 { margin: 0; font-size: 2.1rem; font-weight: 800; }
        .title-banner p { margin: 8px 0 0; opacity: .92; font-size: 1rem; }
        div[data-testid="stMetric"] {
            background: white; border: 1px solid #e2e8f0; padding: 18px;
            border-radius: 14px; box-shadow: 0 3px 12px rgba(15, 23, 42, .06);
        }
        div[data-testid="stMetric"] label { color: #475569; font-weight: 600; }
        .stButton > button { border-radius: 10px; min-height: 42px; font-weight: 600; }
        section[data-testid="stSidebar"] { background: #f1f5f9; }
        .data-status {
            background: #ecfdf5; border: 1px solid #a7f3d0; padding: 10px 14px;
            border-radius: 10px; color: #065f46; font-size: .9rem; margin-bottom: 15px;
        }
        .insight {
            background: #ecfdf5; border-left: 5px solid #10b981; padding: 12px 15px;
            border-radius: 8px; color: #064e3b; margin: 8px 0 18px;
        }
    </style>
    <div class="title-banner">
        <h1>⚡ BTP EcoWaste Pro</h1>
        <p>Suivi intelligent des déchets, des coûts et de l'impact carbone des chantiers</p>
    </div>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 8. OPTIONS ORIGINALES : TEST ET GESTION DES DONNÉES
# ==============================================================================
st.sidebar.header("🧪 Données de test")

if st.sidebar.button("📊 Ajouter les données de démonstration", use_container_width=True):
    demo_df = create_demo_data()
    if not st.session_state.df.empty:
        demo_df = pd.concat([st.session_state.df, demo_df], ignore_index=True)
    save_and_invalidate_cache(demo_df)
    st.sidebar.success("Données de démonstration ajoutées.")
    st.rerun()

if st.sidebar.button("🔄 Remplacer par les données de test", use_container_width=True):
    demo_df = create_demo_data()
    save_and_invalidate_cache(demo_df)
    st.session_state.source_file = DATA_FILE
    st.sidebar.success("Jeu de test chargé.")
    st.rerun()

if st.sidebar.button("🗑️ Vider toutes les données", use_container_width=True):
    empty_df = pd.DataFrame(columns=COLONNES_ATTENDUES)
    save_and_invalidate_cache(empty_df)
    st.sidebar.success("Toutes les données ont été supprimées.")
    st.rerun()

st.sidebar.caption(f"💾 Stockage actif : {DATA_FILE}")
st.sidebar.markdown("---")

# ==============================================================================
# 9. AJOUT : LISTE DE FICHIERS CSV ET SÉLECTION PAR L'UTILISATEUR
# ======================================================================
st.sidebar.header("📁 Fichiers CSV disponibles")

available_paths = liste_fichiers_csv()
available_names = [os.path.basename(path) for path in available_paths]

if available_names:
    selected_name = st.sidebar.selectbox(
        "Choisir un fichier à tester",
        available_names,
        index=(available_names.index(os.path.basename(st.session_state.source_file))
               if os.path.basename(st.session_state.source_file) in available_names else 0)
    )

    if st.sidebar.button("🧪 Tester le fichier sélectionné", use_container_width=True):
        selected_path = next(
            path for path in available_paths
            if os.path.basename(path) == selected_name
        )
        selected_df = lire_fichier_csv(selected_path)
        st.session_state.df = selected_df
        st.session_state.source_file = selected_path
        st.sidebar.success(f"{len(selected_df)} ligne(s) chargée(s).")
        st.rerun()
else:
    st.sidebar.info("Aucun fichier CSV dans data/.")

st.sidebar.caption("Ajoutez d'autres CSV dans le dossier data/ de votre dépôt GitHub.")
st.sidebar.markdown("---")

# ==============================================================================
# 10. BARRE LATERALE - IMPORTATION ORIGINALE CONSERVÉE ET RENFORCÉE
# ==============================================================================
st.sidebar.header("📂 Importation CSV")

uploaded_file = st.sidebar.file_uploader(
    "Importer un registre CSV",
    type=["csv"],
    help="Colonnes recommandées : Chantier, Zone, Date, Type, Quantite..."
)

if uploaded_file is not None:
    try:
        imported_df = pd.read_csv(uploaded_file)
        required_minimal = ["Chantier", "Zone", "Date", "Type", "Quantite"]
        missing_cols = [col for col in required_minimal if col not in imported_df.columns]

        if missing_cols:
            st.sidebar.error(
                "⚠️ Colonnes requises manquantes : " + ", ".join(missing_cols)
            )
        else:
            imported_cleaned = normaliser_dataframe(imported_df)
            st.sidebar.success(f"🔍 Fichier valide ({len(imported_cleaned)} lignes)")

            file_name = st.sidebar.text_input(
                "Nom du fichier à stocker",
                value=f"import_{datetime.now():%Y%m%d_%H%M%S}.csv"
            )
            if not file_name.lower().endswith(".csv"):
                file_name += ".csv"

            col_b1, col_b2 = st.sidebar.columns(2)

            if col_b1.button("➕ Fusionner"):
                df_merged = pd.concat(
                    [st.session_state.df, imported_cleaned],
                    ignore_index=True
                )
                save_and_invalidate_cache(df_merged)
                save_path = os.path.join(DATA_DIRECTORY, os.path.basename(file_name))
                df_merged.to_csv(save_path, index=False, encoding="utf-8-sig")
                st.session_state.source_file = save_path
                st.sidebar.success("Données fusionnées avec succès !")
                st.rerun()

            if col_b2.button("🗑️ Remplacer"):
                save_and_invalidate_cache(imported_cleaned)
                save_path = os.path.join(DATA_DIRECTORY, os.path.basename(file_name))
                imported_cleaned.to_csv(save_path, index=False, encoding="utf-8-sig")
                st.session_state.source_file = save_path
                st.sidebar.success("Base de données remplacée !")
                st.rerun()

    except Exception as error:
        st.sidebar.error(f"Erreur d'importation : {error}")

# ==============================================================================
# 11. SAISIE MANUELLE ORIGINALE CONSERVÉE
# ==============================================================================
st.sidebar.markdown("---")
st.sidebar.header("📝 Saisie manuelle rapide")

with st.sidebar.form("form_dechet", clear_on_submit=True):
    c_chantier = st.selectbox("Chantier", CHANTIERS_DISPONIBLES)
    c_zone = st.selectbox("Zone / Lot", ZONES_CHANTIER)
    c_date = st.date_input("Date", date.today())
    c_type = st.selectbox("Matériau", list(REFERENTIEL_MATERIAUX.keys()))
    unite = REFERENTIEL_MATERIAUX[c_type]["unite"]
    c_qte = st.number_input(f"Quantité ({unite})", min_value=0.1, step=1.0, value=1.0)
    c_filiere = st.selectbox("Filière de traitement", FILIERES_VALORISATION)
    c_cause = st.selectbox("Cause du déchet", CAUSES_FREQUENTES)
    submitted = st.form_submit_button("⚡ Enregistrer", use_container_width=True)

if submitted:
    cout = c_qte * REFERENTIEL_MATERIAUX[c_type]["prix"]
    co2 = c_qte * REFERENTIEL_MATERIAUX[c_type]["co2_facteur"]

    new_entry = pd.DataFrame([{
        "Chantier": c_chantier,
        "Zone": c_zone,
        "Date": pd.to_datetime(c_date),
        "Type": c_type,
        "Quantite": c_qte,
        "Unite": unite,
        "Cout_Estime": cout,
        "Filiere": c_filiere,
        "Cause": c_cause,
        "CO2_Impact_kg": co2
    }])

    df_new = pd.concat([st.session_state.df, new_entry], ignore_index=True)
    save_and_invalidate_cache(df_new)
    if st.session_state.source_file and st.session_state.source_file != DATA_FILE:
        df_new.to_csv(st.session_state.source_file, index=False, encoding="utf-8-sig")
    st.sidebar.success("✅ Déchet enregistré et sauvegardé !")
    st.rerun()

# ==============================================================================
# 12. FILTRES GLOBAUX ORIGINAUX CONSERVÉS
# ==============================================================================
df_current = normaliser_dataframe(st.session_state.df)
st.session_state.df = df_current

st.sidebar.markdown("---")
st.sidebar.header("🔍 Filtres globaux")

if not df_current.empty:
    chantiers_opts = df_current["Chantier"].dropna().unique().tolist()
    filter_chantier = st.sidebar.multiselect(
        "Chantiers",
        options=chantiers_opts,
        default=chantiers_opts
    )
    df_view = df_current[df_current["Chantier"].isin(filter_chantier)]
else:
    df_view = df_current

st.markdown(
    f'<div class="data-status">💾 {len(df_current)} '
    f'enregistrement(s) conservé(s) dans <b>{os.path.basename(st.session_state.source_file)}</b></div>',
    unsafe_allow_html=True
)

# ==============================================================================
# 13. FILTRES SUPPLÉMENTAIRES AJOUTÉS
# ==============================================================================
if not df_current.empty:
    with st.expander("🔎 Filtres avancés : zone, type et période", expanded=False):
        f1, f2, f3 = st.columns(3)
        zones = f1.multiselect(
            "Zones", sorted(df_view["Zone"].dropna().unique()),
            default=sorted(df_view["Zone"].dropna().unique())
        )
        types = f2.multiselect(
            "Types de déchets", sorted(df_view["Type"].dropna().unique()),
            default=sorted(df_view["Type"].dropna().unique())
        )
        date_range = f3.date_input(
            "Période",
            value=(df_view["Date"].min().date(), df_view["Date"].max().date())
        )

    if not isinstance(date_range, tuple) or len(date_range) != 2:
        date_range = (date_range, date_range)

    start_date = pd.Timestamp(date_range[0])
    end_date = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
    df_view = df_view[
        df_view["Zone"].isin(zones)
        & df_view["Type"].isin(types)
        & (df_view["Date"] >= start_date)
        & (df_view["Date"] < end_date)
    ]

# ==============================================================================
# 14. INTERPRÉTATION AUTOMATIQUE AJOUTÉE
# ==============================================================================
def afficher_interpretation(message):
    st.markdown(
        f'<div class="insight">💡 {message}</div>',
        unsafe_allow_html=True
    )


def interpretation_generale(df):
    if df.empty:
        return "Aucune donnée ne correspond aux filtres sélectionnés."

    cout = df["Cout_Estime"].sum()
    co2 = df["CO2_Impact_kg"].sum()
    valorisation = df["Filiere"].isin([
        "Réemploi sur site", "Recyclage / Filière externe"
    ]).mean() * 100
    type_principal = df.groupby("Type")["Cout_Estime"].sum().idxmax()
    zone_principale = df.groupby("Zone")["Cout_Estime"].sum().idxmax()
    cause_principale = df.groupby("Cause")["Cout_Estime"].sum().idxmax()

    return (
        f"### Conclusion générale\n\n"
        f"L'analyse porte sur **{len(df)} relevé(s)**. Les pertes estimées atteignent "
        f"**{cout:,.0f} FCFA**, avec un impact carbone de **{co2:,.1f} kg CO₂eq**. "
        f"Le matériau prioritaire est **{type_principal}**. La zone la plus coûteuse est "
        f"**{zone_principale}**, tandis que la cause principale est **{cause_principale}**. "
        f"Le taux de valorisation atteint **{valorisation:.1f} %**.\n\n"
        f"### Recommandations\n\n"
        f"- Contrôler les commandes et les quantités livrées.\n"
        f"- Renforcer le stockage dans la zone **{zone_principale}**.\n"
        f"- Traiter prioritairement la cause **{cause_principale}**.\n"
        f"- Développer le réemploi et le recyclage avant la mise en décharge."
    )

# ==============================================================================
# 15. RÉSULTATS ET GRAPHIQUES ORIGINAUX CONSERVÉS + INTERPRÉTATIONS
# ==============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Métriques & KPIs",
    "📈 Analyse Coûts & Causes",
    "🌱 Bilan RSE / Tri",
    "📋 Registre & Export",
    "🧠 Interprétation & Conclusion"
])

if df_view.empty:
    st.info(
        "ℹ️ Aucune donnée à analyser. Utilisez les données de démonstration, "
        "importez un fichier CSV ou saisissez un déchet."
    )
else:
    with tab1:
        c1, c2, c3, c4 = st.columns(4)

        perte_totale = df_view["Cout_Estime"].sum()
        total_lignes = len(df_view)
        revalorises = df_view["Filiere"].isin([
            "Réemploi sur site", "Recyclage / Filière externe"
        ]).sum()
        taux_reval = revalorises / total_lignes * 100 if total_lignes > 0 else 0
        total_co2 = df_view["CO2_Impact_kg"].sum()

        c1.metric("💸 Coût total des pertes", f"{perte_totale:,.0f} FCFA")
        c2.metric("📦 Relevés totaux", f"{total_lignes}")
        c3.metric("♻️ Taux de valorisation", f"{taux_reval:.1f} %")
        c4.metric("🌍 Impact carbone", f"{total_co2:,.1f} kg CO₂")

        st.markdown("---")
        g1, g2 = st.columns(2)

        with g1:
            pie_data = df_view.groupby("Type", as_index=False)["Cout_Estime"].sum()
            fig_pie = px.pie(
                pie_data, names="Type", values="Cout_Estime", hole=0.45,
                title="Coûts financiers par matériau (FCFA)"
            )
            fig_pie.update_layout(margin=dict(t=50, b=10, l=10, r=10))
            st.plotly_chart(fig_pie, use_container_width=True, config=PLOT_CONFIG)
            top_type = pie_data.sort_values("Cout_Estime", ascending=False).iloc[0]["Type"]
            afficher_interpretation(f"Le matériau générant le coût le plus élevé est **{top_type}**.")

        with g2:
            trend_df = df_view.groupby(["Date", "Type"], as_index=False)["Cout_Estime"].sum()
            fig_line = px.line(
                trend_df, x="Date", y="Cout_Estime", color="Type", markers=True,
                title="Évolution chronologique des pertes"
            )
            fig_line.update_layout(margin=dict(t=50, b=10, l=10, r=10))
            st.plotly_chart(fig_line, use_container_width=True, config=PLOT_CONFIG)
            afficher_interpretation("Ce graphique permet de repérer les périodes de hausse des pertes et de déclencher une action corrective.")

    with tab2:
        a1, a2 = st.columns(2)

        with a1:
            cause_df = df_view.groupby("Cause", as_index=False)["Cout_Estime"].sum().sort_values("Cout_Estime")
            fig_bar_cause = px.bar(
                cause_df, x="Cout_Estime", y="Cause", orientation="h",
                color="Cout_Estime", color_continuous_scale="Reds",
                title="Impact par cause racine"
            )
            st.plotly_chart(fig_bar_cause, use_container_width=True, config=PLOT_CONFIG)
            afficher_interpretation(f"La cause prioritaire est **{cause_df.iloc[-1]['Cause']}**.")

        with a2:
            zone_df = df_view.groupby("Zone", as_index=False)["Cout_Estime"].sum()
            fig_bar_zone = px.bar(
                zone_df, x="Zone", y="Cout_Estime", color="Zone",
                title="Coûts par zone / lot"
            )
            st.plotly_chart(fig_bar_zone, use_container_width=True, config=PLOT_CONFIG)
            top_zone = zone_df.sort_values("Cout_Estime", ascending=False).iloc[0]["Zone"]
            afficher_interpretation(f"La zone nécessitant le plus d'attention est **{top_zone}**.")

    with tab3:
        r1, r2 = st.columns(2)

        with r1:
            filiere_df = df_view.groupby("Filiere", as_index=False)["Quantite"].sum()
            fig_fil = px.bar(
                filiere_df, x="Filiere", y="Quantite", color="Filiere",
                title="Destination des déchets"
            )
            st.plotly_chart(fig_fil, use_container_width=True, config=PLOT_CONFIG)
            afficher_interpretation(
                f"Le taux de valorisation est de **{taux_reval:.1f} %**. "
                "Le réemploi et le recyclage doivent être privilégiés."
            )

        with r2:
            co2_df = df_view.groupby("Type", as_index=False)["CO2_Impact_kg"].sum()
            fig_co2 = px.pie(
                co2_df, names="Type", values="CO2_Impact_kg",
                title="Bilan carbone (kg CO₂eq)"
            )
            st.plotly_chart(fig_co2, use_container_width=True, config=PLOT_CONFIG)
            top_carbon = co2_df.sort_values("CO2_Impact_kg", ascending=False).iloc[0]["Type"]
            afficher_interpretation(f"Le matériau contribuant le plus au CO₂ est **{top_carbon}**.")

    with tab4:
        st.subheader("📋 Registre des déchets")
        st.dataframe(
            df_view.sort_values("Date", ascending=False),
            use_container_width=True,
            hide_index=True
        )

        csv_bytes = df_view.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 Télécharger le registre (CSV)",
            data=csv_bytes,
            file_name=f"registre_dechets_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with tab5:
        st.subheader("🧠 Interprétation automatique")
        st.markdown(interpretation_generale(df_view))

st.caption(
    "BTP EcoWaste Pro — outil d'aide à la décision. Les coûts et facteurs CO₂ "
    "doivent être adaptés aux données réelles du projet."
)

import os
import threading
import time
import urllib.request
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import streamlit as st

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="BTP EcoWaste Pro",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

PLOT_CONFIG = {"displayModeBar": False, "responsive": True}
DATA_FILE = "dechets_data.csv"
DATA_DIRECTORY = "data"
os.makedirs(DATA_DIRECTORY, exist_ok=True)

COLONNES_ATTENDUES = [
    "Chantier", "Zone", "Date", "Type", "Quantite", "Unite",
    "Cout_Estime", "Filiere", "Cause", "CO2_Impact_kg"
]

# ==============================================================================
# 2. REFERENTIELS BTP
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
    "Déchets Dangereux (Peintures/Huiles)": {"prix": 5000, "unite": "Litre", "co2_facteur": 3.0},
}

FILIERES_VALORISATION = [
    "Réemploi sur site",
    "Recyclage / Filière externe",
    "Revalorisation Énergétique",
    "Mise en Décharge / CET (Non Valorisé)",
]

CAUSES_FREQUENTES = [
    "Sur-commande / Surplus de stock",
    "Erreur de découpe / Mise en œuvre",
    "Casse à la manutention / Transport",
    "Intempéries / Stockage inadéquat",
    "Fin de péremption (Mortier/Ciment)",
    "Non-conformité / Défaut livraison",
]

CHANTIERS_DISPONIBLES = [
    "Chantier Tour Horizon (GC)",
    "Chantier Riviera",
    "Pont Autoroutier Est",
]

ZONES_CHANTIER = [
    "Zone A - Gros Œuvre",
    "Zone B - Second Œuvre",
    "Zone C - Base Vie / Stockage",
    "Voirie & Réseaux (VRD)",
]

# ==============================================================================
# 3. STYLE
# ==============================================================================
st.markdown(
    """
    <style>
    .stApp { background: #f8fafc; }
    .block-container { max-width: 1500px; padding-top: 2rem; }
    .title-banner {
        background: linear-gradient(135deg, #059669 0%, #1e3a8a 100%);
        padding: 28px 32px; border-radius: 18px; color: white;
        margin-bottom: 25px; box-shadow: 0 8px 24px rgba(15,23,42,.16);
    }
    .title-banner h1 { margin: 0; font-size: 2.1rem; font-weight: 800; }
    .title-banner p { margin: 8px 0 0; opacity: .92; }
    div[data-testid="stMetric"] {
        background: white; border: 1px solid #e2e8f0; padding: 18px;
        border-radius: 14px; box-shadow: 0 3px 12px rgba(15,23,42,.06);
    }
    .stButton > button { border-radius: 10px; min-height: 42px; font-weight: 600; }
    .data-status {
        background: #ecfdf5; border: 1px solid #a7f3d0; padding: 10px 14px;
        border-radius: 10px; color: #065f46; margin-bottom: 15px;
    }
    .insight {
        background: #ecfdf5; border-left: 5px solid #10b981;
        padding: 12px 15px; border-radius: 8px; color: #064e3b;
        margin: 8px 0 18px;
    }
    </style>
    <div class="title-banner">
      <h1>⚡ BTP EcoWaste Pro</h1>
      <p>Suivi intelligent des déchets, des coûts et de l'impact carbone des chantiers</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 4. ANTI-SOMMEIL CONSERVE ET OPTIONNEL
# ==============================================================================
APP_URL = os.getenv("STREAMLIT_APP_URL", "")


def background_keep_alive(target_url, interval_sec=600):
    """Ping optionnel. La politique de veille dépend de l'hébergeur."""
    while True:
        try:
            if target_url:
                request = urllib.request.Request(
                    target_url,
                    headers={"User-Agent": "BTP-EcoWaste-KeepAlive"},
                )
                with urllib.request.urlopen(request, timeout=10):
                    pass
        except Exception:
            pass
        time.sleep(interval_sec)


if "keep_alive_started" not in st.session_state and APP_URL:
    threading.Thread(
        target=background_keep_alive,
        args=(APP_URL, 600),
        daemon=True,
    ).start()
    st.session_state["keep_alive_started"] = True

# ==============================================================================
# 5. DONNEES ET NORMALISATION
# ==============================================================================
def dataframe_vide():
    return pd.DataFrame(columns=COLONNES_ATTENDUES)


def normaliser_dataframe(df):
    """Complète les colonnes et évite les erreurs de type/date."""
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
            ).get("prix", 0),
            axis=1,
        )
    df["Cout_Estime"] = pd.to_numeric(df["Cout_Estime"], errors="coerce").fillna(0)

    if "CO2_Impact_kg" not in df.columns:
        df["CO2_Impact_kg"] = df.apply(
            lambda row: row["Quantite"] * REFERENTIEL_MATERIAUX.get(
                row["Type"], {}
            ).get("co2_facteur", 0),
            axis=1,
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
        return dataframe_vide()


def sauvegarder_fichier(df, path):
    normaliser_dataframe(df).to_csv(path, index=False, encoding="utf-8-sig")


def liste_fichiers_csv():
    """Liste uniquement les fichiers CSV réellement disponibles."""
    fichiers = []
    if os.path.exists(DATA_FILE):
        fichiers.append(DATA_FILE)
    if os.path.isdir(DATA_DIRECTORY):
        fichiers.extend(
            os.path.join(DATA_DIRECTORY, nom)
            for nom in sorted(os.listdir(DATA_DIRECTORY))
            if nom.lower().endswith(".csv")
        )
    return fichiers


def create_demo_data():
    """Données conservées pour le bouton de démonstration manuelle."""
    rows = [
        ["Chantier Tour Horizon (GC)", "Zone A - Gros Œuvre", "2026-01-15", "Béton résiduel", 3.5, "Réemploi sur site", "Sur-commande / Surplus de stock"],
        ["Chantier Riviera", "Zone B - Second Œuvre", "2026-02-04", "Bois de coffrage", 25, "Recyclage / Filière externe", "Erreur de découpe / Mise en œuvre"],
        ["Pont Autoroutier Est", "Voirie & Réseaux (VRD)", "2026-03-12", "Gravats / Remblais", 8, "Mise en Décharge / CET (Non Valorisé)", "Casse à la manutention / Transport"],
        ["Chantier Tour Horizon (GC)", "Zone C - Base Vie / Stockage", "2026-04-20", "Cartons & Emballages", 120, "Recyclage / Filière externe", "Sur-commande / Surplus de stock"],
        ["Chantier Riviera", "Zone A - Gros Œuvre", "2026-05-08", "Chutes de fer / Acier", 180, "Recyclage / Filière externe", "Non-conformité / Défaut livraison"],
        ["Pont Autoroutier Est", "Zone B - Second Œuvre", "2026-06-17", "Plâtre / Chutes de placo", 2.4, "Mise en Décharge / CET (Non Valorisé)", "Casse à la manutention / Transport"],
    ]
    columns = ["Chantier", "Zone", "Date", "Type", "Quantite", "Filiere", "Cause"]
    return normaliser_dataframe(pd.DataFrame(rows, columns=columns))


# IMPORTANT : aucune donnée n'est chargée automatiquement.
# Une nouvelle session commence toujours vide.
if "session_initialisee" not in st.session_state:
    st.session_state.df = dataframe_vide()
    st.session_state.source_file = ""
    st.session_state.session_initialisee = True

# ==============================================================================
# 6. SIDEBAR : CHOIX MANUEL D'UN FICHIER DE CHANTIER
# ==============================================================================
st.sidebar.header("📁 Données des chantiers")

available_paths = liste_fichiers_csv()
available_names = [os.path.basename(path) for path in available_paths]

if available_names:
    selected_name = st.sidebar.selectbox(
        "Choisir un fichier / chantier à tester",
        available_names,
    )

    if st.sidebar.button("🧪 Tester ce chantier", use_container_width=True):
        selected_path = next(
            path for path in available_paths
            if os.path.basename(path) == selected_name
        )
        selected_df = lire_fichier_csv(selected_path)

        if selected_df.empty:
            st.sidebar.error("Fichier vide ou données invalides.")
        else:
            st.session_state.df = selected_df
            st.session_state.source_file = selected_path
            st.rerun()
else:
    st.sidebar.info(
        "Aucun fichier disponible. Ajoutez vos CSV dans le dossier data/."
    )

st.sidebar.caption(
    "Les fichiers sont gérés par vous. Aucun fichier de démonstration n'est créé automatiquement."
)
st.sidebar.markdown("---")

# ==============================================================================
# 7. BOUTONS DE DEMONSTRATION MANUELLE
# ==============================================================================
st.sidebar.header("🧪 Données de démonstration")

if st.sidebar.button("📊 Charger la démonstration", use_container_width=True):
    st.session_state.df = create_demo_data()
    st.session_state.source_file = "Démonstration temporaire"
    st.rerun()

if st.sidebar.button("🗑️ Réinitialiser la session", use_container_width=True):
    st.session_state.df = dataframe_vide()
    st.session_state.source_file = ""
    st.rerun()

# ==============================================================================
# 8. IMPORTATION CSV
# ==============================================================================
st.sidebar.header("📂 Importation CSV")
uploaded_file = st.sidebar.file_uploader(
    "Importer un registre CSV",
    type=["csv"],
    help="Colonnes recommandées : Chantier, Zone, Date, Type, Quantite...",
)

if uploaded_file is not None:
    try:
        raw_import = pd.read_csv(uploaded_file)
        required = ["Chantier", "Zone", "Date", "Type", "Quantite"]
        missing = [col for col in required if col not in raw_import.columns]

        if missing:
            st.sidebar.error("Colonnes manquantes : " + ", ".join(missing))
        else:
            imported_df = normaliser_dataframe(raw_import)
            st.sidebar.success(f"Fichier valide : {len(imported_df)} ligne(s)")
            import_name = st.sidebar.text_input(
                "Nom du fichier à stocker",
                value=f"import_{datetime.now():%Y%m%d_%H%M%S}.csv",
            )
            if not import_name.lower().endswith(".csv"):
                import_name += ".csv"

            b1, b2 = st.sidebar.columns(2)
            if b1.button("➕ Fusionner"):
                current = normaliser_dataframe(st.session_state.df)
                merged = pd.concat([current, imported_df], ignore_index=True)
                sauvegarder_fichier(
                    merged,
                    os.path.join(DATA_DIRECTORY, os.path.basename(import_name)),
                )
                st.session_state.df = merged
                st.session_state.source_file = os.path.join(DATA_DIRECTORY, os.path.basename(import_name))
                st.rerun()

            if b2.button("🗑️ Remplacer"):
                path = os.path.join(DATA_DIRECTORY, os.path.basename(import_name))
                sauvegarder_fichier(imported_df, path)
                st.session_state.df = imported_df
                st.session_state.source_file = path
                st.rerun()
    except Exception as error:
        st.sidebar.error(f"Erreur d'importation : {error}")

# ==============================================================================
# 9. SAISIE MANUELLE
# ==============================================================================
st.sidebar.markdown("---")
st.sidebar.header("📝 Saisie manuelle rapide")

with st.sidebar.form("form_dechet", clear_on_submit=True):
    chantier = st.selectbox("Chantier", CHANTIERS_DISPONIBLES)
    zone = st.selectbox("Zone / Lot", ZONES_CHANTIER)
    date_constat = st.date_input("Date", date.today())
    type_dechet = st.selectbox("Matériau", list(REFERENTIEL_MATERIAUX))
    unite = REFERENTIEL_MATERIAUX[type_dechet]["unite"]
    quantite = st.number_input(
        f"Quantité ({unite})", min_value=0.1, value=1.0, step=1.0
    )
    filiere = st.selectbox("Filière de traitement", FILIERES_VALORISATION)
    cause = st.selectbox("Cause du déchet", CAUSES_FREQUENTES)
    submitted = st.form_submit_button("⚡ Enregistrer", use_container_width=True)

if submitted:
    ref = REFERENTIEL_MATERIAUX[type_dechet]
    entry = pd.DataFrame([{
        "Chantier": chantier,
        "Zone": zone,
        "Date": pd.Timestamp(date_constat),
        "Type": type_dechet,
        "Quantite": quantite,
        "Unite": unite,
        "Cout_Estime": quantite * ref["prix"],
        "Filiere": filiere,
        "Cause": cause,
        "CO2_Impact_kg": quantite * ref["co2_facteur"],
    }])
    updated = pd.concat([st.session_state.df, entry], ignore_index=True)

    # Sauvegarde dans le fichier sélectionné, ou dans le CSV principal.
    if st.session_state.source_file and os.path.isfile(st.session_state.source_file):
        target = st.session_state.source_file
    else:
        target = DATA_FILE

    sauvegarder_fichier(updated, target)
    st.session_state.df = updated
    st.session_state.source_file = target
    st.rerun()

# ==============================================================================
# 10. FILTRES SANS ERREUR DE DATE
# ==============================================================================
df_current = normaliser_dataframe(st.session_state.df)
st.session_state.df = df_current

source_label = os.path.basename(st.session_state.source_file) if st.session_state.source_file else "Aucun fichier testé"
st.markdown(
    f'<div class="data-status">💾 Source : <b>{source_label}</b> — '
    f'{len(df_current)} enregistrement(s) testé(s)</div>',
    unsafe_allow_html=True,
)

if df_current.empty:
    st.info(
        "ℹ️ Aucune donnée n'est testée. Choisissez un fichier dans la barre latérale "
        "ou importez un CSV."
    )
    st.stop()

# Filtre chantier conservé
st.sidebar.header("🔍 Filtres globaux")
chantiers = sorted(df_current["Chantier"].dropna().unique().tolist())
selected_chantiers = st.sidebar.multiselect(
    "Chantiers", chantiers, default=chantiers
)
df_view = df_current[df_current["Chantier"].isin(selected_chantiers)].copy()

with st.expander("🔎 Filtres avancés", expanded=False):
    f1, f2, f3 = st.columns(3)
    zones = sorted(df_view["Zone"].dropna().unique().tolist())
    types = sorted(df_view["Type"].dropna().unique().tolist())

    selected_zones = f1.multiselect("Zones", zones, default=zones)
    selected_types = f2.multiselect("Types", types, default=types)

    # Correction de l'erreur de la capture : date_input n'est appelé
    # que si les dates sont valides et si le tableau n'est pas vide.
    dates_valides = pd.to_datetime(df_view["Date"], errors="coerce").dropna()
    date_range = None
    if not dates_valides.empty:
        date_range = f3.date_input(
            "Période",
            value=(dates_valides.min().date(), dates_valides.max().date()),
        )

if date_range is not None:
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        date_start = pd.Timestamp(date_range[0])
        date_end = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
    else:
        date_start = pd.Timestamp(date_range)
        date_end = date_start + pd.Timedelta(days=1)

    df_view = df_view[
        df_view["Zone"].isin(selected_zones)
        & df_view["Type"].isin(selected_types)
        & (df_view["Date"] >= date_start)
        & (df_view["Date"] < date_end)
    ]
else:
    df_view = df_view[
        df_view["Zone"].isin(selected_zones)
        & df_view["Type"].isin(selected_types)
    ]

# ==============================================================================
# 11. INTERPRETATIONS
# ==============================================================================
def afficher_interpretation(message):
    st.markdown(
        f'<div class="insight">💡 {message}</div>',
        unsafe_allow_html=True,
    )


def interpretation_generale(data):
    if data.empty:
        return "Aucune donnée ne correspond aux filtres sélectionnés."

    cout = data["Cout_Estime"].sum()
    co2 = data["CO2_Impact_kg"].sum()
    valorisation = data["Filiere"].isin([
        "Réemploi sur site", "Recyclage / Filière externe"
    ]).mean() * 100
    type_principal = data.groupby("Type")["Cout_Estime"].sum().idxmax()
    zone_principale = data.groupby("Zone")["Cout_Estime"].sum().idxmax()
    cause_principale = data.groupby("Cause")["Cout_Estime"].sum().idxmax()

    return (
        f"### Conclusion générale\n\n"
        f"L'analyse porte sur **{len(data)} relevé(s)**. Les pertes estimées sont de "
        f"**{cout:,.0f} FCFA**, avec un impact carbone de **{co2:,.1f} kg CO₂eq**. "
        f"Le matériau prioritaire est **{type_principal}**. La zone prioritaire est "
        f"**{zone_principale}** et la cause principale est **{cause_principale}**. "
        f"Le taux de valorisation est de **{valorisation:.1f} %**.\n\n"
        "### Recommandations\n\n"
        "- Contrôler les commandes et les quantités livrées.\n"
        f"- Renforcer le stockage dans **{zone_principale}**.\n"
        f"- Traiter prioritairement **{cause_principale}**.\n"
        "- Développer le réemploi et le recyclage."
    )

# ==============================================================================
# 12. TABLEAUX DE BORD
# ==============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Métriques & KPIs",
    "📈 Analyse Coûts & Causes",
    "🌱 Bilan RSE / Tri",
    "📋 Registre & Export",
    "🧠 Interprétation & Conclusion",
])

if df_view.empty:
    st.warning("Aucun résultat pour les filtres sélectionnés.")
else:
    total_cost = df_view["Cout_Estime"].sum()
    total_rows = len(df_view)
    total_co2 = df_view["CO2_Impact_kg"].sum()
    valorised = df_view["Filiere"].isin([
        "Réemploi sur site", "Recyclage / Filière externe"
    ]).sum()
    valorisation_rate = valorised / total_rows * 100 if total_rows else 0

    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💸 Coût total des pertes", f"{total_cost:,.0f} FCFA")
        c2.metric("📦 Relevés totaux", str(total_rows))
        c3.metric("♻️ Taux de valorisation", f"{valorisation_rate:.1f} %")
        c4.metric("🌍 Impact carbone", f"{total_co2:,.1f} kg CO₂")

        st.markdown("---")
        g1, g2 = st.columns(2)
        with g1:
            pie_data = df_view.groupby("Type", as_index=False)["Cout_Estime"].sum()
            fig_pie = px.pie(
                pie_data, names="Type", values="Cout_Estime", hole=0.45,
                title="Coûts financiers par matériau (FCFA)",
            )
            st.plotly_chart(fig_pie, use_container_width=True, config=PLOT_CONFIG)
            top_type = pie_data.sort_values("Cout_Estime", ascending=False).iloc[0]["Type"]
            afficher_interpretation(f"Le matériau prioritaire est **{top_type}**.")

        with g2:
            trend_df = df_view.groupby(["Date", "Type"], as_index=False)["Cout_Estime"].sum()
            fig_line = px.line(
                trend_df, x="Date", y="Cout_Estime", color="Type", markers=True,
                title="Évolution chronologique des pertes",
            )
            st.plotly_chart(fig_line, use_container_width=True, config=PLOT_CONFIG)
            afficher_interpretation("Cette courbe permet de repérer les périodes de hausse des pertes.")

    with tab2:
        a1, a2 = st.columns(2)
        with a1:
            cause_df = df_view.groupby("Cause", as_index=False)["Cout_Estime"].sum().sort_values("Cout_Estime")
            fig_cause = px.bar(
                cause_df, x="Cout_Estime", y="Cause", orientation="h",
                color="Cout_Estime", color_continuous_scale="Reds",
                title="Impact par cause racine",
            )
            st.plotly_chart(fig_cause, use_container_width=True, config=PLOT_CONFIG)
            afficher_interpretation(f"La cause prioritaire est **{cause_df.iloc[-1]['Cause']}**.")

        with a2:
            zone_df = df_view.groupby("Zone", as_index=False)["Cout_Estime"].sum()
            fig_zone = px.bar(
                zone_df, x="Zone", y="Cout_Estime", color="Zone",
                title="Coûts par zone / lot",
            )
            st.plotly_chart(fig_zone, use_container_width=True, config=PLOT_CONFIG)
            top_zone = zone_df.sort_values("Cout_Estime", ascending=False).iloc[0]["Zone"]
            afficher_interpretation(f"La zone prioritaire est **{top_zone}**.")

    with tab3:
        r1, r2 = st.columns(2)
        with r1:
            filiere_df = df_view.groupby("Filiere", as_index=False)["Quantite"].sum()
            fig_filiere = px.bar(
                filiere_df, x="Filiere", y="Quantite", color="Filiere",
                title="Destination des déchets",
            )
            st.plotly_chart(fig_filiere, use_container_width=True, config=PLOT_CONFIG)
            afficher_interpretation(f"Le taux de valorisation est de **{valorisation_rate:.1f} %**.")

        with r2:
            co2_df = df_view.groupby("Type", as_index=False)["CO2_Impact_kg"].sum()
            fig_co2 = px.pie(
                co2_df, names="Type", values="CO2_Impact_kg",
                title="Bilan carbone (kg CO₂eq)",
            )
            st.plotly_chart(fig_co2, use_container_width=True, config=PLOT_CONFIG)
            top_carbon = co2_df.sort_values("CO2_Impact_kg", ascending=False).iloc[0]["Type"]
            afficher_interpretation(f"Le matériau contribuant le plus au CO₂ est **{top_carbon}**.")

    with tab4:
        st.subheader("📋 Registre des déchets")
        st.dataframe(
            df_view.sort_values("Date", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
        csv_bytes = df_view.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 Télécharger le registre (CSV)",
            data=csv_bytes,
            file_name=f"registre_dechets_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with tab5:
        st.subheader("🧠 Interprétation automatique")
        st.markdown(interpretation_generale(df_view))

st.caption(
    "BTP EcoWaste Pro — outil d'aide à la décision. Les coûts et facteurs CO₂ "
    "doivent être adaptés aux données réelles du projet."
)

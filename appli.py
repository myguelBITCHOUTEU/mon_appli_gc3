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

DATA_FILE = "dechets_data.csv"
DATA_DIRECTORY = "data"
PLOT_CONFIG = {"displayModeBar": False, "responsive": True}
os.makedirs(DATA_DIRECTORY, exist_ok=True)

COLONNES_ATTENDUES = [
    "Chantier", "Zone", "Date", "Type", "Quantite", "Unite",
    "Cout_Estime", "Filiere", "Cause", "CO2_Impact_kg"
]

# ==============================================================================
# 2. TRADUCTION
# ==============================================================================
TEXTES = {
    "fr": {
        "subtitle": "Collecte, analyse financière et pilotage environnemental des déchets de chantier",
        "language": "🌐 Langue",
        "demo": "📁 Données des chantiers",
        "choose": "Choisir un chantier à tester",
        "load": "🧪 Charger ce chantier",
        "import": "📥 Importer et stocker un chantier",
        "csv": "Choisir un fichier CSV",
        "store": "💾 Stocker et tester ce chantier",
        "manual": "📝 Saisie manuelle",
        "test": "🧪 Test temporaire",
        "demo_temp": "📊 Charger une démonstration temporaire",
        "reset": "🗑️ Réinitialiser la session",
        "filters": "🔍 Filtres globaux",
        "advanced": "🔎 Filtres avancés",
        "kpis": "📊 KPIs",
        "costs": "📈 Coûts & causes",
        "rse": "🌱 RSE & carbone",
        "register": "📋 Registre & export",
        "interpretation": "🧠 Interprétation précise",
        "site": "Chantier",
        "zone": "Zone / Lot",
        "date": "Date",
        "material": "Matériau",
        "quantity": "Quantité",
        "period": "Période",
        "cost": "Coût total",
        "records": "Relevés",
        "recovery": "Valorisation",
        "carbon": "CO₂",
        "save": "⚡ Enregistrer",
        "no_data": "ℹ️ Aucune donnée testée. Choisissez un fichier ou importez un CSV.",
        "no_result": "Aucun résultat pour les filtres sélectionnés.",
        "conclusion": "Conclusion",
        "recommendations": "Recommandations",
    },
    "en": {
        "subtitle": "Construction waste collection, financial analysis and environmental management",
        "language": "🌐 Language",
        "demo": "📁 Construction-site data",
        "choose": "Choose a site to test",
        "load": "🧪 Load this site",
        "import": "📥 Import and store a site",
        "csv": "Choose a CSV file",
        "store": "💾 Store and test this site",
        "manual": "📝 Manual entry",
        "test": "🧪 Temporary test",
        "demo_temp": "📊 Load temporary demo",
        "reset": "🗑️ Reset session",
        "filters": "🔍 Global filters",
        "advanced": "🔎 Advanced filters",
        "kpis": "📊 KPIs",
        "costs": "📈 Costs & causes",
        "rse": "🌱 CSR & carbon",
        "register": "📋 Register & export",
        "interpretation": "🧠 Precise interpretation",
        "site": "Construction site",
        "zone": "Zone / Lot",
        "date": "Date",
        "material": "Material",
        "quantity": "Quantity",
        "period": "Period",
        "cost": "Total cost",
        "records": "Records",
        "recovery": "Recovery rate",
        "carbon": "CO₂",
        "save": "⚡ Save",
        "no_data": "ℹ️ No data is being tested. Choose a file or import a CSV.",
        "no_result": "No result for the selected filters.",
        "conclusion": "Conclusion",
        "recommendations": "Recommendations",
    },
}

if "language" not in st.session_state:
    st.session_state.language = "fr"

lang_choice = st.sidebar.selectbox(
    "🌐 Langue / Language", ["Français", "English"],
    index=0 if st.session_state.language == "fr" else 1,
)
st.session_state.language = "fr" if lang_choice == "Français" else "en"
LANG = st.session_state.language


def t(key):
    return TEXTES[LANG].get(key, key)

# ==============================================================================
# 3. RÉFÉRENTIELS
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

FILIERES = [
    "Réemploi sur site", "Recyclage / Filière externe",
    "Revalorisation Énergétique", "Mise en Décharge / CET (Non Valorisé)",
]
CAUSES = [
    "Sur-commande / Surplus de stock", "Erreur de découpe / Mise en œuvre",
    "Casse à la manutention / Transport", "Intempéries / Stockage inadéquat",
    "Fin de péremption (Mortier/Ciment)", "Non-conformité / Défaut livraison",
]
CHANTIERS = ["Chantier Tour Horizon (GC)", "Chantier Riviera", "Pont Autoroutier Est"]
ZONES = [
    "Zone A - Gros Œuvre", "Zone B - Second Œuvre",
    "Zone C - Base Vie / Stockage", "Voirie & Réseaux (VRD)",
]

# ==============================================================================
# 4. INTERFACE ET ANTI-SOMMEIL OPTIONNEL
# ==============================================================================
st.markdown(
    f"""
    <style>
    .stApp {{ background:#f6f8fb; }}
    .hero {{ background:linear-gradient(135deg,#0f172a,#075985,#059669); color:white;
             padding:28px 32px; border-radius:18px; margin-bottom:24px; }}
    .hero h1 {{ margin:0; font-size:2.2rem; font-weight:800; }}
    .hero p {{ margin:8px 0 0; opacity:.9; }}
    [data-testid="stMetric"] {{ background:white; border:1px solid #e2e8f0;
             border-radius:14px; padding:15px; box-shadow:0 3px 12px #0f172a12; }}
    .insight {{ background:#ecfdf5; border-left:5px solid #10b981; padding:12px 15px;
             border-radius:8px; color:#064e3b; margin:8px 0 18px; }}
    </style>
    <div class="hero"><h1>🏗️ BTP EcoWaste Pro</h1><p>{t('subtitle')}</p></div>
    """, unsafe_allow_html=True,
)

APP_URL = os.getenv("STREAMLIT_APP_URL", "")


def background_keep_alive(url, interval=600):
    while True:
        try:
            if url:
                request = urllib.request.Request(url, headers={"User-Agent": "BTP-EcoWaste-KeepAlive"})
                with urllib.request.urlopen(request, timeout=10):
                    pass
        except Exception:
            pass
        time.sleep(interval)


if "keep_alive_started" not in st.session_state and APP_URL:
    threading.Thread(target=background_keep_alive, args=(APP_URL,), daemon=True).start()
    st.session_state.keep_alive_started = True

# ==============================================================================
# 5. NORMALISATION ET STOCKAGE
# ==============================================================================
def dataframe_vide():
    return pd.DataFrame(columns=COLONNES_ATTENDUES)


def normaliser_dataframe(df):
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
        df["Unite"] = df["Type"].map(lambda x: REFERENTIEL_MATERIAUX.get(x, {}).get("unite", "U"))
    if "Cout_Estime" not in df.columns:
        df["Cout_Estime"] = df.apply(lambda r: r["Quantite"] * REFERENTIEL_MATERIAUX.get(r["Type"], {}).get("prix", 0), axis=1)
    df["Cout_Estime"] = pd.to_numeric(df["Cout_Estime"], errors="coerce").fillna(0)
    if "CO2_Impact_kg" not in df.columns:
        df["CO2_Impact_kg"] = df.apply(lambda r: r["Quantite"] * REFERENTIEL_MATERIAUX.get(r["Type"], {}).get("co2_facteur", 0), axis=1)
    df["CO2_Impact_kg"] = pd.to_numeric(df["CO2_Impact_kg"], errors="coerce").fillna(0)
    for col in ["Filiere", "Cause"]:
        if col not in df.columns:
            df[col] = "Non spécifié"
        df[col] = df[col].fillna("Non spécifié").astype(str)
    for col in ["Chantier", "Zone", "Type", "Unite"]:
        df[col] = df[col].fillna("Non spécifié").astype(str)
    return df[COLONNES_ATTENDUES]


def lire_csv(path):
    try:
        return normaliser_dataframe(pd.read_csv(path))
    except Exception:
        return dataframe_vide()


def sauvegarder_csv(df, path):
    normaliser_dataframe(df).to_csv(path, index=False, encoding="utf-8-sig")


def fichiers_stockes():
    files = []
    if os.path.exists(DATA_FILE):
        files.append(DATA_FILE)
    files.extend(os.path.join(DATA_DIRECTORY, n) for n in sorted(os.listdir(DATA_DIRECTORY)) if n.lower().endswith(".csv"))
    return files


def nom_securise(name):
    name = os.path.basename(name.strip())
    return name if name.lower().endswith(".csv") else name + ".csv"


def creer_demo():
    rows = [
        ["Chantier Tour Horizon (GC)", "Zone A - Gros Œuvre", "2026-01-15", "Béton résiduel", 3.5, "Réemploi sur site", "Sur-commande / Surplus de stock"],
        ["Chantier Riviera", "Zone B - Second Œuvre", "2026-02-04", "Bois de coffrage", 25, "Recyclage / Filière externe", "Erreur de découpe / Mise en œuvre"],
        ["Pont Autoroutier Est", "Voirie & Réseaux (VRD)", "2026-03-12", "Gravats / Remblais", 8, "Mise en Décharge / CET (Non Valorisé)", "Casse à la manutention / Transport"],
        ["Chantier Tour Horizon (GC)", "Zone C - Base Vie / Stockage", "2026-04-20", "Cartons & Emballages", 120, "Recyclage / Filière externe", "Sur-commande / Surplus de stock"],
        ["Chantier Riviera", "Zone A - Gros Œuvre", "2026-05-08", "Chutes de fer / Acier", 180, "Recyclage / Filière externe", "Non-conformité / Défaut livraison"],
        ["Pont Autoroutier Est", "Zone B - Second Œuvre", "2026-06-17", "Plâtre / Chutes de placo", 2.4, "Mise en Décharge / CET (Non Valorisé)", "Casse à la manutention / Transport"],
    ]
    cols = ["Chantier", "Zone", "Date", "Type", "Quantite", "Filiere", "Cause"]
    return normaliser_dataframe(pd.DataFrame(rows, columns=cols))


# Aucune donnée n'est testée automatiquement lors d'une nouvelle session.
if "session_initialisee" not in st.session_state:
    st.session_state.df = dataframe_vide()
    st.session_state.source_file = ""
    st.session_state.session_initialisee = True

# ==============================================================================
# 6. FICHIERS, IMPORTATION ET SAISIE
# ==============================================================================
st.sidebar.header(t("demo"))
paths = fichiers_stockes()
names = [os.path.basename(p) for p in paths]

if names:
    chosen = st.sidebar.selectbox(t("choose"), names)
    if st.sidebar.button(t("load"), use_container_width=True):
        path = next(p for p in paths if os.path.basename(p) == chosen)
        loaded = lire_csv(path)
        if loaded.empty:
            st.sidebar.error("Fichier vide ou données invalides.")
        else:
            st.session_state.df = loaded
            st.session_state.source_file = path
            st.rerun()
else:
    st.sidebar.info("Aucun fichier disponible. Importez vos données ci-dessous.")

st.sidebar.caption("Les fichiers importés sont ajoutés automatiquement à cette liste.")
st.sidebar.markdown("---")
st.sidebar.header(t("import"))

uploaded = st.sidebar.file_uploader(t("csv"), type=["csv"])
if uploaded is not None:
    try:
        raw = pd.read_csv(uploaded)
        required = ["Chantier", "Zone", "Date", "Type", "Quantite"]
        missing = [c for c in required if c not in raw.columns]
        if missing:
            st.sidebar.error("Colonnes manquantes : " + ", ".join(missing))
        else:
            imported = normaliser_dataframe(raw)
            st.sidebar.success(f"Fichier valide : {len(imported)} ligne(s)")
            storage_name = st.sidebar.text_input("Nom du chantier / fichier", value=os.path.splitext(uploaded.name)[0] + ".csv")
            if st.sidebar.button(t("store"), use_container_width=True):
                path = os.path.join(DATA_DIRECTORY, nom_securise(storage_name))
                sauvegarder_csv(imported, path)
                st.session_state.df = imported
                st.session_state.source_file = path
                st.rerun()
    except Exception as error:
        st.sidebar.error(f"Erreur d'importation : {error}")

st.sidebar.markdown("---")
st.sidebar.header(t("test"))
if st.sidebar.button(t("demo_temp"), use_container_width=True):
    st.session_state.df = creer_demo()
    st.session_state.source_file = "Démonstration temporaire"
    st.rerun()
if st.sidebar.button(t("reset"), use_container_width=True):
    st.session_state.df = dataframe_vide()
    st.session_state.source_file = ""
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header(t("manual"))
with st.sidebar.form("form_dechet", clear_on_submit=True):
    site = st.selectbox(t("site"), CHANTIERS)
    zone = st.selectbox(t("zone"), ZONES)
    record_date = st.date_input(t("date"), date.today())
    material = st.selectbox(t("material"), list(REFERENTIEL_MATERIAUX))
    unit = REFERENTIEL_MATERIAUX[material]["unite"]
    quantity = st.number_input(f"{t('quantity')} ({unit})", min_value=0.1, value=1.0, step=1.0)
    channel = st.selectbox("Filière / Treatment channel", FILIERES)
    cause = st.selectbox("Cause / Cause", CAUSES)
    submitted = st.form_submit_button(t("save"), use_container_width=True)

if submitted:
    ref = REFERENTIEL_MATERIAUX[material]
    row = pd.DataFrame([{
        "Chantier": site, "Zone": zone, "Date": pd.Timestamp(record_date),
        "Type": material, "Quantite": quantity, "Unite": unit,
        "Cout_Estime": quantity * ref["prix"], "Filiere": channel,
        "Cause": cause, "CO2_Impact_kg": quantity * ref["co2_facteur"],
    }])
    updated = pd.concat([st.session_state.df, row], ignore_index=True)
    target = st.session_state.source_file if os.path.isfile(st.session_state.source_file) else DATA_FILE
    sauvegarder_csv(updated, target)
    st.session_state.df = updated
    st.session_state.source_file = target
    st.rerun()

# ==============================================================================
# 7. FILTRES SÉCURISÉS
# ==============================================================================
df_current = normaliser_dataframe(st.session_state.df)
source = os.path.basename(st.session_state.source_file) if st.session_state.source_file else "Aucun fichier testé"
st.markdown(f'<div class="insight">💾 Source : <b>{source}</b> — {len(df_current)} enregistrement(s) testé(s)</div>', unsafe_allow_html=True)

if df_current.empty:
    st.info(t("no_data"))
    st.stop()

st.sidebar.header(t("filters"))
site_options = sorted(df_current["Chantier"].unique().tolist())
selected_sites = st.sidebar.multiselect(t("site"), site_options, default=site_options)
df_view = df_current[df_current["Chantier"].isin(selected_sites)].copy()

with st.expander(t("advanced"), expanded=False):
    f1, f2, f3 = st.columns(3)
    zone_options = sorted(df_view["Zone"].dropna().unique().tolist())
    type_options = sorted(df_view["Type"].dropna().unique().tolist())
    selected_zones = f1.multiselect(t("zone"), zone_options, default=zone_options)
    selected_types = f2.multiselect(t("material"), type_options, default=type_options)
    valid_dates = pd.to_datetime(df_view["Date"], errors="coerce").dropna()
    date_range = None
    if not valid_dates.empty:
        date_range = f3.date_input(t("period"), value=(valid_dates.min().date(), valid_dates.max().date()))

if date_range is not None:
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start = pd.Timestamp(date_range[0])
        end = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
    else:
        start = pd.Timestamp(date_range)
        end = start + pd.Timedelta(days=1)
    df_view = df_view[df_view["Zone"].isin(selected_zones) & df_view["Type"].isin(selected_types) & (df_view["Date"] >= start) & (df_view["Date"] < end)]
else:
    df_view = df_view[df_view["Zone"].isin(selected_zones) & df_view["Type"].isin(selected_types)]

# ==============================================================================
# 8. MOTEUR D'INTERPRÉTATION PRÉCIS ET CONCIS
# ==============================================================================
def analyser_resultats(df, langue="fr"):
    """Produit une analyse déterministe basée uniquement sur les données filtrées."""
    if df.empty:
        return "Aucune donnée disponible." if langue == "fr" else "No data available."

    data = df.copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data = data.dropna(subset=["Date"])
    if data.empty:
        return "Aucune date valide." if langue == "fr" else "No valid date."

    total_cost = float(data["Cout_Estime"].sum())
    total_co2 = float(data["CO2_Impact_kg"].sum())
    total_quantity = float(data["Quantite"].sum())
    records = len(data)
    recovery = data["Filiere"].isin(["Réemploi sur site", "Recyclage / Filière externe"]).mean() * 100

    by_type_cost = data.groupby("Type")["Cout_Estime"].sum()
    by_cause_cost = data.groupby("Cause")["Cout_Estime"].sum()
    by_zone_cost = data.groupby("Zone")["Cout_Estime"].sum()
    by_type_co2 = data.groupby("Type")["CO2_Impact_kg"].sum()

    main_type = by_type_cost.idxmax()
    main_cause = by_cause_cost.idxmax()
    main_zone = by_zone_cost.idxmax()
    main_carbon = by_type_co2.idxmax()

    daily = data.groupby("Date")["Cout_Estime"].sum().sort_index()
    if len(daily) < 2:
        trend_fr, trend_en = "non déterminée", "undetermined"
    elif daily.iloc[-1] > daily.iloc[0]:
        trend_fr, trend_en = "en hausse", "increasing"
    elif daily.iloc[-1] < daily.iloc[0]:
        trend_fr, trend_en = "en baisse", "decreasing"
    else:
        trend_fr, trend_en = "stable", "stable"

    level_fr = "faible" if recovery < 50 else "moyen" if recovery < 70 else "satisfaisant"
    level_en = "low" if recovery < 50 else "medium" if recovery < 70 else "satisfactory"

    if langue == "en":
        return f"""### Precise analysis

- **Records analyzed:** {records}
- **Total quantity:** {total_quantity:,.2f}
- **Estimated waste cost:** {total_cost:,.0f} FCFA
- **Estimated carbon impact:** {total_co2:,.1f} kg CO₂eq
- **Recovery rate:** {recovery:.1f}% ({level_en})
- **Main cost-generating material:** {main_type}
- **Main cause:** {main_cause}
- **Priority zone:** {main_zone}
- **Main carbon contributor:** {main_carbon}
- **Cost trend:** {trend_en}

**Conclusion:** Prioritize the reduction of **{main_type}** in **{main_zone}**, by addressing **{main_cause}**. Improve reuse and recycling to raise the recovery rate."""

    return f"""### Analyse précise

- **Relevés analysés :** {records}
- **Quantité totale :** {total_quantity:,.2f}
- **Coût estimé des déchets :** {total_cost:,.0f} FCFA
- **Impact carbone estimé :** {total_co2:,.1f} kg CO₂eq
- **Taux de valorisation :** {recovery:.1f} % ({level_fr})
- **Matériau générant le plus de coûts :** {main_type}
- **Cause principale :** {main_cause}
- **Zone prioritaire :** {main_zone}
- **Principal contributeur carbone :** {main_carbon}
- **Tendance des coûts :** {trend_fr}

**Conclusion :** Réduire en priorité **{main_type}** dans **{main_zone}**, en agissant sur **{main_cause}**. Renforcer le réemploi et le recyclage pour améliorer le taux de valorisation."""


def afficher_interpretation(message):
    st.markdown(f'<div class="insight">💡 {message}</div>', unsafe_allow_html=True)

# ==============================================================================
# 9. DASHBOARD ET INTERPRÉTATIONS DES GRAPHIQUES
# ==============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    t("kpis"), t("costs"), t("rse"), t("register"), t("interpretation")
])

if df_view.empty:
    st.warning(t("no_result"))
else:
    total_cost = df_view["Cout_Estime"].sum()
    total_rows = len(df_view)
    total_co2 = df_view["CO2_Impact_kg"].sum()
    recovery_rate = df_view["Filiere"].isin(["Réemploi sur site", "Recyclage / Filière externe"]).mean() * 100

    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t("cost"), f"{total_cost:,.0f} FCFA")
        c2.metric(t("records"), str(total_rows))
        c3.metric(t("recovery"), f"{recovery_rate:.1f} %")
        c4.metric(t("carbon"), f"{total_co2:,.1f} kg")
        g1, g2 = st.columns(2)
        with g1:
            grouped = df_view.groupby("Type", as_index=False)["Cout_Estime"].sum()
            fig = px.pie(grouped, names="Type", values="Cout_Estime", hole=.45, title="Coûts par matériau / Costs by material")
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
            afficher_interpretation(f"Matériau prioritaire / Priority material : **{grouped.sort_values('Cout_Estime', ascending=False).iloc[0]['Type']}**.")
        with g2:
            grouped = df_view.groupby("Date", as_index=False)["Cout_Estime"].sum()
            fig = px.line(grouped, x="Date", y="Cout_Estime", markers=True, title="Évolution des pertes / Waste cost trend")
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
            afficher_interpretation("La courbe indique l'évolution temporelle des coûts / The curve shows cost evolution over time.")

    with tab2:
        a1, a2 = st.columns(2)
        with a1:
            grouped = df_view.groupby("Cause", as_index=False)["Cout_Estime"].sum().sort_values("Cout_Estime")
            fig = px.bar(grouped, x="Cout_Estime", y="Cause", orientation="h", color="Cout_Estime", title="Pertes par cause / Losses by cause")
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
            afficher_interpretation(f"Cause prioritaire / Main cause : **{grouped.iloc[-1]['Cause']}**.")
        with a2:
            grouped = df_view.groupby("Zone", as_index=False)["Cout_Estime"].sum()
            fig = px.bar(grouped, x="Zone", y="Cout_Estime", color="Zone", title="Pertes par zone / Losses by zone")
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
            afficher_interpretation(f"Zone prioritaire / Priority zone : **{grouped.sort_values('Cout_Estime', ascending=False).iloc[0]['Zone']}**.")

    with tab3:
        r1, r2 = st.columns(2)
        with r1:
            grouped = df_view.groupby("Filiere", as_index=False)["Quantite"].sum()
            fig = px.bar(grouped, x="Filiere", y="Quantite", color="Filiere", title="Volumes par filière / Volumes by channel")
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
            afficher_interpretation(f"Taux de valorisation / Recovery rate : **{recovery_rate:.1f} %**.")
        with r2:
            grouped = df_view.groupby("Type", as_index=False)["CO2_Impact_kg"].sum()
            fig = px.pie(grouped, names="Type", values="CO2_Impact_kg", title="Impact carbone / Carbon impact")
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
            afficher_interpretation(f"Principal contributeur CO₂ / Main CO₂ contributor : **{grouped.sort_values('CO2_Impact_kg', ascending=False).iloc[0]['Type']}**.")

    with tab4:
        st.dataframe(df_view.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Télécharger / Download CSV",
            data=df_view.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"registre_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with tab5:
        st.subheader(t("interpretation"))
        st.markdown(analyser_resultats(df_view, langue=LANG))

st.caption("BTP EcoWaste Pro — Les coûts et facteurs CO₂ doivent être adaptés aux données réelles du projet.")

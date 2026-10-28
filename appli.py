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
os.makedirs(DATA_DIRECTORY, exist_ok=True)
PLOT_CONFIG = {"displayModeBar": False, "responsive": True}

COLONNES_ATTENDUES = [
    "Chantier", "Zone", "Date", "Type", "Quantite", "Unite",
    "Cout_Estime", "Filiere", "Cause", "CO2_Impact_kg",
]

# ==============================================================================
# 2. TRADUCTION FRANÇAIS / ANGLAIS
# ==============================================================================
TRADUCTIONS = {
    "fr": {
        "language": "🌐 Langue",
        "french": "Français",
        "english": "English",
        "subtitle": "Collecte, analyse financière et pilotage environnemental des déchets de chantier",
        "demo_data": "📁 Données de démonstration",
        "choose_site": "Choisir un chantier à tester",
        "load_site": "🧪 Charger ce chantier",
        "import_store": "📥 Importer et stocker un chantier",
        "choose_csv": "Choisir un fichier CSV",
        "store_test": "💾 Stocker et tester ce chantier",
        "manual": "📝 Saisie manuelle",
        "global_filters": "🔍 Filtres globaux",
        "advanced_filters": "🔎 Filtres avancés",
        "test_data": "🧪 Test temporaire",
        "temporary_demo": "📊 Charger une démonstration temporaire",
        "reset": "🗑️ Réinitialiser la session",
        "import_error": "Erreur d’importation",
        "valid_file": "Fichier valide",
        "stored_loaded": "Chantier stocké et chargé.",
        "no_file": "Aucun fichier. Importez vos données ci-dessous.",
        "no_data": "ℹ️ Aucune donnée testée. Choisissez un fichier ou importez un CSV.",
        "site": "Chantier",
        "zone": "Zone / Lot",
        "date": "Date",
        "material": "Matériau",
        "quantity": "Quantité",
        "sector": "Zone",
        "type": "Type de déchet",
        "period": "Période",
        "records": "Relevés",
        "total_cost": "Coût total",
        "valorization": "Valorisation",
        "carbon": "CO₂",
        "save": "⚡ Enregistrer",
        "kpis": "📊 KPIs",
        "costs": "📈 Coûts & causes",
        "rse": "🌱 RSE & carbone",
        "register": "📋 Registre & export",
        "interpretation": "🧠 Interprétation",
        "cost_chart": "Coûts par matériau",
        "trend_chart": "Évolution des pertes",
        "cause_chart": "Pertes par cause",
        "zone_chart": "Pertes par zone",
        "destination_chart": "Volumes par filière",
        "carbon_chart": "Impact carbone par matériau",
        "no_results": "Aucun résultat pour les filtres sélectionnés.",
        "source": "Source",
        "tested": "enregistrement(s) testé(s)",
        "conclusion": "Conclusion générale",
        "recommendations": "Recommandations",
        "file_stored_hint": "Les fichiers importés sont ajoutés automatiquement à cette liste.",
    },
    "en": {
        "language": "🌐 Language",
        "french": "Français",
        "english": "English",
        "subtitle": "Construction waste collection, financial analysis and environmental management",
        "demo_data": "📁 Demo data",
        "choose_site": "Choose a construction site to test",
        "load_site": "🧪 Load this site",
        "import_store": "📥 Import and store a construction site",
        "choose_csv": "Choose a CSV file",
        "store_test": "💾 Store and test this site",
        "manual": "📝 Manual entry",
        "global_filters": "🔍 Global filters",
        "advanced_filters": "🔎 Advanced filters",
        "test_data": "🧪 Temporary test",
        "temporary_demo": "📊 Load temporary demo",
        "reset": "🗑️ Reset session",
        "import_error": "Import error",
        "valid_file": "Valid file",
        "stored_loaded": "Construction site stored and loaded.",
        "no_file": "No file available. Import your data below.",
        "no_data": "ℹ️ No data is being tested. Choose a file or import a CSV.",
        "site": "Construction site",
        "zone": "Zone / Lot",
        "date": "Date",
        "material": "Material",
        "quantity": "Quantity",
        "sector": "Zone",
        "type": "Waste type",
        "period": "Period",
        "records": "Records",
        "total_cost": "Total cost",
        "valorization": "Recovery rate",
        "carbon": "CO₂",
        "save": "⚡ Save",
        "kpis": "📊 KPIs",
        "costs": "📈 Costs & causes",
        "rse": "🌱 CSR & carbon",
        "register": "📋 Register & export",
        "interpretation": "🧠 Interpretation",
        "cost_chart": "Costs by material",
        "trend_chart": "Waste cost trend",
        "cause_chart": "Losses by cause",
        "zone_chart": "Losses by zone",
        "destination_chart": "Volumes by treatment channel",
        "carbon_chart": "Carbon impact by material",
        "no_results": "No result for the selected filters.",
        "source": "Source",
        "tested": "record(s) tested",
        "conclusion": "General conclusion",
        "recommendations": "Recommendations",
        "file_stored_hint": "Imported files are automatically added to this list.",
    },
}

# Le choix est conservé uniquement pendant la session Streamlit.
if "language" not in st.session_state:
    st.session_state.language = "fr"

language_name = st.sidebar.selectbox(
    "🌐 Langue / Language",
    ["Français", "English"],
    index=0 if st.session_state.language == "fr" else 1,
)
st.session_state.language = "fr" if language_name == "Français" else "en"
LANG = st.session_state.language


def t(key):
    return TRADUCTIONS[LANG].get(key, key)

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
    "Réemploi sur site",
    "Recyclage / Filière externe",
    "Revalorisation Énergétique",
    "Mise en Décharge / CET (Non Valorisé)",
]
CAUSES = [
    "Sur-commande / Surplus de stock",
    "Erreur de découpe / Mise en œuvre",
    "Casse à la manutention / Transport",
    "Intempéries / Stockage inadéquat",
    "Fin de péremption (Mortier/Ciment)",
    "Non-conformité / Défaut livraison",
]
CHANTIERS = ["Chantier Tour Horizon (GC)", "Chantier Riviera", "Pont Autoroutier Est"]
ZONES = [
    "Zone A - Gros Œuvre",
    "Zone B - Second Œuvre",
    "Zone C - Base Vie / Stockage",
    "Voirie & Réseaux (VRD)",
]

# ==============================================================================
# 4. STYLE ET ANTI-SOMMEIL
# ==============================================================================
st.markdown(
    f"""
    <style>
    .stApp {{ background:#f6f8fb; }}
    .hero {{ background:linear-gradient(135deg,#0f172a,#075985,#059669);
             color:white;padding:28px 32px;border-radius:18px;margin-bottom:24px; }}
    .hero h1 {{ margin:0;font-size:2.2rem;font-weight:800; }}
    .hero p {{ margin:8px 0 0;opacity:.9; }}
    [data-testid="stMetric"] {{ background:white;border:1px solid #e2e8f0;
             border-radius:14px;padding:15px;box-shadow:0 3px 12px #0f172a12; }}
    .insight {{ background:#ecfdf5;border-left:5px solid #10b981;
             padding:12px 15px;border-radius:8px;color:#064e3b;margin:8px 0 18px; }}
    </style>
    <div class="hero"><h1>🏗️ BTP EcoWaste Pro</h1>
    <p>{t('subtitle')}</p></div>
    """,
    unsafe_allow_html=True,
)

APP_URL = os.getenv("STREAMLIT_APP_URL", "")


def background_keep_alive(url, interval=600):
    while True:
        try:
            if url:
                request = urllib.request.Request(
                    url, headers={"User-Agent": "BTP-EcoWaste-KeepAlive"}
                )
                with urllib.request.urlopen(request, timeout=10):
                    pass
        except Exception:
            pass
        time.sleep(interval)


if "keep_alive_started" not in st.session_state and APP_URL:
    threading.Thread(target=background_keep_alive, args=(APP_URL,), daemon=True).start()
    st.session_state.keep_alive_started = True

# ==============================================================================
# 5. DONNÉES ET STOCKAGE
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
    result = []
    if os.path.exists(DATA_FILE):
        result.append(DATA_FILE)
    result.extend(os.path.join(DATA_DIRECTORY, n) for n in sorted(os.listdir(DATA_DIRECTORY)) if n.lower().endswith(".csv"))
    return result


def nom_securise(nom):
    nom = os.path.basename(nom.strip())
    return nom if nom.lower().endswith(".csv") else nom + ".csv"


def creer_demo():
    rows = [
        ["Chantier Tour Horizon (GC)", "Zone A - Gros Œuvre", "2026-01-15", "Béton résiduel", 3.5, "Réemploi sur site", "Sur-commande / Surplus de stock"],
        ["Chantier Riviera", "Zone B - Second Œuvre", "2026-02-04", "Bois de coffrage", 25, "Recyclage / Filière externe", "Erreur de découpe / Mise en œuvre"],
        ["Pont Autoroutier Est", "Voirie & Réseaux (VRD)", "2026-03-12", "Gravats / Remblais", 8, "Mise en Décharge / CET (Non Valorisé)", "Casse à la manutention / Transport"],
        ["Chantier Tour Horizon (GC)", "Zone C - Base Vie / Stockage", "2026-04-20", "Cartons & Emballages", 120, "Recyclage / Filière externe", "Sur-commande / Surplus de stock"],
        ["Chantier Riviera", "Zone A - Gros Œuvre", "2026-05-08", "Chutes de fer / Acier", 180, "Recyclage / Filière externe", "Non-conformité / Défaut livraison"],
        ["Pont Autoroutier Est", "Zone B - Second Œuvre", "2026-06-17", "Plâtre / Chutes de placo", 2.4, "Mise en Décharge / CET (Non Valorisé)", "Casse à la manutention / Transport"],
    ]
    return normaliser_dataframe(pd.DataFrame(rows, columns=["Chantier", "Zone", "Date", "Type", "Quantite", "Filiere", "Cause"]))


# Nouvelle session = aucune donnée testée.
if "session_initialisee" not in st.session_state:
    st.session_state.df = dataframe_vide()
    st.session_state.source_file = ""
    st.session_state.session_initialisee = True

# ==============================================================================
# 6. CHOIX D'UN FICHIER ET IMPORTATION
# ==============================================================================
st.sidebar.header(t("demo_data"))
paths = fichiers_stockes()
names = [os.path.basename(p) for p in paths]

if names:
    selected_name = st.sidebar.selectbox(t("choose_site"), names)
    if st.sidebar.button(t("load_site"), use_container_width=True):
        selected_path = next(p for p in paths if os.path.basename(p) == selected_name)
        data = lire_csv(selected_path)
        if data.empty:
            st.sidebar.error("Fichier vide ou données invalides.")
        else:
            st.session_state.df = data
            st.session_state.source_file = selected_path
            st.rerun()
else:
    st.sidebar.info(t("no_file"))

st.sidebar.caption(t("file_stored_hint"))
st.sidebar.markdown("---")
st.sidebar.header(t("import_store"))

uploaded = st.sidebar.file_uploader(t("choose_csv"), type=["csv"])
if uploaded is not None:
    try:
        raw = pd.read_csv(uploaded)
        required = ["Chantier", "Zone", "Date", "Type", "Quantite"]
        missing = [c for c in required if c not in raw.columns]
        if missing:
            st.sidebar.error("Missing columns / Colonnes manquantes: " + ", ".join(missing))
        else:
            imported = normaliser_dataframe(raw)
            st.sidebar.success(f"{t('valid_file')} : {len(imported)}")
            storage_name = st.sidebar.text_input("Nom / File name", value=os.path.splitext(uploaded.name)[0] + ".csv")
            if st.sidebar.button(t("store_test"), use_container_width=True):
                path = os.path.join(DATA_DIRECTORY, nom_securise(storage_name))
                sauvegarder_csv(imported, path)
                st.session_state.df = imported
                st.session_state.source_file = path
                st.sidebar.success(t("stored_loaded"))
                st.rerun()
    except Exception as error:
        st.sidebar.error(f"{t('import_error')} : {error}")

# ==============================================================================
# 7. TEST TEMPORAIRE ET SAISIE MANUELLE
# ==============================================================================
st.sidebar.markdown("---")
st.sidebar.header(t("test_data"))
if st.sidebar.button(t("temporary_demo"), use_container_width=True):
    st.session_state.df = creer_demo()
    st.session_state.source_file = "Temporary demo"
    st.rerun()
if st.sidebar.button(t("reset"), use_container_width=True):
    st.session_state.df = dataframe_vide()
    st.session_state.source_file = ""
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header(t("manual"))
with st.sidebar.form("form_dechet", clear_on_submit=True):
    chantier = st.selectbox(t("site"), CHANTIERS)
    zone = st.selectbox(t("zone"), ZONES)
    constat_date = st.date_input(t("date"), date.today())
    waste_type = st.selectbox(t("material"), list(REFERENTIEL_MATERIAUX))
    unit = REFERENTIEL_MATERIAUX[waste_type]["unite"]
    quantity = st.number_input(f"{t('quantity')} ({unit})", min_value=0.1, value=1.0, step=1.0)
    channel = st.selectbox("Filière / Treatment channel", FILIERES)
    cause = st.selectbox("Cause / Cause", CAUSES)
    submitted = st.form_submit_button(t("save"), use_container_width=True)

if submitted:
    ref = REFERENTIEL_MATERIAUX[waste_type]
    row = pd.DataFrame([{
        "Chantier": chantier, "Zone": zone, "Date": pd.Timestamp(constat_date),
        "Type": waste_type, "Quantite": quantity, "Unite": unit,
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
# 8. FILTRES ROBUSTES
# ==============================================================================
df_current = normaliser_dataframe(st.session_state.df)
source = os.path.basename(st.session_state.source_file) if st.session_state.source_file else "None / Aucun fichier"
st.markdown(f'<div class="insight">💾 {t("source")} : <b>{source}</b> — {len(df_current)} {t("tested")}</div>', unsafe_allow_html=True)

if df_current.empty:
    st.info(t("no_data"))
    st.stop()

st.sidebar.header(t("global_filters"))
site_options = sorted(df_current["Chantier"].unique().tolist())
selected_sites = st.sidebar.multiselect(t("site"), site_options, default=site_options)
df_view = df_current[df_current["Chantier"].isin(selected_sites)].copy()

with st.expander(t("advanced_filters"), expanded=False):
    f1, f2, f3 = st.columns(3)
    zone_options = sorted(df_view["Zone"].dropna().unique().tolist())
    type_options = sorted(df_view["Type"].dropna().unique().tolist())
    selected_zones = f1.multiselect(t("zone"), zone_options, default=zone_options)
    selected_types = f2.multiselect(t("type"), type_options, default=type_options)
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
# 9. TABLEAUX DE BORD BILINGUES
# ==============================================================================
def insight(message):
    st.markdown(f'<div class="insight">💡 {message}</div>', unsafe_allow_html=True)


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    t("kpis"), t("costs"), t("rse"), t("register"), t("interpretation")
])

if df_view.empty:
    st.warning(t("no_results"))
else:
    total_cost = df_view["Cout_Estime"].sum()
    total_rows = len(df_view)
    total_co2 = df_view["CO2_Impact_kg"].sum()
    recovery_rate = df_view["Filiere"].isin(["Réemploi sur site", "Recyclage / Filière externe"]).mean() * 100

    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t("total_cost"), f"{total_cost:,.0f} FCFA")
        c2.metric(t("records"), str(total_rows))
        c3.metric(t("valorization"), f"{recovery_rate:.1f} %")
        c4.metric(t("carbon"), f"{total_co2:,.1f} kg")
        g1, g2 = st.columns(2)
        with g1:
            grouped = df_view.groupby("Type", as_index=False)["Cout_Estime"].sum()
            fig = px.pie(grouped, names="Type", values="Cout_Estime", hole=.45, title=t("cost_chart"))
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
            insight(f"{t('material')} : **{grouped.sort_values('Cout_Estime', ascending=False).iloc[0]['Type']}**.")
        with g2:
            grouped = df_view.groupby("Date", as_index=False)["Cout_Estime"].sum()
            fig = px.line(grouped, x="Date", y="Cout_Estime", markers=True, title=t("trend_chart"))
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
            insight(t("trend_chart"))

    with tab2:
        a1, a2 = st.columns(2)
        with a1:
            grouped = df_view.groupby("Cause", as_index=False)["Cout_Estime"].sum().sort_values("Cout_Estime")
            fig = px.bar(grouped, x="Cout_Estime", y="Cause", orientation="h", color="Cout_Estime", title=t("cause_chart"))
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
            insight(f"Cause / Cause: **{grouped.iloc[-1]['Cause']}**.")
        with a2:
            grouped = df_view.groupby("Zone", as_index=False)["Cout_Estime"].sum()
            fig = px.bar(grouped, x="Zone", y="Cout_Estime", color="Zone", title=t("zone_chart"))
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
            insight(f"Zone: **{grouped.sort_values('Cout_Estime', ascending=False).iloc[0]['Zone']}**.")

    with tab3:
        r1, r2 = st.columns(2)
        with r1:
            grouped = df_view.groupby("Filiere", as_index=False)["Quantite"].sum()
            fig = px.bar(grouped, x="Filiere", y="Quantite", color="Filiere", title=t("destination_chart"))
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
            insight(f"{t('valorization')} : **{recovery_rate:.1f} %**.")
        with r2:
            grouped = df_view.groupby("Type", as_index=False)["CO2_Impact_kg"].sum()
            fig = px.pie(grouped, names="Type", values="CO2_Impact_kg", title=t("carbon_chart"))
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
            insight(f"{t('carbon')} : **{grouped.sort_values('CO2_Impact_kg', ascending=False).iloc[0]['Type']}**.")

    with tab4:
        st.dataframe(df_view.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Download / Télécharger CSV",
            data=df_view.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"registre_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with tab5:
        main_type = df_view.groupby("Type")["Cout_Estime"].sum().idxmax()
        main_zone = df_view.groupby("Zone")["Cout_Estime"].sum().idxmax()
        main_cause = df_view.groupby("Cause")["Cout_Estime"].sum().idxmax()
        st.subheader(t("conclusion"))
        st.markdown(
            f"{t('records')} : **{total_rows}**  \n"
            f"{t('total_cost')} : **{total_cost:,.0f} FCFA**  \n"
            f"{t('carbon')} : **{total_co2:,.1f} kg CO₂eq**  \n"
            f"{t('material')} : **{main_type}**  \n"
            f"{t('sector')} : **{main_zone}**  \n"
            f"Cause principale / Main cause : **{main_cause}**  \n"
            f"{t('valorization')} : **{recovery_rate:.1f} %**"
        )
        st.subheader(t("recommendations"))
        st.markdown(
            f"- ✅ Réduire les pertes liées à **{main_cause}** / Reduce losses linked to **{main_cause}**.\n"
            f"- ✅ Renforcer le contrôle dans **{main_zone}** / Improve control in **{main_zone}**.\n"
            "- ✅ Favoriser le réemploi et le recyclage / Prioritize reuse and recycling."
        )

st.caption("BTP EcoWaste Pro — coûts et facteurs CO₂ à adapter aux données réelles.")

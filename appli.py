import streamlit as st
import pandas as pd
import plotly.express as px
import os
import threading
import time
import urllib.request
from datetime import date, datetime

# ==============================================================================
# 1. OPTIMISATION HAUTE PERFORMANCE & CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="BTP EcoWaste Pro - Import & Performance",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration graphique Plotly allégée
PLOT_CONFIG = {
    'displayModeBar': False,
    'responsive': True
}

# ==============================================================================
# 2. MODULE "ANTI-SOMMEIL" (KEEP-ALIVE AUTO-PING THREAD)
# ==============================================================================
APP_URL = os.getenv("STREAMLIT_APP_URL", "")

def background_keep_alive(target_url, interval_sec=600):
    """Effectue un ping HTTP toutes les 10 min pour maintenir le serveur actif."""
    while True:
        try:
            if target_url:
                req = urllib.request.Request(
                    target_url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) KeepAlive-Bot'}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    pass
        except Exception:
            pass
        time.sleep(interval_sec)

if "keep_alive_started" not in st.session_state and APP_URL:
    t = threading.Thread(target=background_keep_alive, args=(APP_URL, 600), daemon=True)
    t.start()
    st.session_state["keep_alive_started"] = True

# ==============================================================================
# 3. RÉFÉRENTIELS BTP EN MÉMOIRE
# ==============================================================================
DATA_FILE = "dechets_data.csv"

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

CHANTIERS_DISPONIBLES = []
ZONES_CHANTIER = ["Zone A - Gros Œuvre", "Zone B - Second Œuvre", "Zone C - Base Vie / Stockage", "Voirie & Réseaux (VRD)"]

# Colonnes attendues dans le schéma de l'application
COLONNES_ATTENDUES = [
    "Chantier", "Zone", "Date", "Type", "Quantite", "Unite", 
    "Cout_Estime", "Filiere", "Cause", "CO2_Impact_kg"
]

# ==============================================================================
# 4. GESTION DU CACHE ET CHARGEMENT
# ==============================================================================
@st.cache_data(show_spinner=False, ttl=3600)
def load_cached_data():
    """Charge les données existantes de l'application."""
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE, parse_dates=["Date"])
            # S'assurer que toutes les colonnes requises existent
            for col in COLONNES_ATTENDUES:
                if col not in df.columns:
                    df[col] = None
            return df[COLONNES_ATTENDUES]
        except Exception:
            pass
    return pd.DataFrame(columns=COLONNES_ATTENDUES)

def save_and_invalidate_cache(df):
    """Sauvegarde les données et invalide le cache."""
    df.to_csv(DATA_FILE, index=False)
    st.session_state.df = df
    load_cached_data.clear()

# Chargement initial
if "df" not in st.session_state:
    st.session_state.df = load_cached_data()

# ==============================================================================
# 5. HEADER DESIGN
# ==============================================================================
st.markdown("""
<style>
    .title-banner { background: linear-gradient(90deg, #10B981, #1E3A8A); padding: 18px; border-radius: 8px; color: white; margin-bottom: 20px;}
    .title-banner h2 { margin: 0; font-size: 1.8rem; font-weight: 700; }
    .title-banner p { margin: 0; opacity: 0.9; font-size: 0.9rem; }
    .stMetric { background-color: #F8FAFC; padding: 12px; border-radius: 8px; border: 1px solid #E2E8F0; }
</style>
<div class='title-banner'>
    <h2>⚡ BTP EcoWaste Pro — Importation & Monitoring</h2>
    <p>Saisie en direct et importation de fichiers CSV de terrain de manière instantanée</p>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# 6. BARRE LATÉRALE - IMPORTATION & SAISIE
# ==============================================================================
st.sidebar.header("📂 Importation CSV")

uploaded_file = st.sidebar.file_uploader(
    "Importer un registre CSV", 
    type=["csv"], 
    help="Le fichier doit idéalement contenir les colonnes : Chantier, Zone, Date, Type, Quantite..."
)

if uploaded_file is not None:
    try:
        imported_df = pd.read_csv(uploaded_file)
        
        # Validation minimale des colonnes requises
        required_minimal = ["Chantier", "Zone", "Date", "Type", "Quantite"]
        missing_cols = [col for col in required_minimal if col not in imported_df.columns]
        
        if missing_cols:
            st.sidebar.error(f"⚠️ Colonnes requises manquantes : {', '.join(missing_cols)}")
        else:
            # Nettoyage et formatage des données importées
            imported_df["Date"] = pd.to_datetime(imported_df["Date"])
            
            # Auto-complétion des colonnes manquantes ou calculées (Unités, Coûts, CO2)
            if "Unite" not in imported_df.columns:
                imported_df["Unite"] = imported_df["Type"].map(lambda x: REFERENTIEL_MATERIAUX.get(x, {}).get("unite", "U"))
            
            if "Cout_Estime" not in imported_df.columns:
                imported_df["Cout_Estime"] = imported_df.apply(
                    lambda row: row["Quantite"] * REFERENTIEL_MATERIAUX.get(row["Type"], {}).get("prix", 0), axis=1
                )
                
            if "CO2_Impact_kg" not in imported_df.columns:
                imported_df["CO2_Impact_kg"] = imported_df.apply(
                    lambda row: row["Quantite"] * REFERENTIEL_MATERIAUX.get(row["Type"], {}).get("co2_facteur", 0), axis=1
                )
            
            for col in ["Filiere", "Cause"]:
                if col not in imported_df.columns:
                    imported_df[col] = "Non spécifié"
            
            # Conservation stricte de notre format attendu
            imported_cleaned = imported_df[COLONNES_ATTENDUES]
            
            st.sidebar.success(f"🔍 Fichier valide ({len(imported_cleaned)} lignes détectées)")
            
            # Boutons d'action pour l'intégration
            col_b1, col_b2 = st.sidebar.columns(2)
            
            if col_b1.button("➕ Fusionner"):
                df_merged = pd.concat([st.session_state.df, imported_cleaned], ignore_index=True)
                save_and_invalidate_cache(df_merged)
                st.sidebar.success("Données fusionnées avec succès !")
                st.rerun()
                
            if col_b2.button("🗑️ Remplacer"):
                save_and_invalidate_cache(imported_cleaned)
                st.sidebar.success("Base de données remplacée !")
                st.rerun()
                
    except Exception as e:
        st.sidebar.error(f"Erreur d'importation : {e}")

# Saisie manuelle sous l'importateur
st.sidebar.markdown("---")
st.sidebar.header("📝 Saisie Manuelle Rapide")

with st.sidebar.form("form_dechet", clear_on_submit=True):
    c_chantier = st.selectbox("Chantier", CHANTIERS_DISPONIBLES)
    c_zone = st.selectbox("Zone / Lot", ZONES_CHANTIER)
    c_date = st.date_input("Date", date.today())
    c_type = st.selectbox("Matériau", list(REFERENTIEL_MATERIAUX.keys()))
    
    unite = REFERENTIEL_MATERIAUX[c_type]["unite"]
    c_qte = st.number_input(f"Quantité ({unite})", min_value=0.1, step=1.0, value=1.0)
    
    c_filiere = st.selectbox("Filière Traitement", FILIERES_VALORISATION)
    c_cause = st.selectbox("Cause Déchet", CAUSES_FREQUENTES)
    
    submitted = st.form_submit_button("⚡ Enregistrer")

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
    st.sidebar.success(f"✅ Enregistré !")
    st.rerun()

# ==============================================================================
# 7. FILTRES MULTI-CHANTIERS DYNAMIQUES
# ==============================================================================
df_current = st.session_state.df

st.sidebar.markdown("---")
st.sidebar.header("🔍 Filtres globaux")

if not df_current.empty:
    chantiers_opts = df_current["Chantier"].dropna().unique().tolist()
    filter_chantier = st.sidebar.multiselect("Chantiers", options=chantiers_opts, default=chantiers_opts)
    df_view = df_current[df_current["Chantier"].isin(filter_chantier)]
else:
    df_view = df_current

# ==============================================================================
# 8. PRESENTATION DES RESULTATS & GRAPHIQUES
# ==============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Métriques & KPIs", 
    "📈 Analyse Coûts & Causes", 
    "🌱 Bilan RSE / Tri", 
    "📋 Registre & Export"
])

if df_view.empty:
    st.info("ℹ️ Aucune donnée à analyser. Importez un fichier CSV ou utilisez la saisie manuelle dans la barre latérale.")
else:
    # --- TAB 1: KPIs ---
    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        
        perte_totale = df_view["Cout_Estime"].sum()
        total_lignes = len(df_view)
        revalorises = df_view["Filiere"].isin(["Réemploi sur site", "Recyclage / Filière externe"]).sum()
        taux_reval = (revalorises / total_lignes * 100) if total_lignes > 0 else 0
        total_co2 = df_view["CO2_Impact_kg"].sum()
        
        c1.metric("💸 Coût Total Pertes", f"{perte_totale:,.0f} FCFA")
        c2.metric("📦 Relevés totaux", f"{total_lignes}")
        c3.metric("♻️ Taux Valorisation", f"{taux_reval:.1f} %")
        c4.metric("🌍 Impact Carbone", f"{total_co2:,.1f} kg CO₂")
        
        st.markdown("---")
        g1, g2 = st.columns(2)
        
        with g1:
            fig_pie = px.pie(
                df_view, names="Type", values="Cout_Estime", hole=0.45,
                title="Coûts Financiers par Matériau (FCFA)"
            )
            fig_pie.update_layout(margin=dict(t=40, b=10, l=10, r=10))
            st.plotly_chart(fig_pie, use_container_width=True, config=PLOT_CONFIG)
            
        with g2:
            trend_df = df_view.groupby(["Date", "Type"], as_index=False, observed=True)["Cout_Estime"].sum()
            fig_line = px.line(
                trend_df, x="Date", y="Cout_Estime", color="Type", markers=True,
                title="Évolution Chronologique des Pertes"
            )
            fig_line.update_layout(margin=dict(t=40, b=10, l=10, r=10))
            st.plotly_chart(fig_line, use_container_width=True, config=PLOT_CONFIG)

    # --- TAB 2: CAUSES ---
    with tab2:
        a1, a2 = st.columns(2)
        with a1:
            cause_df = df_view.groupby("Cause", as_index=False, observed=True)["Cout_Estime"].sum().sort_values(by="Cout_Estime", ascending=True)
            fig_bar_cause = px.bar(
                cause_df, x="Cout_Estime", y="Cause", orientation='h',
                color="Cout_Estime", color_continuous_scale="Reds", title="Impact par Cause Racine"
            )
            fig_bar_cause.update_layout(margin=dict(t=40, b=10, l=10, r=10))
            st.plotly_chart(fig_bar_cause, use_container_width=True, config=PLOT_CONFIG)
            
        with a2:
            zone_df = df_view.groupby("Zone", as_index=False, observed=True)["Cout_Estime"].sum()
            fig_zone = px.bar(zone_df, x="Zone", y="Cout_Estime", color="Zone", title="Coûts par Zone / Lot")
            fig_zone.update_layout(margin=dict(t=40, b=10, l=10, r=10))
            st.plotly_chart(fig_zone, use_container_width=True, config=PLOT_CONFIG)

    # --- TAB 3: RSE ---
    with tab3:
        r1, r2 = st.columns(2)
        with r1:
            filiere_df = df_view.groupby("Filiere", as_index=False, observed=True)["Quantite"].sum()
            fig_fil = px.bar(filiere_df, x="Filiere", y="Quantite", color="Filiere", title="Destination des Déchets")
            fig_fil.update_layout(margin=dict(t=40, b=10, l=10, r=10))
            st.plotly_chart(fig_fil, use_container_width=True, config=PLOT_CONFIG)
            
        with r2:
            co2_df = df_view.groupby("Type", as_index=False, observed=True)["CO2_Impact_kg"].sum()
            fig_co2 = px.pie(co2_df, names="Type", values="CO2_Impact_kg", title="Bilan Carbone (kg CO₂eq)")
            fig_co2.update_layout(margin=dict(t=40, b=10, l=10, r=10))
            st.plotly_chart(fig_co2, use_container_width=True, config=PLOT_CONFIG)

    # --- TAB 4: HISTORIQUE ---
    with tab4:
        st.dataframe(df_view.sort_values("Date", ascending=False), use_container_width=True)
        csv_bytes = df_view.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Télécharger le Registre (CSV)",
            data=csv_bytes,
            file_name=f"registre_dechets_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )

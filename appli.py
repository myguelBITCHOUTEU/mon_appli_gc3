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
    page_title="BTP EcoWaste Pro - Ultra Rapide",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration graphique Plotly allégée pour exécution instantanée
PLOT_CONFIG = {
    'displayModeBar': False,
    'responsive': True
}

# ==============================================================================
# 2. MODULE "ANTI-SOMMEIL" (KEEP-ALIVE AUTO-PING THREAD)
# ==============================================================================
# Évite l'endormissement du serveur lors d'inactivité
APP_URL = os.getenv("STREAMLIT_APP_URL", "") # Renseignez l'URL de votre app en variable ou ci-dessous

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

# Lancement du thread Keep-Alive une seule fois au démarrage
if "keep_alive_started" not in st.session_state and APP_URL:
    t = threading.Thread(target=background_keep_alive, args=(APP_URL, 600), daemon=True)
    t.start()
    st.session_state["keep_alive_started"] = True

# ==============================================================================
# 3. RÉFÉRENTIELS BTP EN MÉMOIRE CACHE (0 LATENCE)
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

CHANTIERS_DISPONIBLES = ["Chantier Tour Horizon (GC)", "Chantier Résidence Riviera", "Pont Autoroutier Est"]
ZONES_CHANTIER = ["Zone A - Gros Œuvre", "Zone B - Second Œuvre", "Zone C - Base Vie / Stockage", "Voirie & Réseaux (VRD)"]

# ==============================================================================
# 4. GESTION DU CACHE & PERSISTENCE RAPIDE (IN-MEMORY + ASYNC I/O)
# ==============================================================================
@st.cache_data(show_spinner=False, ttl=3600)
def load_cached_data():
    """Charge les données avec mise en cache mémoire ultra-rapide."""
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(
                DATA_FILE,
                dtype={
                    "Chantier": "category",
                    "Zone": "category",
                    "Type": "category",
                    "Unite": "category",
                    "Filiere": "category",
                    "Cause": "category"
                },
                parse_dates=["Date"]
            )
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=[
        "Chantier", "Zone", "Date", "Type", "Quantite", "Unite", 
        "Cout_Estime", "Filiere", "Cause", "CO2_Impact_kg"
    ])

def save_and_invalidate_cache(df):
    """Enregistre et réactualise instantanément le cache."""
    df.to_csv(DATA_FILE, index=False)
    load_cached_data.clear()

# Initialisation du DataFrame dans le Session State
if "df" not in st.session_state:
    st.session_state.df = load_cached_data()

# ==============================================================================
# 5. BARRE LATÉRALE - SAISIE INSTANTANÉE
# ==============================================================================
st.markdown("""
<style>
    .title-banner { background: linear-gradient(90deg, #1E3A8A, #3B82F6); padding: 16px; border-radius: 8px; color: white; margin-bottom: 20px;}
    .title-banner h2 { margin: 0; font-size: 1.8rem; font-weight: 700; }
    .title-banner p { margin: 0; opacity: 0.9; font-size: 0.9rem; }
    .stMetric { background-color: #F8FAFC; padding: 12px; border-radius: 8px; border: 1px solid #E2E8F0; }
</style>
<div class='title-banner'>
    <h2>⚡ BTP EcoWaste Pro — Suivi Chantier Temps Réel</h2>
    <p>Performances Ultra-Rapides & Système Anti-Mise en Veille</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.header("📝 Saisie Terrain Express")

with st.sidebar.form("form_dechet", clear_on_submit=True):
    c_chantier = st.selectbox("Chantier", CHANTIERS_DISPONIBLES)
    c_zone = st.selectbox("Zone / Lot", ZONES_CHANTIER)
    c_date = st.date_input("Date", date.today())
    c_type = st.selectbox("Matériau", list(REFERENTIEL_MATERIAUX.keys()))
    
    unite = REFERENTIEL_MATERIAUX[c_type]["unite"]
    c_qte = st.number_input(f"Quantité ({unite})", min_value=0.1, step=1.0, value=1.0)
    
    c_filiere = st.selectbox("Filière Traitement", FILIERES_VALORISATION)
    c_cause = st.selectbox("Cause Déchet", CAUSES_FREQUENTES)
    
    submitted = st.form_submit_button("⚡ Valider & Enregistrer")

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
    
    st.session_state.df = pd.concat([st.session_state.df, new_entry], ignore_index=True)
    save_and_invalidate_cache(st.session_state.df)
    st.sidebar.success(f"✅ Enregistré en 1 clic ! Perte : {cout:,.0f} FCFA")

# ==============================================================================
# 6. FILTRAGE EN MÉMOIRE
# ==============================================================================
df_current = st.session_state.df

st.sidebar.markdown("---")
st.sidebar.header("🔍 Filtres d'affichage")

if not df_current.empty:
    chantiers_opts = df_current["Chantier"].dropna().unique().tolist()
    filter_chantier = st.sidebar.multiselect("Chantiers", options=chantiers_opts, default=chantiers_opts)
    
    # Filtrage vectoriel rapide
    df_view = df_current[df_current["Chantier"].isin(filter_chantier)]
else:
    df_view = df_current

# Statut Anti-Sommeil
st.sidebar.markdown("---")
st.sidebar.caption("🟢 **Serveur Actif : Mode Anti-Sommeil activé**")

# ==============================================================================
# 7. TABLEAUX DE BORD HAUTE PERFORMANCE
# ==============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Métriques & KPIs", 
    "📈 Analyse Coûts & Causes", 
    "🌱 Bilan RSE / Tri", 
    "📋 Registre & Export"
])

if df_view.empty:
    st.info("ℹ️ Aucune donnée à afficher. Utilisez le formulaire latéral pour démarrer.")
else:
    # --- TAB 1: KPIs ---
    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        
        perte_totale = df_view["Cout_Estime"].sum()
        total_lignes = len(df_view)
        
        # Calcul vectorisé
        revalorises = df_view["Filiere"].isin(["Réemploi sur site", "Recyclage / Filière externe"]).sum()
        taux_reval = (revalorises / total_lignes * 100) if total_lignes > 0 else 0
        total_co2 = df_view["CO2_Impact_kg"].sum()
        
        c1.metric("💸 Coût Total Pertes", f"{perte_totale:,.0f} FCFA")
        c2.metric("📦 Nombre de Relevés", f"{total_lignes}")
        c3.metric("♻️ Taux Valorisation", f"{taux_reval:.1f} %")
        c4.metric("🌍 Impact Carbone", f"{total_co2:,.1f} kg CO₂")
        
        st.markdown("---")
        g1, g2 = st.columns(2)
        
        with g1:
            fig_pie = px.pie(
                df_view, names="Type", values="Cout_Estime", hole=0.45,
                title="Pertes Financières par Matériau (FCFA)"
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
            "📥 Télécharger le Registre (CSV Instantané)",
            data=csv_bytes,
            file_name=f"registre_dechets_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import date, datetime

# ==============================================================================
# 1. CONFIGURATION DE LA PAGE & STYLES CSS
# ==============================================================================
st.set_page_config(
    page_title="BTP EcoWaste - Gestion & Analyse des Déchets de Chantier",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS pour design moderne professionnel BTP
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        color: #1E3A8A;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 10px;
        padding: 18px;
        border-left: 5px solid #1E3A8A;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .metric-card-green {
        border-left-color: #10B981;
    }
    .metric-card-orange {
        border-left-color: #F59E0B;
    }
    .metric-card-red {
        border-left-color: #EF4444;
    }
    .stButton>button {
        background-color: #1E3A8A;
        color: white;
        border-radius: 6px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. REFERENTIEL BTP DE BASE (MATERIAUX, PRICING & CARBON FOOTPRINT)
# ==============================================================================
DATA_FILE = "dechets_data.csv"

# Référentiel matériaux BTP standard : Prix unitaire (FCFA), Unité par défaut, Émissions de CO2 évitées/engendrées (kg CO2/unité)
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
# 3. FONCTIONS CHARGEMENT ET TRAITEMENT DES DONNEES
# ==============================================================================
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df["Date"] = pd.to_datetime(df["Date"])
        return df
    else:
        # Jeu de données vide par défaut avec la structure complète
        return pd.DataFrame(columns=[
            "Chantier", "Zone", "Date", "Type", "Quantite", "Unite", 
            "Cout_Estime", "Filiere", "Cause", "CO2_Impact_kg"
        ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# Chargement initial
df_raw = load_data()

# ==============================================================================
# 4. EN-TÊTE ET BARRE LATÉRALE (SIDEBAR - SAISIE & FILTRES)
# ==============================================================================
st.markdown("<div class='main-title'>🏗️ BTP EcoWaste : Monitoring & Management des Déchets</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Plateforme d'analyse financière, de traçabilité et d'impact environnemental (ISO 14001 / BREEAM / HQE)</div>", unsafe_allow_html=True)

st.sidebar.header("📝 Saisie de Terrain (Nouveau Déchet)")

with st.sidebar.form("form_dechet", clear_on_submit=True):
    chantier_sel = st.selectbox("Chantier", CHANTIERS_DISPONIBLES)
    zone_sel = st.selectbox("Zone / Lot du chantier", ZONES_CHANTIER)
    date_saisie = st.date_input("Date du constat", date.today())
    type_dechet = st.selectbox("Type de matériau / déchet", list(REFERENTIEL_MATERIAUX.keys()))
    
    unite_defaut = REFERENTIEL_MATERIAUX[type_dechet]["unite"]
    quantite = st.number_input(f"Quantité ({unite_defaut})", min_value=0.1, step=1.0)
    
    filiere = st.selectbox("Destination / Filière de traitement", FILIERES_VALORISATION)
    cause = st.selectbox("Cause principale du déchet", CAUSES_FREQUENTES)
    
    submit_btn = st.form_submit_button("➕ Enregistrer le déchet sur le site")

if submit_btn:
    prix_u = REFERENTIEL_MATERIAUX[type_dechet]["prix"]
    co2_u = REFERENTIEL_MATERIAUX[type_dechet]["co2_facteur"]
    
    cout_total = quantite * prix_u
    impact_co2 = quantite * co2_u
    
    new_data = pd.DataFrame([{
        "Chantier": chantier_sel,
        "Zone": zone_sel,
        "Date": pd.to_datetime(date_saisie),
        "Type": type_dechet,
        "Quantite": quantite,
        "Unite": unite_defaut,
        "Cout_Estime": cout_total,
        "Filiere": filiere,
        "Cause": cause,
        "CO2_Impact_kg": impact_co2
    }])
    
    df_raw = pd.concat([df_raw, new_data], ignore_index=True)
    save_data(df_raw)
    st.sidebar.success(f"✅ Enregistré avec succès ! Perte estimée : {cout_total:,.0f} FCFA")

# ==============================================================================
# 5. FILTRES DYNAMIQUES DE L'INTERFACE
# ==============================================================================
st.sidebar.markdown("---")
st.sidebar.header("🔍 Filtres du Tableau de Bord")

if not df_raw.empty:
    chantiers_filter = st.sidebar.multiselect("Filtrer par Chantier", options=df_raw["Chantier"].unique(), default=df_raw["Chantier"].unique())
    df_filtered = df_raw[df_raw["Chantier"].isin(chantiers_filter)]
else:
    df_filtered = df_raw.copy()

# ==============================================================================
# 6. TABLEAU DE BORD D'ANALYSE (ONGLETS PRINCIPAUX)
# ==============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 KPIs & Indicateurs Clés", 
    "📈 Analyse Financière & Périmètres", 
    "🌱 Empreinte Carbone & Tri (HQE)", 
    "📋 Historique & Exportation"
])

if df_filtered.empty:
    st.info("ℹ️ Aucune donnée enregistrée pour le moment. Remplissez le formulaire dans le panneau latéral pour commencer la collecte.")
else:
    # --------------------------------------------------------------------------
    # TAB 1 : KPIs & INDICATEURS CLÉS
    # --------------------------------------------------------------------------
    with tab1:
        st.subheader("Performance Globale du Chantier")
        
        c1, c2, c3, c4 = st.columns(4)
        
        perte_totale = df_filtered["Cout_Estime"].sum()
        total_entrees = len(df_filtered)
        
        # Calcul du Taux de Valorisation
        val_df = df_filtered[df_filtered["Filiere"].isin(["Réemploi sur site", "Recyclage / Filière externe"])]
        taux_valorisation = (len(val_df) / total_entrees * 100) if total_entrees > 0 else 0
        
        total_co2 = df_filtered["CO2_Impact_kg"].sum()
        
        with c1:
            st.metric("💸 Perte Financière Totale", f"{perte_totale:,.0f} FCFA")
        with c2:
            st.metric("📦 Incidents & Saisies", f"{total_entrees} relevés")
        with c3:
            st.metric("♻️ Taux de Valorisation", f"{taux_valorisation:.1f} %", delta="Objectif HQE > 70%" if taux_valorisation >= 70 else "En dessous de l'objectif")
        with c4:
            st.metric("🌍 Empreinte Carbone Générée", f"{total_co2:,.1f} kg CO₂eq")

        st.markdown("---")
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("##### 🍩 Répartition des Déchets par Type de Matériau")
            fig_pie_type = px.pie(
                df_filtered, names="Type", values="Cout_Estime", hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Bold,
                title="Pertes Financières par Matériau (FCFA)"
            )
            st.plotly_chart(fig_pie_type, use_container_width=True)
            
        with col_g2:
            st.markdown("##### 📈 Évolution Temporelle des Coûts des Pertes")
            df_trend = df_filtered.groupby(["Date", "Type"])["Cout_Estime"].sum().reset_index()
            fig_line = px.line(
                df_trend, x="Date", y="Cout_Estime", color="Type", markers=True,
                title="Tendance des pertes quotidiennes (FCFA)"
            )
            st.plotly_chart(fig_line, use_container_width=True)

    # --------------------------------------------------------------------------
    # TAB 2 : ANALYSE FINANCIÈRE & PÉRIMÈTRES
    # --------------------------------------------------------------------------
    with tab2:
        st.subheader("Analyse par Cause Racine et par Zone de Chantier")
        
        col_a1, col_a2 = st.columns(2)
        
        with col_a1:
            st.markdown("##### 🎯 Coût des Déchets par Cause Origine")
            cause_df = df_filtered.groupby("Cause")["Cout_Estime"].sum().reset_index().sort_values(by="Cout_Estime", ascending=True)
            fig_bar_cause = px.bar(
                cause_df, x="Cout_Estime", y="Cause", orientation='h',
                color="Cout_Estime", color_continuous_scale="Reds",
                labels={"Cout_Estime": "Perte (FCFA)", "Cause": "Cause du déchet"}
            )
            st.plotly_chart(fig_bar_cause, use_container_width=True)
            
        with col_a2:
            st.markdown("##### 📍 Répartition des Coûts par Zone de Chantier")
            zone_df = df_filtered.groupby("Zone")["Cout_Estime"].sum().reset_index()
            fig_bar_zone = px.bar(
                zone_df, x="Zone", y="Cout_Estime", color="Zone",
                title="Pertes accumulées par Zone / Lot"
            )
            st.plotly_chart(fig_bar_zone, use_container_width=True)

    # --------------------------------------------------------------------------
    # TAB 3 : EMPREINTE CARBONE & TRI (HQE/ISO 14001)
    # --------------------------------------------------------------------------
    with tab3:
        st.subheader("Bilan RSE & Filières de Traitement des Déchets")
        
        col_r1, col_r2 = st.columns(2)
        
        with col_r1:
            st.markdown("##### 🚚 Traçabilité selon les Filières d'Élimination")
            filiere_df = df_filtered.groupby("Filiere")["Quantite"].sum().reset_index()
            fig_filiere = px.bar(
                filiere_df, x="Filiere", y="Quantite", color="Filiere",
                title="Volumes gérés par filière de destination",
                color_discrete_map={
                    "Réemploi sur site": "#10B981",
                    "Recyclage / Filière externe": "#3B82F6",
                    "Revalorisation Énergétique": "#F59E0B",
                    "Mise en Décharge / CET (Non Valorisé)": "#EF4444"
                }
            )
            st.plotly_chart(fig_filiere, use_container_width=True)
            
        with col_r2:
            st.markdown("##### 🌱 Carbon Score : Émissions CO₂ associées par Matériau")
            co2_df = df_filtered.groupby("Type")["CO2_Impact_kg"].sum().reset_index()
            fig_co2 = px.pie(
                co2_df, names="Type", values="CO2_Impact_kg",
                title="Bilan Carbonne Généré (kg CO2eq)"
            )
            st.plotly_chart(fig_co2, use_container_width=True)

    # --------------------------------------------------------------------------
    # TAB 4 : HISTORIQUE ET EXPORTATION
    # --------------------------------------------------------------------------
    with tab4:
        st.subheader("Registre Officiel des Déchets de Chantier")
        st.dataframe(df_filtered.sort_values("Date", ascending=False), use_container_width=True)
        
        st.markdown("---")
        col_ex1, col_ex2 = st.columns(2)
        
        with col_ex1:
            # Téléchargement CSV
            csv_data = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Télécharger le Registre Brut (CSV)",
                data=csv_data,
                file_name=f"registre_dechets_btp_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
        with col_ex2:
            st.info("💡 **Conseil BTP :** Conservez ce registre pour vos audits annuels ISO 14001 et les inspections BREEAM / HQE.")

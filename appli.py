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
# ================================================================================
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

# ==============================================================================
# 2. MODULE ANTI-SOMMEIL
# ==============================================================================
APP_URL = os.getenv("STREAMLIT_APP_URL", "")


def background_keep_alive(target_url, interval_sec=600):
    """Effectue un ping HTTP toutes les 10 minutes."""
    while True:
        try:
            if target_url:
                req = urllib.request.Request(
                    target_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 KeepAlive-Bot"
                    }
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
# 3. REFERENTIELS BTP
# ==============================================================================
REFERENTIEL_MATERIAUX = {
    "Béton résiduel": {
        "prix": 75000,
        "unite": "m3",
        "co2_facteur": 240
    },
    "Chutes de fer / Acier": {
        "prix": 800,
        "unite": "kg",
        "co2_facteur": 1.8
    },
    "Bois de coffrage": {
        "prix": 2500,
        "unite": "Planche",
        "co2_facteur": 0.5
    },
    "Parpaings / Agglos cassés": {
        "prix": 500,
        "unite": "Unité (U)",
        "co2_facteur": 1.2
    },
    "Gravats / Remblais": {
        "prix": 10000,
        "unite": "Tonne",
        "co2_facteur": 15
    },
    "Plâtre / Chutes de placo": {
        "prix": 12000,
        "unite": "Tonne",
        "co2_facteur": 120
    },
    "Plastiques & Gainages": {
        "prix": 1500,
        "unite": "kg",
        "co2_facteur": 2.5
    },
    "Cartons & Emballages": {
        "prix": 300,
        "unite": "kg",
        "co2_facteur": 0.9
    },
    "Déchets Dangereux (Peintures/Huiles)": {
        "prix": 5000,
        "unite": "Litre",
        "co2_facteur": 3.0
    }
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
    "Chantier",
    "Zone",
    "Date",
    "Type",
    "Quantite",
    "Unite",
    "Cout_Estime",
    "Filiere",
    "Cause",
    "CO2_Impact_kg"
]

DATA_FILE = "dechets_data.csv"

# ==============================================================================
# 4. CHARGEMENT ET STOCKAGE CSV
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
    """Sauvegarde les données dans le fichier CSV existant."""
    df.to_csv(DATA_FILE, index=False)
    st.session_state.df = df
    load_cached_data.clear()


# ==============================================================================
# 5. AJOUT : DONNEES DE DEMONSTRATION
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

# ==============================================================================
# 6. INTERFACE VISUELLE AMELIOREE
# ==============================================================================
st.markdown(
    """
    <style>
        .stApp {
            background: #f8fafc;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }

        .title-banner {
            background: linear-gradient(135deg, #059669 0%, #1e3a8a 100%);
            padding: 28px 32px;
            border-radius: 18px;
            color: white;
            margin-bottom: 25px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, .16);
        }

        .title-banner h1 {
            margin: 0;
            font-size: 2.1rem;
            font-weight: 800;
            letter-spacing: -.5px;
        }

        .title-banner p {
            margin: 8px 0 0;
            opacity: .92;
            font-size: 1rem;
        }

        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid #e2e8f0;
            padding: 18px;
            border-radius: 14px;
            box-shadow: 0 3px 12px rgba(15, 23, 42, .06);
        }

        div[data-testid="stMetric"] label {
            color: #475569;
            font-weight: 600;
        }

        .stButton > button {
            border-radius: 10px;
            min-height: 42px;
            font-weight: 600;
            border: 1px solid #cbd5e1;
        }

        section[data-testid="stSidebar"] {
            background: #f1f5f9;
        }

        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: #0f172a;
        }

        .data-status {
            background: #ecfdf5;
            border: 1px solid #a7f3d0;
            padding: 10px 14px;
            border-radius: 10px;
            color: #065f46;
            font-size: .9rem;
            margin-bottom: 15px;
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
# 7. OPTIONS AJOUTEES : TEST ET GESTION DES DONNEES
# ==============================================================================
st.sidebar.header("🧪 Données de test")

if st.sidebar.button(
    "📊 Ajouter les données de démonstration",
    use_container_width=True
):
    demo_df = create_demo_data()
    if not st.session_state.df.empty:
        demo_df = pd.concat(
            [st.session_state.df, demo_df],
            ignore_index=True
        )
    save_and_invalidate_cache(demo_df)
    st.sidebar.success("Données de démonstration ajoutées.")
    st.rerun()

if st.sidebar.button(
    "🔄 Remplacer par les données de test",
    use_container_width=True
):
    save_and_invalidate_cache(create_demo_data())
    st.sidebar.success("Jeu de test chargé.")
    st.rerun()

if st.sidebar.button(
    "🗑️ Vider toutes les données",
    use_container_width=True
):
    empty_df = pd.DataFrame(columns=COLONNES_ATTENDUES)
    save_and_invalidate_cache(empty_df)
    st.sidebar.success("Toutes les données ont été supprimées.")
    st.rerun()

st.sidebar.caption(f"💾 Stockage actif : {DATA_FILE}")
st.sidebar.markdown("---")

# ==============================================================================
# 8. BARRE LATERALE - IMPORTATION
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
        required_minimal = [
            "Chantier", "Zone", "Date", "Type", "Quantite"
        ]
        missing_cols = [
            col for col in required_minimal
            if col not in imported_df.columns
        ]

        if missing_cols:
            st.sidebar.error(
                "⚠️ Colonnes requises manquantes : "
                + ", ".join(missing_cols)
            )
        else:
            imported_df["Date"] = pd.to_datetime(
                imported_df["Date"], errors="coerce"
            )
            imported_df["Quantite"] = pd.to_numeric(
                imported_df["Quantite"], errors="coerce"
            ).fillna(0)

            if "Unite" not in imported_df.columns:
                imported_df["Unite"] = imported_df["Type"].map(
                    lambda x: REFERENTIEL_MATERIAUX.get(
                        x, {}
                    ).get("unite", "U")
                )

            if "Cout_Estime" not in imported_df.columns:
                imported_df["Cout_Estime"] = imported_df.apply(
                    lambda row: row["Quantite"] *
                    REFERENTIEL_MATERIAUX.get(
                        row["Type"], {}
                    ).get("prix", 0),
                    axis=1
                )

            if "CO2_Impact_kg" not in imported_df.columns:
                imported_df["CO2_Impact_kg"] = imported_df.apply(
                    lambda row: row["Quantite"] *
                    REFERENTIEL_MATERIAUX.get(
                        row["Type"], {}
                    ).get("co2_facteur", 0),
                    axis=1
                )

            for col in ["Filiere", "Cause"]:
                if col not in imported_df.columns:
                    imported_df[col] = "Non spécifié"

            imported_cleaned = imported_df[COLONNES_ATTENDUES]
            st.sidebar.success(
                f"🔍 Fichier valide ({len(imported_cleaned)} lignes)"
            )

            col_b1, col_b2 = st.sidebar.columns(2)

            if col_b1.button("➕ Fusionner"):
                df_merged = pd.concat(
                    [st.session_state.df, imported_cleaned],
                    ignore_index=True
                )
                save_and_invalidate_cache(df_merged)
                st.sidebar.success("Données fusionnées avec succès !")
                st.rerun()

            if col_b2.button("🗑️ Remplacer"):
                save_and_invalidate_cache(imported_cleaned)
                st.sidebar.success("Base de données remplacée !")
                st.rerun()

    except Exception as error:
        st.sidebar.error(f"Erreur d'importation : {error}")

# ==============================================================================
# 9. SAISIE MANUELLE
# ==============================================================================
st.sidebar.markdown("---")
st.sidebar.header("📝 Saisie manuelle rapide")

with st.sidebar.form("form_dechet", clear_on_submit=True):
    c_chantier = st.selectbox(
        "Chantier",
        CHANTIERS_DISPONIBLES
    )
    c_zone = st.selectbox(
        "Zone / Lot",
        ZONES_CHANTIER
    )
    c_date = st.date_input(
        "Date",
        date.today()
    )
    c_type = st.selectbox(
        "Matériau",
        list(REFERENTIEL_MATERIAUX.keys())
    )

    unite = REFERENTIEL_MATERIAUX[c_type]["unite"]
    c_qte = st.number_input(
        f"Quantité ({unite})",
        min_value=0.1,
        step=1.0,
        value=1.0
    )
    c_filiere = st.selectbox(
        "Filière de traitement",
        FILIERES_VALORISATION
    )
    c_cause = st.selectbox(
        "Cause du déchet",
        CAUSES_FREQUENTES
    )
    submitted = st.form_submit_button(
        "⚡ Enregistrer",
        use_container_width=True
    )

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

    df_new = pd.concat(
        [st.session_state.df, new_entry],
        ignore_index=True
    )
    save_and_invalidate_cache(df_new)
    st.sidebar.success("✅ Déchet enregistré et sauvegardé !")
    st.rerun()

# ==============================================================================
# 10. FILTRES GLOBAUX
# ==============================================================================
df_current = st.session_state.df

st.sidebar.markdown("---")
st.sidebar.header("🔍 Filtres globaux")

if not df_current.empty:
    chantiers_opts = (
        df_current["Chantier"]
        .dropna()
        .unique()
        .tolist()
    )
    filter_chantier = st.sidebar.multiselect(
        "Chantiers",
        options=chantiers_opts,
        default=chantiers_opts
    )
    df_view = df_current[
        df_current["Chantier"].isin(filter_chantier)
    ]
else:
    df_view = df_current

st.markdown(
    f'<div class="data-status">💾 {len(df_current)} '
    f'enregistrement(s) conservé(s) dans <b>{DATA_FILE}</b></div>',
    unsafe_allow_html=True
)

# ==============================================================================
# 11. RESULTATS ET GRAPHIQUES
# ==============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Métriques & KPIs",
    "📈 Analyse Coûts & Causes",
    "🌱 Bilan RSE / Tri",
    "📋 Registre & Export"
])

if df_view.empty:
    st.info(
        "ℹ️ Aucune donnée à analyser. Utilisez les données de démonstration, "
        "importez un fichier CSV ou saisissez un déchet."
    )
else:
    # --------------------------------------------------------------------------
    # TAB 1 : KPIs
    # --------------------------------------------------------------------------
    with tab1:
        c1, c2, c3, c4 = st.columns(4)

        perte_totale = df_view["Cout_Estime"].sum()
        total_lignes = len(df_view)
        revalorises = df_view["Filiere"].isin([
            "Réemploi sur site",
            "Recyclage / Filière externe"
        ]).sum()
        taux_reval = (
            revalorises / total_lignes * 100
            if total_lignes > 0 else 0
        )
        total_co2 = df_view["CO2_Impact_kg"].sum()

        c1.metric(
            "💸 Coût total des pertes",
            f"{perte_totale:,.0f} FCFA"
        )
        c2.metric(
            "📦 Relevés totaux",
            f"{total_lignes}"
        )
        c3.metric(
            "♻️ Taux de valorisation",
            f"{taux_reval:.1f} %"
        )
        c4.metric(
            "🌍 Impact carbone",
            f"{total_co2:,.1f} kg CO₂"
        )

        st.markdown("---")
        g1, g2 = st.columns(2)

        with g1:
            fig_pie = px.pie(
                df_view,
                names="Type",
                values="Cout_Estime",
                hole=0.45,
                title="Coûts financiers par matériau (FCFA)"
            )
            fig_pie.update_layout(
                margin=dict(t=50, b=10, l=10, r=10),
                legend_title_text="Matériau"
            )
            st.plotly_chart(
                fig_pie,
                use_container_width=True,
                config=PLOT_CONFIG
            )

        with g2:
            trend_df = (
                df_view
                .groupby(["Date", "Type"], as_index=False,
                         observed=True)["Cout_Estime"]
                .sum()
            )
            fig_line = px.line(
                trend_df,
                x="Date",
                y="Cout_Estime",
                color="Type",
                markers=True,
                title="Évolution chronologique des pertes"
            )
            fig_line.update_layout(
                margin=dict(t=50, b=10, l=10, r=10),
                yaxis_title="Coût estimé (FCFA)"
            )
            st.plotly_chart(
                fig_line,
                use_container_width=True,
                config=PLOT_CONFIG
            )

    # --------------------------------------------------------------------------
    # TAB 2 : CAUSES
    # --------------------------------------------------------------------------
    with tab2:
        a1, a2 = st.columns(2)

        with a1:
            cause_df = (
                df_view
                .groupby("Cause", as_index=False, observed=True)["Cout_Estime"]
                .sum()
                .sort_values(by="Cout_Estime", ascending=True)
            )
            fig_bar_cause = px.bar(
                cause_df,
                x="Cout_Estime",
                y="Cause",
                orientation="h",
                color="Cout_Estime",
                color_continuous_scale="Reds",
                title="Impact par cause racine"
            )
            fig_bar_cause.update_layout(
                margin=dict(t=50, b=10, l=10, r=10),
                xaxis_title="Coût estimé (FCFA)"
            )
            st.plotly_chart(
                fig_bar_cause,
                use_container_width=True,
                config=PLOT_CONFIG
            )

        with a2:
            zone_df = (
                df_view
                .groupby("Zone", as_index=False, observed=True)["Cout_Estime"]
                .sum()
            )
            fig_zone = px.bar(
                zone_df,
                x="Zone",
                y="Cout_Estime",
                color="Zone",
                title="Coûts par zone / lot"
            )
            fig_zone.update_layout(
                margin=dict(t=50, b=10, l=10, r=10),
                yaxis_title="Coût estimé (FCFA)"
            )
            st.plotly_chart(
                fig_zone,
                use_container_width=True,
                config=PLOT_CONFIG
            )

    # --------------------------------------------------------------------------
    # TAB 3 : RSE
    # --------------------------------------------------------------------------
    with tab3:
        r1, r2 = st.columns(2)

        with r1:
            filiere_df = (
                df_view
                .groupby("Filiere", as_index=False, observed=True)["Quantite"]
                .sum()
            )
            fig_fil = px.bar(
                filiere_df,
                x="Filiere",
                y="Quantite",
                color="Filiere",
                title="Destination des déchets"
            )
            fig_fil.update_layout(
                margin=dict(t=50, b=10, l=10, r=10),
                yaxis_title="Quantité"
            )
            st.plotly_chart(
                fig_fil,
                use_container_width=True,
                config=PLOT_CONFIG
            )

        with r2:
            co2_df = (
                df_view
                .groupby("Type", as_index=False, observed=True)["CO2_Impact_kg"]
                .sum()
            )
            fig_co2 = px.pie(
                co2_df,
                names="Type",
                values="CO2_Impact_kg",
                title="Bilan carbone (kg CO₂eq)"
            )
            fig_co2.update_layout(
                margin=dict(t=50, b=10, l=10, r=10)
            )
            st.plotly_chart(
                fig_co2,
                use_container_width=True,
                config=PLOT_CONFIG
            )

    # --------------------------------------------------------------------------
    # TAB 4 : REGISTRE ET EXPORT
    # --------------------------------------------------------------------------
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
            file_name=(
                f"registre_dechets_"
                f"{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            ),
            mime="text/csv",
            use_container_width=True
        )

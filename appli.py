import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import date

# ----------------- configuration de la page -------------------

st.set_page_config(page_title="GESTION FINANCIERE DECHETS",layout="wide")

# ----------------- fichier de stockage des donnees ----------------

DATA_FILE="dechets_data.csv"

# ---------------- Dictionnaire des prix unitaires moyens ---------------------

PRIX_UNITAIRES={
	"parpaings casses":500, # fcfa par parpaing
        "chutes de fer":800, # fcfa par kg
        "beton residuel":75000, # fcfa par m^3
        "bois de coffrage": 2500, # fcfa par planche
        "gravats":10000, # fcfa par tonne
}

# ---------------fonction pour charger les donnees -----------------

def load_data():
	if os.path.exists(DATA_FILE):
		return pd.read_csv(DATA_FILE)
	return pd.DataFrame(columns=["Date","Type","quantite","unite","cout_Estime","cause"])

# ----------------- interface utilisateur ---------------------

st.title(" ANALYSE FINANCIERE DES DECHETS DE CHANTIER ")

# --------------- COLLECTE DES DONNEES ---------------

st.sidebar.header("Enregistrement")
with st.sidebar.form("form_dechet"):
	date_saisie=st.date_input("Date",date.today())
	type_dechet=st.selectbox("Type",list(PRIX_UNITAIRES.keys()))
	quantite=st.number_input("Quantite",min_value=0.0,step=1.0)
	cause=st.text_input("cause")
	unite=st.selectbox("Unite",["Unite (U)","kg","m3","Tonne"])

	submit=st.form_submit_button("calculer et enregistrer le dechet")

if submit:
	cout= quantite*PRIX_UNITAIRES[type_dechet]
	new_row=pd.DataFrame([[date_saisie,type_dechet,quantite,unite,cout,cause]],
										columns=["Date","type","Quantite","unite","Cout_Estime","Cause"])
	df=load_data()
	df=pd.concat([df,new_row],ignore_index=True)
	df.to_csv(DATA_FILE,index=False)
	st.sidebar.success(f"Perte enregistree : {cout} FCFA")

#------------------- ANALYSE DES DONNEES ----------------

df=load_data()
if not df.empty:

	col1,col2=st.columns(2)
	total_perte=df["Cout_Estime"].sum()
	st.metric("PERTE FINANCIERE TOTALE", f"{total_perte:,.0f} FCFA")
	
	with col1:
		st.subheader("Repartition des dechets par type")
		fig_pie=px.pie(df,names="Types",values="Quantite",hole=0.3)
		fig_cout = px.bar(df,x="Type",y="Cout_Estime",color="Type",title="cout par categorie")
		st.plotly_chart(fig_pie,use_container_width=True)
		st.plotly_chart(fig_cout)
	with col2:
		st.subheader("Evolution temporelle")
		df["Date"]=pd.to_datetime(df["Date"])
		fig_line=px.line(df.sort_values("Date"),x="Date",y="Quantite",color="Type")
		fig_pie=px.pie(df,names="Type",values="Cout_Estime",title="Repartition de la perte (%)")
		st.plotly_chart(fig_line,use_container_width=True)
		st.plotly_chart(fig_pie)

	st.subheader(" Tableau detaille ")
	st.dataframe(df,use_container_width=True)
	
	#------------------- Bouton de telechargement ---------------------

	csv=df.to_csv(index=False).encode("utf-8")
	st.download_button("Telecharger le rapport CSV",csv,"rapport_chantier.csv","text/csv")
else:
	st.info("Aucune donnee disponible. Utilisez le formulaire a gauche pour commencer.")
	
		
	


	


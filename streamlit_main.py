import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

# Google Sheets autentifikácia (cez secrets)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Názov spreadsheetu a hárku
SHEET_NAME = "ChatBot_Obklady_MR"
FORMATY_SHEET = "formaty"

# Načítanie dát z formátov
@st.cache_data
def nacitaj_formaty():
    sheet = client.open(SHEET_NAME).worksheet(FORMATY_SHEET)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    return df

# Hlavný program
def main():
    st.title("🧱 Výber obkladu a dlažby – krok 1")

    df_formaty = nacitaj_formaty()

    # Výber dekoru
    dekor = st.selectbox("Vyberte dekor:", sorted(df_formaty["dekor"].unique()))

    if dekor:
        df_filtered = df_formaty[df_formaty["dekor"] == dekor]
        kolekcia = st.selectbox("Vyberte kolekciu:", sorted(df_filtered["kolekcia"].unique()))

        if kolekcia:
            st.success(f"Vybrali ste dekor **{dekor}** a kolekciu **{kolekcia}**.")
            st.info("Pokračovanie: výber série pripravujeme.")

if __name__ == "__main__":
    main()

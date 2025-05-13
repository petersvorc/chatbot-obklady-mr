import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import datetime

# Google Sheets autentifikácia
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Názvy hárkov
SHEET_NAME = "ChatBot_Obklady_MR"
FORMATY_SHEET = "formaty"
CENNIK_SHEET = "cennik"
SLUZBY_SHEET = "sluzby"
DOPYT_SHEET = "dopyt"

# Načítanie dát
@st.cache_data
def nacitaj_data(sheet_name):
    sheet = client.open(SHEET_NAME).worksheet(sheet_name)
    data = sheet.get_all_records()
    return pd.DataFrame(data)

df_formaty = nacitaj_data(FORMATY_SHEET)
df_cennik = nacitaj_data(CENNIK_SHEET)
df_sluzby = nacitaj_data(SLUZBY_SHEET)

# Funkcia na výpočet ceny dlažby
def vypocitaj_cenu_dlazby(param, mnozstvo):
    filtr = df_cennik[df_cennik["rozmer + hrúbka + povrch"] == param]
    if mnozstvo <= 20:
        cena_za_m2 = filtr.iloc[0]["21-59 m2"]
        doprava = filtr.iloc[0]["transportná paleta"] + filtr.iloc[0]["doprava"]
        celkova_cena = round(cena_za_m2 * mnozstvo + doprava)
    elif 21 <= mnozstvo <= 59:
        cena_za_m2 = filtr.iloc[0]["21-59 m2"]
        celkova_cena = round(cena_za_m2 * mnozstvo)
    elif 60 <= mnozstvo <= 120:
        cena_za_m2 = filtr.iloc[0]["60-120 m2"]
        celkova_cena = round(cena_za_m2 * mnozstvo)
    else:  # nad 121 m2
        cena_za_m2 = filtr.iloc[0]["60-120 m2"]
        celkova_cena = round(cena_za_m2 * mnozstvo)
    return celkova_cena, mnozstvo

# Funkcia na výpočet ceny služieb
def vypocitaj_cenu_sluzieb(sluzby):
    cena = 0
    for sluzba in sluzby:
        cena += df_sluzby[df_sluzby["sluzba"] == sluzba]["cena"].values[0]
    return round(cena)

# Hlavná aplikácia
def main():
    st.title("🧱 Konfigurátor obkladov a služieb")

    # Výber dekoru
    dekor = st.selectbox("Vyberte dekor:", sorted(df_formaty["dekor"].unique()))
    df_kolekcie = df_formaty[df_formaty["dekor"] == dekor]

    # Výber kolekcie
    kolekcia = st.selectbox("Vyberte kolekciu:", sorted(df_kolekcie["kolekcia"].unique()))
    df_serie = df_kolekcie[df_kolekcie["kolekcia"] == kolekcia]

    # Výber série
    seria = st.selectbox("Vyberte sériu:", sorted(df_serie["séria"].unique()))
    df_rozmery = df_serie[df_serie["séria"] == seria]

    # Výber rozmeru + hrúbka + povrch
    param = st.selectbox("Vyberte formát + povrch:", sorted(df_rozmery["rozmer + hrúbka + povrch"].unique()))

    # Zadanie množstva
    mnozstvo = st.number_input("Zadajte množstvo v m²:", min_value=1, step=1)

    # Výber služieb
    vybrane_sluzby = st.multiselect("Vyberte doplnkové služby:", sorted(df_sluzby["sluzba"].unique()))

    # Zadanie e-mailu a miesta dodania
    email = st.text_input("Zadajte váš e-mail:")
    miesto = st.text_input("Zadajte miesto dodania:")

    if st.button("Odoslať dopyt"):
        cena_dlazby, mnozstvo_zaznam = vypocitaj_cenu_dlazby(param, mnozstvo)
        cena_sluzieb = vypocitaj_cenu_sluzieb(vybrane_sluzby)
        celkova_cena = cena_dlazby + cena_sluzieb

        # Súhrn položiek
        suhrn = f"Dekor: {dekor}, Kolekcia: {kolekcia}, Séria: {seria}, Rozmer: {param}, Množstvo: {mnozstvo} m²"
        if vybrane_sluzby:
            suhrn += ", Služby: " + ", ".join(vybrane_sluzby)

        # Poznámka pri individuálnej zľave
        if mnozstvo > 121:
            suhrn += " (Cena bude individuálne upravená)"

        # Zápis do Google Sheets
        sheet = client.open(SHEET_NAME).worksheet(DOPYT_SHEET)
        datum = datetime.datetime.now().strftime("%Y-%m-%d")
        id_zaujemcu = f"zaujemca_{int(datetime.datetime.now().timestamp())}"

        novy_zaznam = [datum, id_zaujemcu, email, miesto, dekor, df_rozmery.iloc[0]["značka"], kolekcia, seria, param, mnozstvo, celkova_cena, suhrn]
        sheet.append_row(novy_zaznam)

        st.success("Dopyt bol úspešne odoslaný! Ďakujeme.")

if __name__ == "__main__":
    main()

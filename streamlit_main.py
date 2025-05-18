import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import uuid
import json
import os

# Autentifikácia ku Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Načítanie hárkov
sheet = client.open("ChatBot_Obklady_MR")
df_formaty = pd.DataFrame(sheet.worksheet("formaty").get_all_records())
df_cennik = pd.DataFrame(sheet.worksheet("cennik").get_all_records())
df_doprava = pd.DataFrame(sheet.worksheet("doprava").get_all_records())
dopyt_ws = sheet.worksheet("dopyt")

# Funkcia pre výpočet ceny
def vypocitaj_cenu_dlazby(param, mnozstvo):
    filtr = df_cennik[df_cennik["rozmer + hrúbka + povrch"] == param]
    if filtr.empty:
        return None, None

    if mnozstvo <= 20:
        cena_za_m2 = filtr.iloc[0]["21-59 m2"]
        doprava_r = df_doprava[df_doprava["polozka"].str.lower() == "doprava"]
        doprava_val = float(doprava_r["cena"].values[0]) if not doprava_r.empty else 0
        celkova_cena = round(cena_za_m2 * mnozstvo + doprava_val)
    elif 21 <= mnozstvo <= 59:
        cena_za_m2 = filtr.iloc[0]["21-59 m2"]
        celkova_cena = round(cena_za_m2 * mnozstvo)
    elif 60 <= mnozstvo <= 120:
        cena_za_m2 = filtr.iloc[0]["60-120 m2"]
        celkova_cena = round(cena_za_m2 * mnozstvo)
    else:
        cena_za_m2 = filtr.iloc[0]["60-120 m2"]
        celkova_cena = round(cena_za_m2 * mnozstvo)
        return celkova_cena, "individuálna zľava"

    return celkova_cena, None

# Streamlit formulár
st.title("Výber dlažby a cenová ponuka")

dekor = st.selectbox("Vyberte dekor:", sorted(df_formaty["dekor"].unique()))
kolekcie = df_formaty[df_formaty["dekor"] == dekor]["kolekcia"].unique()
kolekcia = st.selectbox("Vyberte kolekciu:", sorted(kolekcie))
serie = df_formaty[(df_formaty["dekor"] == dekor) & (df_formaty["kolekcia"] == kolekcia)]["séria"].unique()
seria = st.selectbox("Vyberte sériu:", sorted(serie))
param = st.selectbox("Vyberte formát + povrch:", sorted(df_formaty[(df_formaty["dekor"] == dekor) & (df_formaty["kolekcia"] == kolekcia) & (df_formaty["séria"] == seria)]["rozmer + hrúbka + povrch"].unique()))
mnozstvo = st.number_input("Požadované množstvo (m²):", min_value=1, step=1)

miesto = st.text_input("Miesto dodania:")
email = st.text_input("Emailová adresa:")

if st.button("✅ Odoslať dopyt"):
    cena, zlava = vypocitaj_cenu_dlazby(param, mnozstvo)

    if cena is None:
        st.error("Pre tento výber nemáme cenu v cenníku.")
    else:
        znacka = df_formaty[
            (df_formaty["dekor"] == dekor) &
            (df_formaty["kolekcia"] == kolekcia) &
            (df_formaty["séria"] == seria)
        ]["značka"].values[0]

        id_zaujemcu = str(uuid.uuid4())[:8]
        datum = datetime.now().strftime("%Y-%m-%d %H:%M")
        suhrn = f"{dekor}, {kolekcia}, {seria}, {param} = {mnozstvo} m²"

        dopyt_ws.append_row([
            datum,
            id_zaujemcu,
            email,
            miesto,
            dekor,
            znacka,
            kolekcia,
            seria,
            param,
            mnozstvo,
            f"{cena} €" + (f" ({zlava})" if zlava else ""),
            suhrn
        ])

        st.success("✅ Dopyt bol úspešne odoslaný.")
        st.balloons()

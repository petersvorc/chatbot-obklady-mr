import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import datetime
import random
import string
import json
import os

# Autentifikácia cez Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Názvy sheetov
sheet = client.open("ChatBot_Obklady_MR")
df_formaty = pd.DataFrame(sheet.worksheet("formaty").get_all_records())
df_cennik = pd.DataFrame(sheet.worksheet("cennik").get_all_records())
df_doprava = pd.DataFrame(sheet.worksheet("doprava").get_all_records())
df_sluzby = pd.DataFrame(sheet.worksheet("sluzby").get_all_records())
worksheet_dopyt = sheet.worksheet("dopyt")

# Funkcia na výpočet ceny dlažby
def vypocitaj_cenu_dlazby(param, mnozstvo):
    filtr = df_cennik[df_cennik["rozmer + hrúbka + povrch"] == param]
    if filtr.empty:
        return None
    if mnozstvo <= 20:
        cena_za_m2 = filtr.iloc[0]["21-59 m2"]
        doprava = ziskaj_dopravu()
        celkova_cena = round(cena_za_m2 * mnozstvo + doprava)
    elif 21 <= mnozstvo <= 59:
        cena_za_m2 = filtr.iloc[0]["21-59 m2"]
        celkova_cena = round(cena_za_m2 * mnozstvo)
    elif 60 <= mnozstvo <= 120:
        cena_za_m2 = filtr.iloc[0]["60-120 m2"]
        celkova_cena = round(cena_za_m2 * mnozstvo)
    else:
        celkova_cena = None
    return celkova_cena

# Funkcia na výpočet ceny dopravy
def ziskaj_dopravu():
    riadok = df_doprava[df_doprava["polozka"].str.lower() == "doprava"]
    try:
        return float(riadok["cena"].values[0])
    except:
        return 0

# Funkcia na vygenerovanie ID záujemcu
def generate_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Inicializácia session state
if "polozky" not in st.session_state:
    st.session_state["polozky"] = []

# Výber dlažby
st.header("Vyberte si dlažbu")

dekor = st.selectbox("Vyberte dekor:", sorted(df_formaty["dekor"].unique()))
df_dekor = df_formaty[df_formaty["dekor"] == dekor]

kolekcia = st.selectbox("Vyberte kolekciu:", sorted(df_dekor["kolekcia"].unique()))
df_kolekcia = df_dekor[df_dekor["kolekcia"] == kolekcia]

seria = st.selectbox("Vyberte sériu:", sorted(df_kolekcia["séria"].unique()))
df_seria = df_kolekcia[df_kolekcia["séria"] == seria]

param = st.selectbox("Vyberte formát + povrch:", sorted(df_seria["rozmer + hrúbka + povrch"].unique()))
mnozstvo = st.number_input("Množstvo (m²):", min_value=1, step=1)

if st.button("✅ Pridať túto dlažbu"):
    cena = vypocitaj_cenu_dlazby(param, mnozstvo)
    if cena is None:
        st.error("Pre tento výber nemáme cenu v cenníku.")
    else:
        znacka = df_seria.iloc[0]["značka"]
        polozka = {
            "dekor": dekor,
            "značka": znacka,
            "kolekcia": kolekcia,
            "séria": seria,
            "rozmer + hrúbka + povrch": param,
            "množstvo": mnozstvo,
            "cena": cena
        }
        st.session_state["polozky"].append(polozka)
        st.success("Dlažba bola pridaná.")

if st.session_state["polozky"]:
    st.subheader("Súhrn vášho výberu:")
    for idx, p in enumerate(st.session_state["polozky"]):
        st.write(f"{idx+1}. {p['dekor']} | {p['kolekcia']} | {p['séria']} | {p['rozmer + hrúbka + povrch']} | {p['množstvo']} m² | {p['cena']} €")

    st.subheader("Zadajte kontaktné údaje")
    email = st.text_input("Emailová adresa:")
    miesto = st.text_input("Miesto dodania:")

    if st.button("📨 Odoslať dopyt"):
        if not email or not miesto:
            st.error("Zadajte email aj miesto dodania.")
        else:
            today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            id_zaujemcu = generate_id()

            for p in st.session_state["polozky"]:
                worksheet_dopyt.append_row([
                    today,
                    id_zaujemcu,
                    email,
                    miesto,
                    p["dekor"],
                    p["značka"],
                    p["kolekcia"],
                    p["séria"],
                    p["rozmer + hrúbka + povrch"],
                    p["množstvo"],
                    p["cena"],
                    f"{p['dekor']} | {p['kolekcia']} | {p['séria']} | {p['rozmer + hrúbka + povrch']} | {p['množstvo']} m²"
                ])

            st.success("Dopyt bol úspešne odoslaný.")
            st.session_state["polozky"] = []

import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random
import json
import os

# Google Sheets auth
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Nacitanie dat
sheet = client.open("ChatBot_Obklady_MR")
df_formaty = pd.DataFrame(sheet.worksheet("formaty").get_all_records())
df_cennik = pd.DataFrame(sheet.worksheet("cennik").get_all_records())
df_doprava = pd.DataFrame(sheet.worksheet("doprava").get_all_records())
df_sluzby = pd.DataFrame(sheet.worksheet("sluzby").get_all_records())
ws_dopyt = sheet.worksheet("dopyt")

# Funkcia na výpočet ceny dlažby
def vypocitaj_cenu_dlazby(param, mnozstvo, celkove_mnozstvo):
    filtr = df_cennik[df_cennik["rozmery (mm) a povrch"] == param]
    if filtr.empty:
        return None, None
    if celkove_mnozstvo <= 20:
        cena_za_m2 = filtr.iloc[0]["21-59 m2"]
        doprava_riadok = df_doprava[df_doprava["polozka"].str.lower() == "doprava"]
        doprava = float(doprava_riadok["cena"].values[0]) if not doprava_riadok.empty else 0
        celkova_cena = round(cena_za_m2 * mnozstvo + doprava)
    elif 21 <= celkove_mnozstvo <= 59:
        cena_za_m2 = filtr.iloc[0]["21-59 m2"]
        celkova_cena = round(cena_za_m2 * mnozstvo)
    elif 60 <= celkove_mnozstvo <= 120:
        cena_za_m2 = filtr.iloc[0]["60-120 m2"]
        celkova_cena = round(cena_za_m2 * mnozstvo)
    else:
        cena_za_m2 = filtr.iloc[0]["60-120 m2"]
        celkova_cena = round(cena_za_m2 * mnozstvo)
    return cena_za_m2, celkova_cena

# Inicializácia session state
if "polozky" not in st.session_state:
    st.session_state["polozky"] = []
if "sluzby" not in st.session_state:
    st.session_state["sluzby"] = []

st.title("Vyberte si dlažbu")

# Výber dlažby
dekor = st.selectbox("Vyberte dekor:", sorted(df_formaty["dekor"].unique()))
df_filtered = df_formaty[df_formaty["dekor"] == dekor]
kolekcia = st.selectbox("Vyberte kolekciu:", sorted(df_filtered["kolekcia"].unique()))
df_filtered = df_filtered[df_filtered["kolekcia"] == kolekcia]
seria = st.selectbox("Vyberte sériu:", sorted(df_filtered["séria"].unique()))
df_filtered = df_filtered[df_filtered["séria"] == seria]
param = st.selectbox("Vyberte rozmer + povrch:", sorted(df_filtered["rozmery (mm) a povrch"].unique()))
mnozstvo = st.number_input("Množstvo (m²):", min_value=1, step=1)

if st.button("✅ Pridať túto dlažbu"):
    st.session_state["polozky"].append({
        "dekor": dekor,
        "kolekcia": kolekcia,
        "séria": seria,
        "param": param,
        "mnozstvo": mnozstvo
    })
    st.success("Dlažba bola pridaná")

# Súhrn výberu
if st.session_state["polozky"]:
    st.subheader("Súhrn výberu dlažby")
    celkove_mnozstvo = sum([p["mnozstvo"] for p in st.session_state["polozky"]])
    for i, pol in enumerate(st.session_state["polozky"], 1):
        cena_m2, cena_spolu = vypocitaj_cenu_dlazby(pol["param"], pol["mnozstvo"], celkove_mnozstvo)
        if cena_m2 is not None:
            st.markdown(f"**Výber {i}:** {pol['param']} | Množstvo: {pol['mnozstvo']} m² | Cena za m²: {cena_m2} € | Cena spolu: {cena_spolu} €")
        else:
            st.error(f"Pre výber {i} nie je cena dostupná.")

    # Výber doplnkovej služby
    st.subheader("Servis dizajnéra")
    vybrane_sluzby = st.multiselect("Doplnkové služby:", df_sluzby["sluzba"].tolist())
    cena_sluzieb = sum(df_sluzby[df_sluzby["sluzba"] == s]["cena"].values[0] for s in vybrane_sluzby)
    st.write(f"**Cena služieb spolu:** {cena_sluzieb} €")

    # Kontaktné údaje
    st.subheader("Záver")
    miesto_dodania = st.text_input("Miesto dodania")
    email = st.text_input("Emailová adresa (povinné)", placeholder="vas@email.sk")

    if st.button("📨 Odoslať dopyt"):
        if not email:
            st.error("Zadajte e-mailovú adresu.")
        else:
            for pol in st.session_state["polozky"]:
                cena_m2, cena_spolu = vypocitaj_cenu_dlazby(pol["param"], pol["mnozstvo"], celkove_mnozstvo)
                ws_dopyt.append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    random.randint(100000, 999999),
                    email,
                    miesto_dodania,
                    pol["dekor"],
                    "",  # značka – zatiaľ prázdna
                    pol["kolekcia"],
                    pol["séria"],
                    pol["param"],
                    pol["mnozstvo"],
                    cena_spolu,
                    f"{pol['param']} | {pol['mnozstvo']} m² | {cena_spolu} €"
                ])
            st.success("Dopyt bol úspešne odoslaný.")
            st.session_state["polozky"] = []

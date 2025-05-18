import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import datetime
import json
import os

# ------------------- Autentifikácia -------------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# ------------------- Načítanie sheetov -------------------
sheet = client.open("ChatBot_Obklady_MR")
df_cennik = pd.DataFrame(sheet.worksheet("cennik").get_all_records())
df_doprava = pd.DataFrame(sheet.worksheet("doprava").get_all_records())
df_sluzby = pd.DataFrame(sheet.worksheet("sluzby").get_all_records())
worksheet_dopyt = sheet.worksheet("dopyt")

# ------------------- Inicializácia session state -------------------
if "vybrane_dlazby" not in st.session_state:
    st.session_state["vybrane_dlazby"] = []
if "sluzby" not in st.session_state:
    st.session_state["sluzby"] = []

# ------------------- Výpočet ceny -------------------
def vypocitaj_cenu(param, mnozstvo, celkove_mnozstvo):
    riadok = df_cennik[df_cennik["rozmer + hrúbka + povrch"] == param]
    if riadok.empty:
        return None, None, None, None
    doprava = 0
    doprava_text = None
    if celkove_mnozstvo <= 20:
        cena_m2 = riadok.iloc[0]["21-59 m2"]
        doprava_riadok = df_doprava[df_doprava["polozka"].str.lower() == "doprava do 20 m²"]
        if not doprava_riadok.empty:
            doprava = float(doprava_riadok["cena"].values[0])
            doprava_text = f"Pre objednávky do 20 m² účtujeme dopravu: {doprava} €"
        cena = round(cena_m2 * mnozstvo + doprava)
        poznamka = None
    elif 21 <= celkove_mnozstvo <= 59:
        cena_m2 = riadok.iloc[0]["21-59 m2"]
        cena = round(cena_m2 * mnozstvo)
        poznamka = None
    elif 60 <= celkove_mnozstvo <= 120:
        cena_m2 = riadok.iloc[0]["60-120 m2"]
        cena = round(cena_m2 * mnozstvo)
        poznamka = None
    else:
        cena_m2 = riadok.iloc[0]["60-120 m2"]
        cena = round(cena_m2 * mnozstvo)
        poznamka = "Pri množstve dlažby nad 121 m2 je pravdepodobne priestor pre zľavu. Odošlite formulár alebo nás priamo kontaktujte."
    return cena_m2, cena, poznamka, doprava_text

# ------------------- Formulár -------------------
st.header("Overte si parametre našich dlažieb a orientačné ceny.")
st.write("Na cenu majú vplyv rozmery, povrch a množstvo dlažby.")

param = st.selectbox("Vyberte rozmery, hrúbku a povrch:", sorted(df_cennik["rozmer + hrúbka + povrch"].unique()))
mnozstvo = st.number_input("Množstvo (m²):", min_value=1, step=1)

if st.button("Pridať tento typ dlažby"):
    celkove_mnozstvo = sum(p["mnozstvo"] for p in st.session_state["vybrane_dlazby"]) + mnozstvo
    cena_m2, cena, poznamka, doprava_text = vypocitaj_cenu(param, mnozstvo, celkove_mnozstvo)
    if cena is None:
        st.error("Nenašla sa cena pre vybraný formát.")
    else:
        st.session_state["vybrane_dlazby"].append({
            "param": param,
            "mnozstvo": mnozstvo,
            "cena_m2": cena_m2,
            "cena": cena,
            "poznamka": poznamka,
            "doprava_text": doprava_text
        })
        st.success("Dlažba bola pridaná.")

# ------------------- Súhrn -------------------
if st.session_state["vybrane_dlazby"]:
    st.subheader("Súhrn vášho výberu:")
    total = 0
    for i, p in enumerate(st.session_state["vybrane_dlazby"]):
        st.write(f"{i+1}. | {p['param']} | {p['cena_m2']} €/m² | {p['mnozstvo']} m² | {p['cena']} €")
        if p['doprava_text']:
            st.write(f"0. | {p['doprava_text']}")
        if p['poznamka']:
            st.info(p['poznamka'])
        total += p["cena"]
    st.write(f"**Orientačná cena spolu:** {total} €")

    if st.button("Vybrať ďalšiu dlažbu"):
        st.experimental_rerun()

    st.subheader("Doplnkové služby")
    vybrane_sluzby = st.multiselect("Vyberte služby:", df_sluzby["sluzba"].unique())
    st.session_state["sluzby"] = vybrane_sluzby

    st.subheader("Zadajte kontaktné údaje")
    email = st.text_input("Emailová adresa:")
    miesto = st.text_input("Miesto dodania:")

    if st.button("Odoslať dopyt"):
        if not email or not miesto:
            st.error("Zadajte email aj miesto dodania.")
        else:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for polozka in st.session_state["vybrane_dlazby"]:
                worksheet_dopyt.append_row([
                    timestamp,
                    "",
                    email,
                    miesto,
                    "",
                    "",
                    "",
                    "",
                    polozka["param"],
                    polozka["mnozstvo"],
                    polozka["cena"],
                    f"{polozka['param']} | {polozka['cena_m2']} €/m² | {polozka['mnozstvo']} m²"
                ])
            if st.session_state["sluzby"]:
                worksheet_dopyt.append_row([
                    timestamp, "", email, miesto, "", "", "", "", "Doplnkové služby",
                    "",
                    "",
                    ", ".join(st.session_state["sluzby"])
                ])
            st.success("Dopyt bol odoslaný.")
            st.session_state["vybrane_dlazby"] = []
            st.session_state["sluzby"] = []

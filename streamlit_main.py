import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import datetime
import json
import os
import random
import string

# ------------------- Autentifikácia -------------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# ------------------- Načítanie dát s cachovaním -------------------
@st.cache_data(ttl=300)
def nacitaj_data():
    sheet = client.open("ChatBot_Obklady_MR")
    df_cennik = pd.DataFrame(sheet.worksheet("cennik").get_all_records())
    df_doprava = pd.DataFrame(sheet.worksheet("doprava").get_all_records())
    df_sluzby = pd.DataFrame(sheet.worksheet("sluzby").get_all_records())
    worksheet_dopyt = sheet.worksheet("dopyt")
    return df_cennik, df_doprava, df_sluzby, worksheet_dopyt

df_cennik, df_doprava, df_sluzby, worksheet_dopyt = nacitaj_data()

# ------------------- Inicializácia session state -------------------
if "vybrane_dlazby" not in st.session_state:
    st.session_state["vybrane_dlazby"] = []
if "clear_form" not in st.session_state:
    st.session_state["clear_form"] = False

def generate_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# ------------------- Výpočet ceny -------------------
def vypocitaj_cenu(param, mnozstvo, celkove_mnozstvo):
    riadok = df_cennik[df_cennik["rozmer + hrúbka + povrch"] == param]
    if riadok.empty:
        return None, None, None, None, None
    doprava_text = None
    doprava_cena = 0
    if celkove_mnozstvo <= 20:
        cena_m2 = round(riadok.iloc[0]["21-59 m2"])
        doprava_riadok = df_doprava[df_doprava["polozka"].str.lower() == "doprava do 20 m²"]
        if not doprava_riadok.empty:
            doprava_cena = round(float(doprava_riadok["cena"].values[0]))
            doprava_text = "doprava do 20 m²"
        cena = round(cena_m2 * mnozstvo)
        poznamka = None
    elif 21 <= celkove_mnozstvo <= 59:
        cena_m2 = round(riadok.iloc[0]["21-59 m2"])
        cena = round(cena_m2 * mnozstvo)
        poznamka = None
    elif 60 <= celkove_mnozstvo <= 120:
        cena_m2 = round(riadok.iloc[0]["60-120 m2"])
        cena = round(cena_m2 * mnozstvo)
        poznamka = None
    else:
        cena_m2 = round(riadok.iloc[0]["60-120 m2"])
        cena = round(cena_m2 * mnozstvo)
        poznamka = "Pri množstve dlažby nad 121 m2 je pravdepodobne priestor pre zľavu. Odošlite formulár alebo nás priamo kontaktujte."
    return cena_m2, cena, poznamka, doprava_text, doprava_cena

# ------------------- Formulár -------------------
st.header("Overte si parametre našich dlažieb a orientačné ceny.")
st.write("Na cenu majú vplyv rozmery, povrch a množstvo dlažby.")

if st.session_state["clear_form"]:
    st.session_state["clear_form"] = False
    st.experimental_rerun()

param = st.selectbox("Vyberte rozmery, hrúbku a povrch:", sorted(df_cennik["rozmer + hrúbka + povrch"].unique()), key="param")
mnozstvo = st.number_input("Množstvo (m²):", min_value=1, step=1, key="mnozstvo")
vybrane_sluzby = st.multiselect("Vyberte doplnkové služby:", df_sluzby["sluzba"].unique(), key="sluzby")

if st.button("Pridať tento typ dlažby"):
    celkove_mnozstvo = sum(p["mnozstvo"] for p in st.session_state["vybrane_dlazby"]) + mnozstvo
    cena_m2, cena, poznamka, doprava_text, doprava_cena = vypocitaj_cenu(param, mnozstvo, celkove_mnozstvo)
    if cena is None:
        st.error("Nenašla sa cena pre vybraný formát.")
    else:
        polozka = {
            "param": param,
            "mnozstvo": mnozstvo,
            "cena_m2": cena_m2,
            "cena": cena,
            "poznamka": poznamka,
            "doprava_text": doprava_text,
            "doprava_cena": doprava_cena,
            "sluzby": vybrane_sluzby,
            "cena_sluzby": sum(round(df_sluzby[df_sluzby["sluzba"] == s]["cena"].values[0]) for s in vybrane_sluzby)
        }
        st.session_state["vybrane_dlazby"].append(polozka)
        st.success("Dlažba bola pridaná.")
        st.session_state["clear_form"] = True

# ------------------- Súhrn -------------------
if st.session_state["vybrane_dlazby"]:
    st.subheader("Súhrn vášho výberu:")
    total = 0
    for i, p in enumerate(st.session_state["vybrane_dlazby"], start=1):
        st.write(f"{i}. {p['param']} | {p['cena_m2']} €/m² | {p['mnozstvo']} m² | {p['cena']} €")
        total += p["cena"]
        if p["doprava_text"] and p["doprava_cena"]:
            st.write(f"{i}. {p['doprava_text']} | {p['doprava_cena']} €")
            total += p["doprava_cena"]
        for sluzba in p['sluzby']:
            cena_sluzby = round(df_sluzby[df_sluzby["sluzba"] == sluzba]["cena"].values[0])
            st.write(f"{i}. Doplnková služba: {sluzba} | {cena_sluzby} €")
            total += cena_sluzby
        if p['poznamka']:
            st.info(p['poznamka'])
    st.write(f"**Orientačná cena spolu:** {total} €")

    if st.button("Vybrať ďalšiu dlažbu"):
        st.session_state["param"] = None
        st.session_state["mnozstvo"] = 1
        st.session_state["sluzby"] = []
        st.rerun()

    st.subheader("Zadajte kontaktné údaje:")
    email = st.text_input("Emailová adresa:")
    miesto = st.text_input("Miesto dodania:")

    if st.button("Odoslať dopyt"):
        if not email or not miesto:
            st.error("Zadajte email aj miesto dodania.")
        else:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            id_zaujemcu = generate_id()
            for p in st.session_state["vybrane_dlazby"]:
                worksheet_dopyt.append_row([
                    timestamp,
                    id_zaujemcu,
                    email,
                    miesto,
                    "",
                    "",
                    "",
                    "",
                    p["param"],
                    p["mnozstvo"],
                    p["cena"] + p["doprava_cena"] + p["cena_sluzby"],
                    f"{p['param']} | {p['cena_m2']} €/m² | {p['mnozstvo']} m² | Služby: {', '.join(p['sluzby']) if p['sluzby'] else 'Žiadne'}"
                ])
            st.success("Dopyt bol odoslaný.")
            st.session_state["vybrane_dlazby"] = []

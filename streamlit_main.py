
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import uuid
import os
import json

# Google Sheets autentifikácia (cez secrets)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Názvy hárkov
SHEET_NAME = "ChatBot_Obklady_MR"
DOPYT_SHEET = "dopyt"
DIZAJN_SHEET = "dopyt_dizajn"
SHOWROOM_SHEET = "dopyt_showroom"

# Funkcia pre zápis dopytu na dlažbu
def zapis_dopyt(email, dekor, znacka, kolekcia, seria, rozmery, hrubka, povrch, mnozstvo):
    sheet = client.open(SHEET_NAME).worksheet(DOPYT_SHEET)
    datum = datetime.today().strftime("%Y-%m-%d")
    id_zaujemcu = "zaujemca_" + uuid.uuid4().hex[:6]
    sheet.append_row([datum, id_zaujemcu, email, "", dekor, znacka, kolekcia, seria, rozmery, hrubka, povrch, mnozstvo])

# Funkcia pre zápis dizajnového dopytu
def zapis_dizajn(email, typ, plocha, pudorys, styl, poznamka):
    sheet = client.open(SHEET_NAME).worksheet(DIZAJN_SHEET)
    datum = datetime.today().strftime("%Y-%m-%d")
    id_zaujemcu = "dizajn_" + uuid.uuid4().hex[:6]
    meno = ""  # prázdne meno
    sheet.append_row([datum, id_zaujemcu, meno, email, typ, plocha, pudorys, styl, poznamka])

# Funkcia pre zápis rezervácie showroomu
def zapis_showroom(email, mesto, poznamka):
    sheet = client.open(SHEET_NAME).worksheet(SHOWROOM_SHEET)
    datum = datetime.today().strftime("%Y-%m-%d")
    id_zaujemcu = "showroom_" + uuid.uuid4().hex[:6]
    sheet.append_row([datum, id_zaujemcu, email, mesto, "", poznamka, "nový"])

# Hlavné UI aplikácie
st.title("🧱 Obklady MR – Asistent")

st.write("Dobrý deň! S čím vám môžeme pomôcť?")
vyber = st.selectbox("Vyberte tému:", ["–", "Chcem si pozrieť ceny", "Potrebujem návrh / dizajn", "Chcem navštíviť showroom", "Chcem sa poradiť"])

if vyber == "Chcem si pozrieť ceny":
    st.subheader("Orientačný výpočet ceny")
    email = st.text_input("E-mail:")
    dekor = st.text_input("Dekor:")
    znacka = st.text_input("Značka:")
    kolekcia = st.text_input("Kolekcia:")
    seria = st.text_input("Séria:")
    rozmery = st.text_input("Rozmery (mm):")
    hrubka = st.text_input("Hrúbka (mm):")
    povrch = st.text_input("Povrch:")
    mnozstvo = st.text_input("Požadované množstvo (m²):")
    if st.button("Odoslať dopyt"):
        zapis_dopyt(email, dekor, znacka, kolekcia, seria, rozmery, hrubka, povrch, mnozstvo)
        st.success("Ďakujeme! Vaša požiadavka bola zaznamenaná.")

elif vyber == "Potrebujem návrh / dizajn":
    st.subheader("Záujem o návrh interiéru alebo vizualizáciu")
    email = st.text_input("E-mail:")
    typ = st.text_input("Typ priestoru (napr. kúpeľňa, kuchyňa):")
    plocha = st.text_input("Rozmery (plocha v m²):")
    pudorys = st.selectbox("Máte pôdorys?", ["áno", "nie"])
    styl = st.text_input("Preferovaný dekor / štýl:")
    poznamka = st.text_area("Doplňujúce informácie:")
    if st.button("Odoslať dizajnový dopyt"):
        zapis_dizajn(email, typ, plocha, pudorys, styl, poznamka)
        st.success("Ďakujeme! Náš tím sa vám čoskoro ozve.")

elif vyber == "Chcem navštíviť showroom":
    st.subheader("Rezervácia návštevy showroomu")
    st.markdown("📧 Rezerváciu termínu si zatiaľ dohodnite e-mailom na: [office@myresidence.sk](mailto:office@myresidence.sk)")
    email = st.text_input("E-mail:")
    mesto = st.selectbox("Mesto showroomu:", ["Košice", "Prešov", "Iné"])
    poznamka = st.text_area("Čo vás zaujíma?")
    if st.button("Odoslať žiadosť o návštevu"):
        zapis_showroom(email, mesto, poznamka)
        st.success("Ďakujeme! Vaša požiadavka bola zaznamenaná.")

elif vyber == "Chcem sa poradiť":
    st.subheader("FAQ a poradenstvo")
    st.markdown("❓ Zadajte svoju otázku a my vám odpovieme:")
    st.info("Táto sekcia bude čoskoro dostupná aj s napojením na našu databázu znalostí.")

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

# Inicializácia session state
if "polozky" not in st.session_state:
    st.session_state["polozky"] = []

if "stav_vyberu" not in st.session_state:
    st.session_state["stav_vyberu"] = "vyber"

if "rerun_po_pridani" not in st.session_state:
    st.session_state["rerun_po_pridani"] = False

def vypocitaj_cenu_dlazby(param, mnozstvo):
    filtr = df_cennik[df_cennik["rozmer + hrúbka + povrch"] == param]
    if filtr.empty:
        return None

    if mnozstvo <= 20:
        cena_za_m2 = filtr.iloc[0]["21-59 m2"]
        doprava_riadok = df_cennik[df_cennik["rozmer + hrúbka + povrch"] == "doprava"]
        doprava = doprava_riadok["21-59 m2"].values[0] if not doprava_riadok.empty else 0
        celkova_cena = round(cena_za_m2 * mnozstvo + doprava)
    elif 21 <= mnozstvo <= 59:
        cena_za_m2 = filtr.iloc[0]["21-59 m2"]
        celkova_cena = round(cena_za_m2 * mnozstvo)
    elif 60 <= mnozstvo <= 120:
        cena_za_m2 = filtr.iloc[0]["60-120 m2"]
        celkova_cena = round(cena_za_m2 * mnozstvo)
    else:
        cena_za_m2 = filtr.iloc[0]["60-120 m2"]
        celkova_cena = round(cena_za_m2 * mnozstvo)

    return celkova_cena

def main():
    st.title("🧱 Výber obkladov a dlažieb")

    # BEZPEČNÝ RERUN PO PRIDANÍ
    if st.session_state.get("rerun_po_pridani"):
        st.session_state["polozky"].append(st.session_state["nova_polozka"])
        st.success("Dlažba bola pridaná.")
        st.session_state["rerun_po_pridani"] = False

    if st.session_state["stav_vyberu"] == "vyber":
        st.header("➕ Pridajte dlažbu do výberu")

        dekor = st.selectbox("Dekor:", sorted(df_formaty["dekor"].unique()))
        df_kolekcia = df_formaty[df_formaty["dekor"] == dekor]

        kolekcia = st.selectbox("Kolekcia:", sorted(df_kolekcia["kolekcia"].unique()))
        df_seria = df_kolekcia[df_kolekcia["kolekcia"] == kolekcia]

        seria = st.selectbox("Séria:", sorted(df_seria["séria"].unique()))
        df_param = df_seria[df_seria["séria"] == seria]

        param = st.selectbox("Formát + povrch:", sorted(df_param["rozmer + hrúbka + povrch"].unique()))
        mnozstvo = st.number_input("Množstvo (m²):", min_value=1, step=1)

        if st.button("✅ Pridať túto dlažbu"):
            cena = vypocitaj_cenu_dlazby(param, mnozstvo)
            if cena is None:
                st.error("Pre tento výber nemáme cenu v cenníku.")
            else:
                st.session_state["nova_polozka"] = {
                    "dekor": dekor,
                    "kolekcia": kolekcia,
                    "séria": seria,
                    "formát": param,
                    "mnoznost": mnozstvo,
                    "cena": cena
                }
                st.session_state["rerun_po_pridani"] = True
                st.experimental_rerun()

        if st.session_state["polozky"]:
            if st.button("👉 Ukončiť výber a prejsť na súhrn"):
                st.session_state["stav_vyberu"] = "suhlas"
                st.experimental_rerun()

    elif st.session_state["stav_vyberu"] == "suhlas":
        st.header("🧾 Súhrn výberu")

        polozky = st.session_state["polozky"]
        celkove_m2 = sum(p["mnoznost"] for p in polozky)
        celkova_cena = sum(p["cena"] for p in polozky)

        for idx, p in enumerate(polozky, start=1):
            st.write(f"{idx}. {p['dekor']} / {p['kolekcia']} / {p['séria']} / {p['formát']} - {p['mnoznost']} m² - {p['cena']} €")

        st.write(f"**Celková výmera:** {celkove_m2} m²")
        st.write(f"**Cena spolu za dlažby:** {celkova_cena} €")

        if celkove_m2 > 121:
            st.info("💬 Bude vám ponúknutá individuálna zľava.")

        vybrane_sluzby = st.multiselect("Doplnkové služby:", df_sluzby["sluzba"].unique())
        cena_sluzieb = sum(df_sluzby[df_sluzby["sluzba"] == s]["cena"].values[0] for s in vybrane_sluzby)

        st.write(f"**Cena služieb spolu:** {cena_sluzieb} €")

        email = st.text_input("E-mail:")
        miesto = st.text_input("Miesto dodania:")

        if st.button("📨 Odoslať dopyt"):
            sheet = client.open(SHEET_NAME).worksheet(DOPYT_SHEET)
            datum = datetime.datetime.now().strftime("%Y-%m-%d")
            id_zaujemcu = f"zaujemca_{int(datetime.datetime.now().timestamp())}"

            suhrn = "; ".join([f"{p['dekor']} {p['kolekcia']} {p['séria']} {p['formát']} ({p['mnoznost']} m²)" for p in polozky])
            zapis = [
                datum, id_zaujemcu, email, miesto,
                polozky[0]["dekor"], polozky[0]["kolekcia"], polozky[0]["séria"], polozky[0]["formát"],
                celkove_m2, celkova_cena + cena_sluzieb, suhrn
            ]
            sheet.append_row(zapis)
            st.success("Dopyt bol odoslaný. Ďakujeme!")
            st.session_state["polozky"] = []
            st.session_state["stav_vyberu"] = "vyber"
            st.experimental_rerun()

if __name__ == "__main__":
    main()

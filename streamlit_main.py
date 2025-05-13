import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import datetime
from uuid import uuid4

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
    if filtr.empty:
        return None, None
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

    polozky = []

    st.header("👉 Vyberajte dlažby:")

    while True:
        dekor = st.selectbox("Vyberte dekor:", sorted(df_formaty["dekor"].unique()), key=f"dekor_{uuid4()}")
        df_kolekcie = df_formaty[df_formaty["dekor"] == dekor]

        kolekcia = st.selectbox("Vyberte kolekciu:", sorted(df_kolekcie["kolekcia"].unique()), key=f"kolekcia_{uuid4()}")
        df_serie = df_kolekcie[df_kolekcie["kolekcia"] == kolekcia]

        seria = st.selectbox("Vyberte sériu:", sorted(df_serie["séria"].unique()), key=f"seria_{uuid4()}")
        df_rozmery = df_serie[df_serie["séria"] == seria]

        param = st.selectbox("Vyberte formát + povrch:", sorted(df_rozmery["rozmer + hrúbka + povrch"].unique()), key=f"param_{uuid4()}")

        mnozstvo = st.number_input("Zadajte množstvo v m²:", min_value=1, step=1, key=f"mnozstvo_{uuid4()}")

        if st.button("Pridať dlažbu", key=f"pridat_{uuid4()}"):
            cena_dlazby, mnozstvo_zaznam = vypocitaj_cenu_dlazby(param, mnozstvo)
            if cena_dlazby is None:
                st.error("Pre vybraný formát + povrch nemáme zatiaľ cenu. Prosím kontaktujte nás e-mailom.")
            else:
                polozky.append({
                    "dekor": dekor,
                    "kolekcia": kolekcia,
                    "séria": seria,
                    "formát": param,
                    "množstvo": mnozstvo,
                    "cena": cena_dlazby
                })
                st.success("Dlažba bola pridaná do zoznamu.")
                st.experimental_rerun()

        if polozky:
            st.subheader("📝 Aktuálny výber:")
            for idx, p in enumerate(polozky):
                st.write(f"{idx+1}. {p['dekor']} / {p['kolekcia']} / {p['séria']} / {p['formát']} - {p['množstvo']} m² - {p['cena']} €")
            vymazat = st.selectbox("Chcete odstrániť nejakú dlažbu?", options=["Nie"] + [f"{i+1}" for i in range(len(polozky))], key=f"vymazat_{uuid4()}")
            if vymazat != "Nie":
                polozky.pop(int(vymazat)-1)
                st.experimental_rerun()

        pokracovat = st.radio("Chcete vyberať ďalej?", ("Áno", "Nie"), key=f"pokracovat_{uuid4()}")
        if pokracovat == "Nie":
            break

    if not polozky:
        st.error("Nevybrali ste žiadne dlažby.")
        return

    # Súhrn a výpočet ceny
    st.header("📋 Súhrn objednávky:")

    celkove_mnozstvo = sum(p["množstvo"] for p in polozky)
    celkova_cena_dlazieb = sum(p["cena"] for p in polozky)

    st.write(f"**Celková plocha:** {celkove_mnozstvo} m²")
    st.write(f"**Cena dlažieb spolu:** {celkova_cena_dlazieb} €")

    if celkove_mnozstvo > 121:
        st.info("💬 Upozornenie: Bude vám ponúknutá individuálna zľava.")

    # Výber služieb
    vybrane_sluzby = st.multiselect("Vyberte doplnkové služby:", sorted(df_sluzby["sluzba"].unique()), key=f"sluzby_{uuid4()}")

    cena_sluzieb = vypocitaj_cenu_sluzieb(vybrane_sluzby)
    st.write(f"**Cena služieb spolu:** {cena_sluzieb} €")

    # Zadanie e-mailu a miesta dodania
    email = st.text_input("Zadajte váš e-mail:", key=f"email_{uuid4()}")
    miesto = st.text_input("Zadajte miesto dodania:", key=f"miesto_{uuid4()}")

    if st.button("Odoslať dopyt finálne", key=f"odoslat_{uuid4()}"):
        sheet = client.open(SHEET_NAME).worksheet(DOPYT_SHEET)
        datum = datetime.datetime.now().strftime("%Y-%m-%d")
        id_zaujemcu = f"zaujemca_{int(datetime.datetime.now().timestamp())}"

        suhrn_poloziek = "; ".join([f"{p['dekor']} {p['kolekcia']} {p['séria']} {p['formát']} ({p['množstvo']} m²)" for p in polozky])

        novy_zaznam = [
            datum, id_zaujemcu, email, miesto,
            polozky[0]["dekor"], polozky[0]["kolekcia"], polozky[0]["séria"], polozky[0]["formát"],
            celkove_mnozstvo, celkova_cena_dlazieb + cena_sluzieb, suhrn_poloziek
        ]
        sheet.append_row(novy_zaznam)

        st.success("Dopyt bol úspešne odoslaný! Ďakujeme za záujem.")

if __name__ == "__main__":
    main()

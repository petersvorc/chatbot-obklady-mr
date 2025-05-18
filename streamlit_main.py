import streamlit as st
import pandas as pd
import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Načítanie údajov z Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Google Sheets
sheet = client.open("ChatBot_Obklady_MR")
df_formaty = pd.DataFrame(sheet.worksheet("formaty").get_all_records())
df_cennik = pd.DataFrame(sheet.worksheet("cennik").get_all_records())
df_dopyt = sheet.worksheet("dopyt")
df_sluzby = pd.DataFrame(sheet.worksheet("sluzby").get_all_records())
df_doprava = pd.DataFrame(sheet.worksheet("doprava").get_all_records())

# Funkcia na výpočet dopravy
def ziskaj_dopravu():
    try:
        riadok = df_doprava[df_doprava["polozka"].str.lower() == "doprava"]
        return float(riadok["cena"].values[0])
    except:
        return 0

# Výpočet ceny podľa množstva
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
        cena_za_m2 = filtr.iloc[0]["60-120 m2"]
        st.info("💬 Bude vám ponúknutá individuálna zľava.")
        celkova_cena = round(cena_za_m2 * mnozstvo)
    return celkova_cena

# Streamlit aplikácia
def main():
    st.title("🧱 Chatbot – Dopyt pre obklady a dlažby")

    if "polozky" not in st.session_state:
        st.session_state["polozky"] = []

    st.header("Vyberte si dlažbu")
    dekor = st.selectbox("Vyberte dekor:", sorted(df_formaty["dekor"].unique()))
    znacky = df_formaty[df_formaty["dekor"] == dekor]["značka"].unique()
    znacka = st.selectbox("Vyberte značku:", sorted(znacky))

    kolekcie = df_formaty[(df_formaty["dekor"] == dekor) & (df_formaty["značka"] == znacka)]["kolekcia"].unique()
    kolekcia = st.selectbox("Vyberte kolekciu:", sorted(kolekcie))

    serie = df_formaty[
        (df_formaty["dekor"] == dekor) &
        (df_formaty["značka"] == znacka) &
        (df_formaty["kolekcia"] == kolekcia)
    ]["séria"].unique()
    seria = st.selectbox("Vyberte sériu:", sorted(serie))

    df_filtered = df_formaty[
        (df_formaty["dekor"] == dekor) &
        (df_formaty["značka"] == znacka) &
        (df_formaty["kolekcia"] == kolekcia) &
        (df_formaty["séria"] == seria)
    ]
    formaty_moznosti = df_filtered["rozmer + hrúbka + povrch"].unique()
    param = st.selectbox("Vyberte formát + povrch:", sorted(formaty_moznosti))

    mnozstvo = st.number_input("Množstvo (m²):", min_value=1, step=1)

    if st.button("✅ Pridať túto dlažbu"):
        cena = vypocitaj_cenu_dlazby(param, mnozstvo)
        if cena is None:
            st.error("Pre tento výber nemáme cenu v cenníku.")
        else:
            st.success("Dlažba bola pridaná.")
            st.session_state["polozky"].append({
                "dekor": dekor,
                "znacka": znacka,
                "kolekcia": kolekcia,
                "seria": seria,
                "param": param,
                "mnozstvo": mnozstvo,
                "cena": cena
            })
            st.rerun()

    if st.session_state["polozky"]:
        st.subheader("📋 Súhrn výberu")
        for i, pol in enumerate(st.session_state["polozky"]):
            st.markdown(f"**{i+1}.** {pol['param']} – {pol['mnozstvo']} m² – {pol['cena']} €")

        if st.button("👉 Ukončiť výber a prejsť na súhrn"):
            meno = st.text_input("Vaše meno alebo názov firmy:")
            email = st.text_input("E-mail:")
            miesto = st.text_input("Miesto dodania:")

            vybrane_sluzby = st.multiselect("Doplnkové služby:", df_sluzby["sluzba"].unique())
            cena_sluzieb = sum(df_sluzby[df_sluzby["sluzba"] == s]["cena"].values[0] for s in vybrane_sluzby)

            st.write(f"**Cena služieb spolu:** {cena_sluzieb} €")

            if st.button("📩 Odoslať dopyt"):
                datum = datetime.now().strftime("%Y-%m-%d")
                for pol in st.session_state["polozky"]:
                    df_dopyt.append_row([
                        datum,
                        f"zaujemca_{datum}",
                        email,
                        miesto,
                        pol["dekor"],
                        pol["znacka"],
                        pol["kolekcia"],
                        pol["seria"],
                        pol["param"],
                        pol["mnozstvo"],
                        "",  # stav
                        ", ".join(vybrane_sluzby),
                        cena_sluzieb,
                        pol["cena"]
                    ])
                st.success("✅ Dopyt bol odoslaný. Ozveme sa vám čoskoro.")
                st.session_state["polozky"] = []
                st.rerun()

if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd
import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials

# Autorizácia k Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Názvy sheetov
sheet_id = "1iALZvof0sDNU9aMDrh74RgT7T08RZxB36j-nM0Xtbfc"
formaty = client.open_by_key(sheet_id).worksheet("formaty")
cennik = client.open_by_key(sheet_id).worksheet("cennik")
doprava = client.open_by_key(sheet_id).worksheet("doprava")
dopyt = client.open_by_key(sheet_id).worksheet("dopyt")
sluzby = client.open_by_key(sheet_id).worksheet("sluzby")

# Načítanie dát
df_formaty = pd.DataFrame(formaty.get_all_records())
df_cennik = pd.DataFrame(cennik.get_all_records())
df_doprava = pd.DataFrame(doprava.get_all_records())
df_sluzby = pd.DataFrame(sluzby.get_all_records())

# Výpočet ceny
def ziskaj_dopravu():
    try:
        riadok = df_doprava[df_doprava["polozka"].str.lower() == "doprava"]
        return float(riadok["cena"].values[0])
    except:
        return 0

def vypocitaj_cenu_dlazby(param, mnozstvo):
    filtr = df_cennik[df_cennik["rozmer + hrubka + povrch"] == param]
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

# Aplikácia
st.title("Vyberte si dlažbu")

# Výber dekoru
dekor = st.selectbox("Dekor:", sorted(df_formaty["dekor"].unique()))
df_filtered = df_formaty[df_formaty["dekor"] == dekor]

# Výber ďalších parametrov
kolekcia = st.selectbox("Kolekcia:", sorted(df_filtered["kolekcia"].unique()))
df_filtered = df_filtered[df_filtered["kolekcia"] == kolekcia]

seria = st.selectbox("Séria:", sorted(df_filtered["séria"].unique()))
df_filtered = df_filtered[df_filtered["séria"] == seria]

param = st.selectbox("Formát + povrch:", sorted(df_filtered["rozmer + hrubka + povrch"].unique()))

# Množstvo
mnozstvo = st.number_input("Množstvo (m²):", min_value=1, step=1)

# Doplnkové služby
vybrane_sluzby = st.multiselect("Doplnkové služby:", df_sluzby["sluzba"].unique())
cena_sluzieb = sum(df_sluzby[df_sluzby["sluzba"] == s]["cena"].values[0] for s in vybrane_sluzby) if vybrane_sluzby else 0
st.write(f"**Cena služieb spolu:** {cena_sluzieb} €")

# E-mail
email = st.text_input("Zadajte váš e-mail")

# Potvrdenie
if st.button("✅ Odoslať dopyt"):
    cena = vypocitaj_cenu_dlazby(param, mnozstvo)
    if cena is None:
        st.error("Pre tento výber nemáme cenu v cenníku.")
    else:
        zaznam = [dekor, kolekcia, seria, param, mnozstvo, cena, ", ".join(vybrane_sluzby), cena_sluzieb, email]
        dopyt.append_row(zaznam)
        st.success("Dopyt bol úspešne odoslaný!")

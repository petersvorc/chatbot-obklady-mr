st.header("Vyberte si dlažbu")
dekor = st.selectbox("Vyberte dekor:", sorted(df_formaty["dekor"].unique()))

kolekcie = df_formaty[df_formaty["dekor"] == dekor]["kolekcia"].unique()
kolekcia = st.selectbox("Vyberte kolekciu:", sorted(kolekcie))

serie = df_formaty[
    (df_formaty["dekor"] == dekor) &
    (df_formaty["kolekcia"] == kolekcia)
]["séria"].unique()
seria = st.selectbox("Vyberte sériu:", sorted(serie))

df_filtered = df_formaty[
    (df_formaty["dekor"] == dekor) &
    (df_formaty["kolekcia"] == kolekcia) &
    (df_formaty["séria"] == seria)
]
formaty_moznosti = df_filtered["rozmer + hrúbka + povrch"].unique()
param = st.selectbox("Vyberte formát + povrch:", sorted(formaty_moznosti))

# Značka sa zistí automaticky z filtrovaného df
znacka = df_filtered[df_filtered["rozmer + hrúbka + povrch"] == param]["značka"].values[0]

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

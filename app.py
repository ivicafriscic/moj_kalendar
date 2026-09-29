import streamlit as st
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import urllib.parse
import os
import json

DATOTEKA_BAZE = "lokalna_baza.json"
ADMIN_LOZINKA = "Ivo"

SMTP_SERVER = "://gmail.com"             
SMTP_PORT = 587  
MOJ_EMAIL = "ana.koren1@gmail.com"            
MOJA_LOZINKA = "dyyhszecummfwkej"             
EMAIL_PONUDACA = "friscicivica69@gmail.com" 

def ucitaj_trajne_podatke():
    if os.path.exists(DATOTEKA_BAZE):
        try:
            with open(DATOTEKA_BAZE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"slobodni": [], "rezervirani": {}, "podsjetnici": []}

def spremi_trajne_podatke(p):
    try:
        with open(DATOTEKA_BAZE, "w", encoding="utf-8") as f:
            json.dump(p, f, indent=4, ensure_ascii=False)
    except:
        pass

if "baza_lokalna" not in st.session_state:
    st.session_state.baza_lokalna = ucitaj_trajne_podatke()
baza = st.session_state.baza_lokalna

def posalji_email_genericki(primatelj, naslov, tekst):
    try:
        msg = MIMEText(tekst, "plain", "utf-8")
        msg["Subject"] = naslov
        msg["From"] = MOJ_EMAIL
        msg["To"] = primatelj
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
        server.ehlo()
        server.starttls()  
        server.ehlo()
        server.login(MOJ_EMAIL, MOJA_LOZINKA)
        server.sendmail(MOJ_EMAIL, [primatelj], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP Greška: {e}")
        return False

def posalji_email_potvrde_direktno(termin, ime, mail_kl):
    try:
        cisto = termin[:16]
        p_poc = datetime.strptime(cisto, "%Y-%m-%d %H:%M")
        t_trajanje = 45
        if "35 min" in termin: t_trajanje = 35
        elif "90 min" in termin: t_trajanje = 90
        p_kraj = p_poc + timedelta(minutes=t_trajanje)
        g_start = p_poc.strftime("%Y%m%dT%H%M%S")
        g_end = p_kraj.strftime("%Y%m%dT%H%M%S")
        g_naslov = urllib.parse.quote(f"Nastava: {ime}")
        g_opis = urllib.parse.quote(f"Polaznik: {ime}\nOpis: {termin}")
        google_cal_link = f"https://google.com{g_naslov}&dates={g_start}/{g_end}&details={g_opis}"
        link_tekst = f"\n\n📅 Dodaj u Google kalendar jednim klikom:\n{google_cal_link}"
    except:
        link_tekst = ""
    naslov_m = f"Rezervacija termina: {termin}"
    tekst_m = f"Pozdrav,\n\nUspješna rezervacija!\n\nTermin: {termin}\nPolaznik: {ime}\nE-mail: {mail_kl}{link_tekst}\n\nŠkola brzog čitanja Varaždin"
    posalji_email_genericki(EMAIL_PONUDACA, naslov_m, tekst_m)
    posalji_email_genericki(mail_kl, naslov_m, tekst_m)
    return True

def provjeri_i_posalji_podsjetnike_brzo():
    try:
        sada = datetime.now()
        za_cetiri_sata = sada + timedelta(hours=4)
        rez_rjecnik = baza.get("rezervirani", {})
        for stavka in list(rez_rjecnik.keys()):
            cisto = stavka[:16]
            poc = datetime.strptime(cisto, "%Y-%m-%d %H:%M")
            if sada < poc <= za_cetiri_sata and stavka not in baza.get("podsjetnici", []):
                info = rez_rjecnik.get(stavka, {})
                naslov_p = "Podsjetnik na Vaš termin"
                tekst_p = f"Poštovani/a {info.get('klijent')},\n\nImate rezerviran termin za 4 sata.\n📅 {stavka}\n\nKREO tim"
                # ISPRAVLJENO: Točno povlačenje ključa 'email' iz baze
                if posalji_email_genericki(info.get("email"), naslov_p, tekst_p):
                    baza["podsjetnici"].append(stavka)
        spremi_trajne_podatke(baza)
    except:
        pass

provjeri_i_posalji_podsjetnike_brzo()
st.set_page_config(page_title="Rezervacija Termina", page_icon="📅")
st.title("📅 Online Rezervacija Termina")
tab1, tab2 = st.tabs(["👤 Rezerviraj Termin", "🔐 Admin Panel"])

with tab1:
    st.write("Odaberite slobodan termin i unesite podatke.")
    if "uspjeh_poruka" in st.session_state:
        st.success(st.session_state.uspjeh_poruka)
        del st.session_state.uspjeh_poruka
    slobodni_prikaz = [t for t in baza.get("slobodni", []) if t not in baza.get("rezervirani", {})]
    if not slobodni_prikaz:
        st.info("Trenutno nema slobodnih termina.")
    else:
        with st.form("forma_rezervacija", clear_on_submit=True):
            ime = st.text_input("Ime i Prezime:")
            email_kupca = st.text_input("Vaš E-mail:")
            termin = st.selectbox("Termin:", sorted(slobodni_prikaz))
            if st.form_submit_button("Potvrdi Rezervaciju"):
                if not ime or not email_kupca:
                    st.warning("Ispunite sva polja!")
                else:
                    baza["slobodni"].remove(termin)
                    baza["rezervirani"][termin] = {"klijent": ime, "email": email_kupca}
                    posalji_email_potvrde_direktno(termin, ime, email_kupca)
                    spremi_trajne_podatke(baza)
                    st.session_state.uspjeh_poruka = f"Uspješno rezervirano: {termin}!"
                    st.rerun()

with tab2:
    st.header("Administracija")
    upisana_lozinka = st.text_input("Lozinka:", type="password")
    if upisana_lozinka == ADMIN_LOZINKA:
        st.success("Pristup odobren!")
        if "admin_uspjeh" in st.session_state:
            st.success(st.session_state.admin_uspjeh)
            del st.session_state.admin_uspjeh
        if st.button("🚨 Očisti cijelu listu"):
            baza["slobodni"], baza["rezervirani"], baza["podsjetnici"] = [], {}, []
            spremi_trajne_podatke(baza)
            st.rerun()
        col_d, col_v = st.columns(2)
        odabrani_datum = col_d.date_input("Datum:", datetime.now())
        sati_opcije = [f"{h:02d}:{m:02d}" for h in range(8, 21) for m in (0, 15, 30, 45)]
        odabrano_vrijeme = col_v.selectbox("Vrijeme:", sati_opcije)
        opcije_trajanja = {
            "35 minuta - POMOĆ U ČITANJU": "35 min - POMOĆ U ČITANJU",
            "45 minuta - BESPLATNO TESTIRANJE ČITANJA": "45 min - BESPLATNO TESTIRANJE ČITANJA",
            "90 minuta - BRZO ČITANJE I MUDRO UČENJE": "90 min - BRZO ČITANJE I MUDRO UČENJE"
        }
        odabrani_opis = st.radio("Program:", list(opcije_trajanja.keys()))
        text_programa = opcije_trajanja[odabrani_opis]
        if st.button("➕ Kreiraj i dodaj termin"):
            novi = f"{odabrani_datum} {odabrano_vrijeme} ({text_programa})"
            if novi in baza.get("slobodni", []):
                st.error("Termin već postoji!")
            else:
                baza["slobodni"].append(novi)
                spremi_trajne_podatke(baza)
                st.session_state.admin_uspjeh = f"Kreirano: {novi}"
                st.rerun()
        st.subheader("📋 Slobodni termini")
        st.dataframe(baza.get("slobodni", []), use_container_width=True)
        st.subheader("📋 Rezervirani termini")
        st.write(baza.get("rezervirani", {}))
    elif upisana_lozinka != "":
        st.error("Pogrešna lozinka!")


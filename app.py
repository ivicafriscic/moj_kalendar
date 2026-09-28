
import streamlit as st
import json
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import threading
import time
import io
import openpyxl
import urllib.parse

DATOTEKA_PODATAKA = "podaci.json"
ADMIN_LOZINKA = "Pletern1c@"  # <--- PROMIJENITE OVU LOZINKU ZA ADMINA

# --- PODACI ZA EMAIL POŠILJATELJA ---
SMTP_SERVER = "74.125.140.108"              
SMTP_PORT = 465
MOJ_EMAIL = "ana.koren1@gmail.com"            # <--- VAŠ GMAIL
MOJA_LOZINKA = "dyyhszecummfwkej" # <--- GOOGLE APP PASSWORD (16 SLOVA)
EMAIL_PONUDACA = "brzocitanjeiucenjevz@gmail.com" # <--- GDJE STIŽE OBAVIJEST

def ucitaj_podatke():
    if os.path.exists(DATOTEKA_PODATAKA):
        with open(DATOTEKA_PODATAKA, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"slobodni": [], "rezervirani": {}, "poslani_podsjetnici": []}

def spremi_podatke(podaci):
    with open(DATOTEKA_PODATAKA, "w", encoding="utf-8") as f:
        json.dump(podaci, f, indent=4, ensure_ascii=False)

def posalji_email_genericki(primatelj, naslov, tekst):
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.login(MOJ_EMAIL, MOJA_LOZINKA)
        msg = MIMEText(tekst, "plain", "utf-8")
        msg["Subject"] = naslov
        msg["From"] = MOJ_EMAIL
        msg["To"] = primatelj
        server.sendmail(MOJ_EMAIL, [primatelj], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"❌ Neuspješno slanje maila na {primatelj}. Greška: {e}")
        return False

def posalji_email_potvrde_direktno(termin, ime_klijenta, email_klijenta):
    naslov_ponudac = f"Nova rezervacija termina: {termin}"
    tekst_ponudac = f"Pozdrav,\n\nImate novu rezervaciju!\n\nTermin: {termin}\nKlijent: {ime_klijenta}\nE-mail klijenta: {email_klijenta}\n\nLijep pozdrav,\nVaš Web Sustav"
    
    naslov_klijent = "Potvrda rezervacije termina - Škola brzog čitanja i mudrog učenja Varaždin"
    tekst_klijent = f"Poštovani/a {ime_klijenta},\n\nOvim putem potvrđujemo Vašu rezervaciju termina.\n\nDetalji:\n📅 Termin: {termin}\n\nU slučaju bilo kakvih promjena ili dodatnih pitanja, slobodno nas kontaktirajte odgovaranjem na ovaj mail ili putem naših društvenih mreža.\n\nHvala Vam na povjerenju!\n\nSrdačan pozdrav,\nŠkola brzog čitanja i mudrog učenja Varaždin"
    
    ok_vlasnik = posalji_email_genericki(EMAIL_PONUDACA, naslov_ponudac, tekst_ponudac)
    ok_klijent = posalji_email_genericki(email_klijenta, naslov_klijent, tekst_klijent)
    return ok_vlasnik and ok_klijent

def parsiraj_vrijeme_termina(termin_puni):
    """Pomoćna funkcija koja precizno izvlači točan početak i kraj termina radi provjere preklapanja."""
    try:
        # Primjer formata: "28.09.2026 14:30 (35 min - POMOĆ U ČITANJU)"
        dijelovi = termin_puni.split(" (")
        vrijeme_str = dijelovi[0].strip()
        
        # Izvlačenje minuta iz drugog dijela: "35 min - POMOĆ U ČITANJU)"
        trajanje_dio = dijelovi[1].split(" min")
        minute = int(trajanje_dio[0].strip())
        
        pocetak = datetime.strptime(vrijeme_str, "%d.%m.%Y %H:%M")
        kraj = pocetak + timedelta(minutes=minute)
        return pocetak, kraj
    except:
        return None, None

def provjeri_i_posalji_podsjetnike():
    while True:
        try:
            podaci_baza = ucitaj_podatke()
            promjena = False
            if "poslani_podsjetnici" not in podaci_baza:
                podaci_baza["poslani_podsjetnici"] = []
                promjena = True
            sada = datetime.now()
            za_cetiri_sata = sada + timedelta(hours=4)
            
            for termin_str, info in list(podaci_baza["rezervirani"].items()):
                pocetak, kraj = parsiraj_vrijeme_termina(termin_str)
                if pocetak and sada < pocetak <= za_cetiri_sata and termin_str not in podaci_baza["poslani_podsjetnici"]:
                    naslov_podsjetnik = "Podsjetnik na Vaš termin"
                    tekst_podsjetnik = f"Poštovani/a {info['klijent']},\n\nOvo je automatski podsjetnik da imate rezerviran termin kod nas za točno 4 sata.\n\n📅 Termin: {termin_str}\n\nRadujemo se Vašem dolasku!\n\nSrdačan pozdrav,\nŠkola brzog čitanja i mudrog učenja Varaždin"
                    if posalji_email_genericki(info["email"], naslov_podsjetnik, tekst_podsjetnik):
                        podaci_baza["poslani_podsjetnici"].append(termin_str)
                        promjena = True
            if promjena:
                spremi_podatke(podaci_baza)
        except Exception as e:
            print(f"Greška u pozadinskom podsjetniku: {e}")
        time.sleep(300)

if not any(t.name == "KreoPodsjetnikThread" for t in threading.enumerate()):
    timer_thread = threading.Thread(target=provjeri_i_posalji_podsjetnike, name="KreoPodsjetnikThread", daemon=True)
    timer_thread.start()

if "podaci" not in st.session_state:
    st.session_state.podaci = ucitaj_podatke()
podaci = st.session_state.podaci

st.set_page_config(page_title="Rezervacija Termina", page_icon="📅", layout="centered")

IME_SLIKE = "logo.png"
if os.path.exists(IME_SLIKE):
    st.image(IME_SLIKE, use_container_width=True)
else:
    st.header("Škola brzog čitanja i mudrog učenja Varaždin")

st.title("📅 Online Rezervacija Termina")
tab1, tab2 = st.tabs(["👤 Rezerviraj Termin", "🔐 Admin Panel"])

with tab1:
    st.write("Dobrodošli! Odaberite jedan od slobodnih termina i unesite svoje podatke.")
    if "uspjeh_poruka" in st.session_state:
        st.success(st.session_state.uspjeh_poruka)
        del st.session_state.uspjeh_poruka

    with st.form("forma_rezervacija", clear_on_submit=True):
        ime = st.text_input("Ime i Prezime:")
        email_kupca = st.text_input("Vaš E-mail:")
        slobodni = [t for t in podaci["slobodni"] if t not in podaci["rezervirani"]]
        if not slobodni:
            st.info("Trenutno nema slobodnih termina. Molimo pokušajte kasnije.")
            gumb_rezerviraj = None
        else:
            termin = st.selectbox("Odaberite slobodan termin:", sorted(slobodni))
            gumb_rezerviraj = st.form_submit_button("Potvrdi Rezervaciju")
        if gumb_rezerviraj:
            if not ime or not email_kupca:
                st.warning("Molimo ispunite sva polja!")
            else:
                podaci["slobodni"].remove(termin)
                podaci["rezervirani"][termin] = {"klijent": ime, "email": email_kupca}
                with st.spinner("Slanje e-mail obavijesti..."):
                    slanje_uspjelo = posalji_email_potvrde_direktno(termin, ime, email_kupca)
                if slanje_uspjelo:
                    spremi_podatke(podaci)
                    st.session_state.uspjeh_poruka = f"Uspješno ste rezervirali termin {termin}! Potvrda je poslana na Vaš e-mail."
                    st.rerun()
                else:
                    podaci["slobodni"].append(termin)
                    del podaci["rezervirani"][termin]

    st.markdown("---")
    st.subheader("🔗 Kontakt i društvene mreže")
    st.markdown("""
    Pratite naš rad ili nas kontaktirajte putem interneta:
    * **Web stranica:** [://kreo-vz.com](https://://kreo-vz.com)
    * **Facebook:** [Škola brzog čitanja i mudrog učenja - Varaždin](https://facebook.com)
    * **Instagram:** [@skola_brzog_citanja_varazdin](https://instagram.com)
    """)

with tab2:
    st.header("Administracija")
    upisana_lozinka = st.text_input("Unesite admin lozinku:", type="password")
    
    if upisana_lozinka == ADMIN_LOZINKA:
        st.success("Pristup odobren!")
        
        st.subheader("🛠️ Alat za generiranje termina")
        
        if "odabrano_trajanje" not in st.session_state:
            st.session_state.odabrano_trajanje = 45

        if "admin_uspjeh" in st.session_state:
            st.success(st.session_state.admin_uspjeh)
            del st.session_state.admin_uspjeh

        col_d, col_v = st.columns(2)
        odabrani_datum = col_d.date_input("1. Odaberite datum:", datetime.now())
        sati_opcije = [f"{h:02d}:{m:02d}" for h in range(8, 21) for m in (0, 15, 30, 45)]
        odabrano_vrijeme = col_v.selectbox("2. Odaberite vrijeme početka:", sati_opcije)
        
        st.write("3. Odaberite trajanje lekcije:")
        c1, c2, c3 = st.columns(3)
        if c1.button("⏱️ 35 minuta", type="primary" if st.session_state.odabrano_trajanje == 35 else "secondary"):
            st.session_state.odabrano_trajanje = 35
        if c2.button("⏱️ 45 minuta", type="primary" if st.session_state.odabrano_trajanje == 45 else "secondary"):
            st.session_state.odabrano_trajanje = 45
        if c3.button("⏱️ 90 minuta", type="primary" if st.session_state.odabrano_trajanje == 90 else "secondary"):
            st.session_state.odabrano_trajanje = 90
            
        opis_lekcije = ""
        if st.session_state.odabrano_trajanje == 35:
            opis_lekcije = " - POMOĆ U ČITANJU"
        elif st.session_state.odabrano_trajanje == 45:
            opis_lekcije = " - BESPLATNO TESTIRANJE ČITANJA"
        elif st.session_state.odabrano_trajanje == 90:
            opis_lekcije = " - BRZO ČITANJE I MUDRO UČENJE"
            
        st.info(f"Trenutno označeno: **{st.session_state.odabrano_trajanje} minuta{opis_lekcije}**")
        
        if st.button("➕ Kreiraj i dodaj termin u sustav"):
            pocetak_dt = datetime.combine(odabrani_datum, datetime.strptime(odabrano_vrijeme, "%H:%M").time())
            kraj_dt = pocetak_dt + timedelta(minutes=st.session_state.odabrano_trajanje)
            
            novi_termin_puni = f"{pocetak_dt.strftime('%d.%m.%Y %H:%M')} ({st.session_state.odabrano_trajanje} min{opis_lekcije})"
            
            preklapa_se = False
            svi_postojeci_termini = podaci["slobodni"] + list(podaci["rezervirani"].keys())
            

                        break


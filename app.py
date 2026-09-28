import streamlit as st
import json
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import io
import openpyxl
import urllib.parse

DATOTEKA_PODATAKA = "podaci.json"
ADMIN_LOZINKA = "Ivo"  # <--- Vaša lozinka za ulaz u Admin Panel

# --- PODACI ZA EMAIL POŠILJATELJA ---
SMTP_SERVER = "74.125.140.108"              
SMTP_PORT = 465
MOJ_EMAIL = "ana.koren1@gmail.com"            # Vaš Gmail račun preko kojeg se šalje
MOJA_LOZINKA = "dyyhszecummfwkej"             # Vaša Google aplikacijska lozinka (16 slova)
EMAIL_PONUDACA = "brzocitanjeiucenjevz@gmail.com" # Mail na koji primate obavijesti o novoj rezervaciji

def ucitaj_podatke():
    if os.path.exists(DATOTEKA_PODATAKA):
        try:
            with open(DATOTEKA_PODATAKA, "r", encoding="utf-8") as f:
                podaci = json.load(f)
                # Prisilno osiguravanje čistih mapa i listi bez obzira na stare zapise
                if not isinstance(podaci.get("slobodni"), list):
                    podaci["slobodni"] = []
                if not isinstance(podaci.get("rezervirani"), dict):
                    podaci["rezervirani"] = {}
                if not isinstance(podaci.get("poslani_podsjetnici"), list):
                    podaci["poslani_podsjetnici"] = []
                if not isinstance(podaci.get("metapodaci"), dict):
                    podaci["metapodaci"] = {}
                return podaci
        except:
            pass
    return {"slobodni": [], "rezervirani": {}, "poslani_podsjetnici": [], "metapodaci": {}}

def spremi_podatke(podaci_za_spremiti):
    with open(DATOTEKA_PODATAKA, "w", encoding="utf-8") as f:
        json.dump(podaci_za_spremiti, f, indent=4, ensure_ascii=False)

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
        print(f"Greška pri slanju emaila: {e}")
        return False

def posalji_email_potvrde_direktno(termin, ime_klijenta, email_klijenta):
    naslov_ponudac = f"Nova rezervacija termina: {termin}"
    tekst_ponudac = f"Pozdrav,\n\nImate novu rezervaciju!\n\nTermin: {termin}\nKlijent: {ime_klijenta}\nE-mail klijenta: {email_klijenta}\n\nLijep pozdrav,\nVaš Web Sustav"
    
    naslov_klijent = "Potvrda rezervacije termina - Škola brzog čitanja i mudrog učenja Varaždin"
    tekst_klijent = f"Poštovani/a {ime_klijenta},\n\nOvim putem potvrđujemo Vašu rezervaciju termina.\n\nDetalji:\n📅 Termin: {termin}\n\nU slučaju bilo kakvih promjena ili dodatnih pitanja, slobodno nas kontaktirajte odgovaranjem na ovaj mail ili putem naših društvenih mreža.\n\nHvala Vam na povjerenju!\n\nSrdačan pozdrav,\nŠkola brzog čitanja i mudrog učenja Varaždin"
    
    ok_vlasnik = posalji_email_genericki(EMAIL_PONUDACA, naslov_ponudac, tekst_ponudac)
    ok_klijent = posalji_email_genericki(email_klijenta, naslov_klijent, tekst_klijent)
    return ok_vlasnik and ok_klijent

def provjeri_i_posalji_podsjetnike_brzo(podaci_baza):
    try:
        promjena = False
        sada = datetime.now()
        za_cetiri_sata = sada + timedelta(hours=4)
        
        meta = podaci_baza.get("metapodaci", {})
        for k in list(meta.keys()):
            v = meta.get(k, {})
            pocetak_str = v.get("pocetak", "")
            if pocetak_str:
                try:
                    pocetak = datetime.strptime(pocetak_str, "%Y-%m-%d %H:%M")
                    if sada < pocetak <= za_cetiri_sata and k not in podaci_baza.get("poslani_podsjetnici", []):
                        info = podaci_baza.get("rezervirani", {}).get(k)
                        if info:
                            naslov_podsjetnik = "Podsjetnik na Vaš termin"
                            tekst_podsjetnik = f"Poštovani/a {info['klijent']},\n\nOvo je automatski podsjetnik da imate rezerviran termin kod nas za točno 4 sata.\n\n📅 Termin: {k}\n\nRadujemo se Vašem dolasku!\n\nSrdačan pozdrav,\nVaš KREO tim"
                            if posalji_email_genericki(info["email"], naslov_podsjetnik, tekst_podsjetnik):
                                podaci_baza["poslani_podsjetnici"].append(k)
                                promjena = True
                except:
                    continue
        if promjena:
            spremi_podatke(podaci_baza)
    except Exception as e:
        print(f"Greška u podsjetnicima: {e}")

# --- INICIJALIZACIJA BAZE PODATAKA ---
podaci = ucitaj_podatke()
provjeri_i_posalji_podsjetnike_brzo(podaci)

if "podaci" not in st.session_state:
    st.session_state.podaci = podaci
podaci = st.session_state.podaci

st.set_page_config(page_title="Rezervacija Termina", page_icon="📅", layout="centered")

IME_SLIKE = "logo.png"
if os.path.exists(IME_SLIKE):
    st.image(IME_SLIKE, use_container_width=True)
else:
    st.header("Škola brzog čitanja i mudrog učenja Varaždin")

st.title("📅 Online Rezervacija Termina")
st.markdown("Ovdje možete brzo i izravno rezervirati ili organizirati termine za nastavu.")
tab1, tab2 = st.tabs(["👤 Rezerviraj Termin", "🔐 Admin Panel"])

with tab1:
    st.write("Dobrodošli! Odaberite jedan od slobodnih termina i unesite svoje podatke.")
    if "uspjeh_poruka" in st.session_state:
        st.success(st.session_state.uspjeh_poruka)
        del st.session_state.uspjeh_poruka

    slobodni_prikaz = [t for t in podaci.get("slobodni", []) if t not in podaci.get("rezervirani", {})]
    
    if not slobodni_prikaz:
        st.info("Trenutno nema slobodnih termina. Molimo pokušajte kasnije.")
    else:
        with st.form("forma_rezervacija", clear_on_submit=True):
            ime = st.text_input("Ime i Prezime:")
            email_kupca = st.text_input("Vaš E-mail:")
            termin = st.selectbox("Odaberite slobodan termin:", sorted(slobodni_prikaz))
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
        
        if "admin_uspjeh" in st.session_state:
            st.success(st.session_state.admin_uspjeh)
            del st.session_state.admin_uspjeh

        # --- GUMB ZA TOTALNO RESTARTIRANJE STRANICE ---
        if st.button("🚨 Očisti cijelu bazu podataka (Kreni ispočetka)"):
            podaci["slobodni"] = []
            podaci["rezervirani"] = {}
            podaci["poslani_podsjetnici"] = []
            podaci["metapodaci"] = {}
            spremi_podatke(podaci)
            st.warning("Baza podataka je u potpunosti obrisana!")
            st.rerun()

        col_d, col_v = st.columns(2)
        odabrani_datum = col_d.date_input("1. Odaberite datum:", datetime.now())
        sati_opcije = [f"{h:02d}:{m:02d}" for h in range(8, 21) for m in (0, 15, 30, 45)]
        odabrano_vrijeme = col_v.selectbox("2. Odaberite vrijeme početka:", sati_opcije)
        
        st.write("3. Odaberite trajanje lekcije:")
        opcije_trajanja = {
            "35 minuta - POMOĆ U ČITANJU": 35,
            "45 minuta - BESPLATNO TESTIRANJE ČITANJA": 45,
            "90 minuta - BRZO ČITANJE I MUDRO UČENJE": 90
        }
        odabrani_opis = st.radio("Označite željeni program:", list(opcije_trajanja.keys()))
        minute_trajanja = opcije_trajanja[odabrani_opis]
        
        cisti_opis_tekst = "Nastava"
        if "POMOĆ" in odabrani_opis:
            cisti_opis_tekst = "POMOĆ U ČITANJU"
        elif "TESTIRANJE" in odabrani_opis:
            cisti_opis_tekst = "BESPLATNO TESTIRANJE ČITANJA"
        elif "MUDRO" in odabrani_opis:
            cisti_opis_tekst = "BRZO ČITANJE I MUDRO UČENJE"
            
        st.info(f"Trenutno označeno: **{minute_trajanja} minuta - {cisti_opis_tekst}**")
        
        if st.button("➕ Kreiraj i dodaj termin u sustav"):
            pocetak_dt = datetime.combine(odabrani_datum, datetime.strptime(odabrano_vrijeme, "%H:%M").time())
            kraj_dt = pocetak_dt + timedelta(minutes=minute_trajanja)
            
            novi_termin_puni = f"{pocetak_dt.strftime('%d.%m.%Y.')} {pocetak_dt.strftime('%H:%M')} ({minute_trajanja} min - {cisti_opis_tekst})"
            
            preklapa_se = False


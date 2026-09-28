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
                if "slobodni" not in podaci or not isinstance(podaci["slobodni"], list):
                    podaci["slobodni"] = []
                if "rezervirani" not in podaci or not isinstance(podaci["rezervirani"], dict):
                    podaci["rezervirani"] = {}
                if "poslani_podsjetnici" not in podaci or not isinstance(podaci["poslani_podsjetnici"], list):
                    podaci["poslani_podsjetnici"] = []
                return podaci
        except:
            pass
    return {"slobodni": [], "rezervirani": {}, "poslani_podsjetnici": []}

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
        
        for k in list(podaci_baza.get("rezervirani", {}).keys()):
            try:
                cisto_vrijeme = k[:16]
                pocetak = datetime.strptime(cisto_vrijeme, "%Y-%m-%d %H:%M")
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

# --- INICIJALIZACIJA I UKLANJANJE TISKARSKE GREŠKE ---
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

        if st.button("🚨 Očisti cijelu bazu podataka (Kreni ispočetka)"):
            podaci["slobodni"] = []
            podaci["rezervirani"] = {}
            podaci["poslani_podsjetnici"] = []
            spremi_podatke(podaci)
            st.warning("Baza podataka je u potpunosti obrisana!")
            st.rerun()

        # Vraćanje klasičnog tekstualnog unosa s izvornim formatom datuma
        novi_termin = st.text_input("Unesite termin u starom formatu (Format: GGGG-MM-DD HH:MM):", value=datetime.now().strftime("%Y-%m-%d %H:%M"))
        
        st.write("Odaberite program lekcije:")
        opcije_trajanja = {
            "35 minuta - POMOĆ U ČITANJU": "35 min - POMOĆ U ČITANJU",
            "45 minuta - BESPLATNO TESTIRANJE ČITANJA": "45 min - BESPLATNO TESTIRANJE ČITANJA",
            "90 minuta - BRZO ČITANJE I MUDRO UČENJE": "90 min - BRZO ČITANJE I MUDRO UČENJE"
        }
        odabrani_opis = st.radio("Označite željeni program:", list(opcije_trajanja.keys()))
        tekst_programa = opcije_trajanja[odabrani_opis]
        
        if st.button("➕ Kreiraj i dodaj termin u sustav"):
            # Generiranje točnog punog stringa za kalendar (UKLONJENA PROVJERA PREKLAPANJA)
            novi_termin_puni = f"{novi_termin} ({tekst_programa})"
            
            if novi_termin_puni in podaci.get("slobodni", []):
                st.error("Ovaj termin već postoji kao slobodan!")
            else:
                podaci["slobodni"].append(novi_termin_puni)
                spremi_podatke(podaci)
                st.session_state.admin_uspjeh = f"Uspješno generiran termin: {novi_termin_puni}"
                st.rerun()

        st.subheader("📋 Trenutno objavljeni slobodni termini (Moguće generirati 100+)")
        if not podaci.get("slobodni", []):
            st.info("Nema otvorenih slobodnih termina u sustavu.")
        else:
            for slobodan in sorted(podaci["slobodni"]):
                col_s1, col_s2 = st.columns(2)
                col_s1.write(f"🟢 {slobodan}")
                if col_s2.button("Ukloni termin", key=f"rem_{slobodan}"):
                    podaci["slobodni"].remove(slobodan)
                    spremi_podatke(podaci)
                    st.warning(f"Slobodan termin {slobodan} je trajno uklonjen.")


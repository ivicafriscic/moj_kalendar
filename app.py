import streamlit as st
import json
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

DATOTEKA_PODATAKA = "podaci.json"
ADMIN_LOZINKA = "Pletern1c@"  # <--- PROMIJENITE OVU LOZINKU ZA ADMINA

# --- PODACI ZA EMAIL POŠILJATELJA ---
SMTP_SERVER = "://gmail.com"
SMTP_PORT = 587
MOJ_EMAIL = "vas-email@gmail.com"            # <--- VAŠ GMAIL
MOJA_LOZINKA = "dyyhszecummfwkej" # <--- GOOGLE APP PASSWORD (16 SLOVA)
EMAIL_PONUDACA = "ana.koren1@gmail.com" # <--- GDJE STIŽE OBAVIJEST

def ucitaj_podatke():
    if os.path.exists(DATOTEKA_PODATAKA):
        with open(DATOTEKA_PODATAKA, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"slobodni": ["2026-10-15 10:00", "2026-10-16 14:00"], "rezervirani": {}}

def spremi_podatke(podaci):
    with open(DATOTEKA_PODATAKA, "w", encoding="utf-8") as f:
        json.dump(podaci, f, indent=4, ensure_ascii=False)

def posalji_email(termin, ime_klijenta, email_klijenta):
    naslov = f"Nova rezervacija termina: {termin}"
    tekst_poruke = f"Pozdrav,\n\nImate novu rezervaciju!\n\nTermin: {termin}\nKlijent: {ime_klijenta}\nE-mail klijenta: {email_klijenta}\n\nLijep pozdrav,\nVaš Web Sustav"
    msg = MIMEText(tekst_poruke, "plain", "utf-8")
    msg["Subject"] = naslov
    msg["From"] = MOJ_EMAIL
    msg["To"] = EMAIL_PONUDACA
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(MOJ_EMAIL, MOJA_LOZINKA)
        server.sendmail(MOJ_EMAIL, [EMAIL_PONUDACA], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Greška pri slanju emaila: {e}")
        return False

if "podaci" not in st.session_state:
    st.session_state.podaci = ucitaj_podatke()
podaci = st.session_state.podaci

st.set_page_config(page_title="Rezervacija Termina", page_icon="📅", layout="centered")
st.title("📅 Online Rezervacija Termina")

tab1, tab2 = st.tabs(["👤 Rezerviraj Termin", "🔐 Admin Panel"])

# --- PANEL ZA KLIJENTE (JAVNA WEB STRANICA) ---
with tab1:
    st.write("Dobrodošli! Odaberite jedan od slobodnih termina i unesite svoje podatke.")
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
                spremi_podatke(podaci)
                
                with st.spinner("Slanje e-mail obavijesti..."):
                    posalji_email(termin, ime, email_kupca)
                
                st.success(f"Uspješno ste rezervirali termin {termin}! Ponuđač je obaviješten.")
                st.rerun()

# --- ADMIN PANEL (ZAŠTIĆEN LOZINKOM) ---
with tab2:
    st.header("Administracija")
    upisana_lozinka = st.text_input("Unesite admin lozinku:", type="password")
    
    if upisana_lozinka == ADMIN_LOZINKA:
        st.success("Pristup odobren!")
        
        st.subheader("Dodaj novi termin")
        novi_termin = st.text_input("Format (GGGG-MM-DD HH:MM):", value=datetime.now().strftime("%Y-%m-%d %H:%M"))
        if st.button("Dodaj u kalendar"):
            try:
                datetime.strptime(novi_termin, "%Y-%m-%d %H:%M")
                if novi_termin in podaci["slobodni"] or novi_termin in podaci["rezervirani"]:
                    st.error("Ovaj termin već postoji!")
                else:
                    podaci["slobodni"].append(novi_termin)
                    spremi_podatke(podaci)
                    st.success(f"Dodan termin: {novi_termin}")
                    st.rerun()
            except ValueError:
                st.error("Krivi format datuma!")

        st.subheader("Pregled rezervacija")
        if not podaci["rezervirani"]:
            st.info("Nema rezerviranih termina.")
        else:
            for t, info in sorted(podaci["rezervirani"].items()):
                st.write(f"📅 **{t}** ➡️ 👤 {info['klijent']} ({info['email']})")
    elif upisana_lozinka != "":
        st.error("Pogrešna lozinka!")

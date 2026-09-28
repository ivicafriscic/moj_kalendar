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
MOJ_EMAIL = "ana.koren1@gmail.com"            # <--- VAŠ GMAIL
MOJA_LOZINKA = "dyyhszecummfwkej" # <--- GOOGLE APP PASSWORD (16 SLOVA)
EMAIL_PONUDACA = "brzocitanjeiucenjevz@gmail.com" # <--- GDJE STIŽE OBAVIJEST

import streamlit as st
import json
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import threading
import time

def ucitaj_podatke():
    if os.path.exists(DATOTEKA_PODATAKA):
        with open(DATOTEKA_PODATAKA, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"slobodni": ["2026-10-15 10:00", "2026-10-16 14:00"], "rezervirani": {}, "poslani_podsjetnici": []}

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
        print(f"Greška pri slanju emaila na {primatelj}: {e}")
        return False

def posalji_email_potvrde(termin, ime_klijenta, email_klijenta):
    naslov_ponudac = f"Nova rezervacija termina: {termin}"
    tekst_ponudac = f"Pozdrav,\n\nImate novu rezervaciju!\n\nTermin: {termin}\nKlijent: {ime_klijenta}\nE-mail klijenta: {email_klijenta}\n\nLijep pozdrav,\nVaš Web Sustav"
    posalji_email_genericki(EMAIL_PONUDACA, naslov_ponudac, tekst_ponudac)
    
    naslov_klijent = "Potvrda rezervacije termina - KREO"
    tekst_klijent = f"Poštovani/a {ime_klijenta},\n\nOvim putem potvrđujemo Vašu rezervaciju termina.\n\nDetalji:\n📅 Termin: {termin}\n\nU slučaju bilo kakvih promjena ili dodatnih pitanja, slobodno nas kontaktirajte na broj +385 91 568 2434 ili odgovaranjem na ovaj mail.\n\nHvala Vam na povjerenju!\n\nSrdačan pozdrav,\nVaš KREO tim"
    posalji_email_genericki(email_klijenta, naslov_klijent, tekst_klijent)

# --- POZADINSKI SUSTAV ZA PODSJETNIKE (4 SATA PRIJE) ---
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
                try:
                    vrijeme_termina = datetime.strptime(termin_str, "%Y-%m-%d %H:%M")
                    # Ako je termin unutar sljedeća 4 sata, a još nije prošao i podsjetnik nije poslan
                    if sada < vrijeme_termina <= za_cetiri_sata and termin_str not in podaci_baza["poslani_podsjetnici"]:
                        naslov_podsjetnik = "Podsjetnik na Vaš termin - KREO"
                        tekst_podsjetnik = f"Poštovani/a {info['klijent']},\n\nOvo je automatski podsjetnik da imate rezerviran termin kod nas za točno 4 sata.\n\n📅 Termin: {termin_str}\n\nRadujemo se Vašem dolasku!\n\nSrdačan pozdrav,\nVaš KREO tim"
                        
                        if posalji_email_genericki(info["email"], naslov_podsjetnik, tekst_podsjetnik):
                            podaci_baza["poslani_podsjetnici"].append(termin_str)
                            promjena = True
                except ValueError:
                    continue
            
            if promjena:
                spremi_podatke(podaci_baza)
        except Exception as e:
            print(f"Greška u pozadinskom podsjetniku: {e}")
        time.sleep(300) # Provjera svakih 5 minuta

# Pokretanje podsjetnika u zasebnoj pozadinskoj dretvi (samo jednom)
if not any(t.name == "KreoPodsjetnikThread" for t in threading.enumerate()):
    timer_thread = threading.Thread(target=provjeri_i_posalji_podsjetnike, name="KreoPodsjetnikThread", daemon=True)
    timer_thread.start()

# --- STREAMLIT APLIKACIJA ---
if "podaci" not in st.session_state:
    st.session_state.podaci = ucitaj_podatke()
podaci = st.session_state.podaci

st.set_page_config(page_title="KREO - Rezervacija Termina", page_icon="📅", layout="centered")

# --- KREO LOGOTIP ---
LOGO_URL = "https://kreo-vz.com"
st.image(LOGO_URL, width=250)

st.title("📅 Online Rezervacija Termina")

tab1, tab2 = st.tabs(["👤 Rezerviraj Termin", "🔐 Admin Panel"])

# --- PANEL ZA KLIJENTE (JAVNA STRANICA) ---
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
                    posalji_email_potvrde(termin, ime, email_kupca)
                
                st.success(f"Uspješno ste rezervirali termin {termin}! Potvrda je poslana na Vaš e-mail.")
                st.rerun()

    # --- KREO KONTAKTI ---
    st.markdown("---")
    st.subheader("📞 Kontakt informacije")
    st.markdown("""
    Ako trebate hitnu promjenu termina ili imate dodatnih upita, obratite nam se s povjerenjem:
    * **Telefon:** [+385 91 568 2434](tel:+385915682434)
    * **Web stranica:** [://kreo-vz.com](https://://kreo-vz.com)
    """)

# --- ADMIN PANEL (UPRAVLJANJE I BRISANJE) ---
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

        # --- OPCIJA BRISANJA/OTKAZIVANJA TERMINA ---
        st.subheader("Pregled i otkazivanje rezervacija")
        if not podaci["rezervirani"]:
            st.info("Nema rezerviranih termina.")
        else:
            for t, info in sorted(podaci["rezervirani"].items()):
                col1, col2 = st.columns([4, 1])
                col1.write(f"📅 **{t}** ➡️ 👤 {info['klijent']} ({info['email']})")
                # Gumb za brisanje pojedinog termina
                if col2.button("Otkaži", key=f"del_{t}"):
                    # Vraćamo termin među slobodne i brišemo podatke klijenta
                    podaci["slobodni"].append(t)
                    del podaci["rezervirani"][t]
                    if t in podaci.get("poslani_podsjetnici", []):
                        podaci["poslani_podsjetnici"].remove(t)
                    spremi_podatke(podaci)
                    st.warning(f"Termin {t} je otkazan i vraćen među slobodne.")
                    st.rerun()
    elif upisana_lozinka != "":
        st.error("Pogrešna lozinka!")


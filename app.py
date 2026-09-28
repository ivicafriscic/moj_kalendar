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

DATOTEKA_PODATAKA = "podaci.json"
ADMIN_LOZINKA = "Pletern1c@"  # <--- PROMIJENITE OVU LOZINKU ZA ADMINA

# --- PODACI ZA EMAIL POŠILJATELJA ---
SMTP_SERVER = "://gmail.com"
SMTP_PORT = 587
MOJ_EMAIL = "ana.koren1@gmail.com"            # <--- VAŠ GMAIL
MOJA_LOZINKA = "dyyhszecummfwkej" # <--- GOOGLE APP PASSWORD (16 SLOVA)
EMAIL_PONUDACA = "brzocitanjeiucenjevz@gmail.com" # <--- GDJE STIŽE OBAVIJEST

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
    
    naslov_klijent = "Potvrda rezervacije termina - Škola brzog čitanja i mudrog učenja Varaždin"
    tekst_klijent = f"Poštovani/a {ime_klijenta},\n\nOvim putem potvrđujemo Vašu rezervaciju termina.\n\nDetalji:\n📅 Termin: {termin}\n\nU slučaju bilo kakvih promjena ili dodatnih pitanja, slobodno nas kontaktirajte odgovaranjem na ovaj mail ili putem naših društvenih mreža.\n\nHvala Vam na povjerenju!\n\nSrdačan pozdrav,\nŠkola brzog čitanja i mudrog učenja Varaždin"
    posalji_email_genericki(email_klijenta, naslov_klijent, tekst_klijent)

# --- Pozadinski podsjetnici ---
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
                    if sada < vrijeme_termina <= za_cetiri_sata and termin_str not in podaci_baza["poslani_podsjetnici"]:
                        naslov_podsjetnik = "Podsjetnik na Vaš termin"
                        tekst_podsjetnik = f"Poštovani/a {info['klijent']},\n\nOvo je automatski podsjetnik da imate rezerviran termin kod nas za točno 4 sata.\n\n📅 Termin: {termin_str}\n\nRadujemo se Vašem dolasku!\n\nSrdačan pozdrav,\nŠkola brzog čitanja i mudrog učenja Varaždin"
                        
                        if posalji_email_genericki(info["email"], naslov_podsjetnik, tekst_podsjetnik):
                            podaci_baza["poslani_podsjetnici"].append(termin_str)
                            promjena = True
                except ValueError:
                    continue
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

# --- PRIMJENA LOKALNOG LOGOTIPA ---
IME_SLIKE = "logo.png"
if os.path.exists(IME_SLIKE):
    st.image(IME_SLIKE, use_container_width=True)
else:
    st.header("Škola brzog čitanja i mudrog učenja Varaždin")

st.title("📅 Online Rezervacija Termina")

tab1, tab2 = st.tabs(["👤 Rezerviraj Termin", "🔐 Admin Panel"])

with tab1:
    st.write("Dobrodošli! Odaberite jedan od slobodnih termina i unesite svoje podatke.")
    
    # Ako postoji spremljena obavijest o uspjehu u memoriji, prikaži je ovdje (izvan forme)
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
                # 1. Odmah upiši u bazu i makni termin da netko drugi ne klikne u isto vrijeme
                podaci["slobodni"].remove(termin)
                podaci["rezervirani"][termin] = {"klijent": ime, "email": email_kupca}
                spremi_podatke(podaci)
                
                # 2. Pokreni slanje maila u zasebnoj brzoj dretvi kako ne bi zablokiralo sučelje
                email_thread = threading.Thread(target=posalji_email_potvrde, args=(termin, ime, email_kupca))
                email_thread.start()
                
                # 3. Spremi poruku i osvježi stranicu
                st.session_state.uspjeh_poruka = f"Uspješno ste rezervirali termin {termin}! Potvrda se šalje na Vaš e-mail."
                st.rerun()

    # --- KREO KONTAKTI ---
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

        st.subheader("Pregled i otkazivanje rezervacija")
        if not podaci["rezervirani"]:
            st.info("Nema rezerviranih termina.")
        else:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Rezervacije"
            ws.append(["Datum i Vrijeme", "Ime i Prezime", "E-mail klijenta"])
            
            for t, info in sorted(podaci["rezervirani"].items()):
                ws.append([t, info['klijent'], info['email']])
                
                col1, col2 = st.columns(2)  # <-- ISPRAVLJENO: Broj je unutra!
                col1.write(f"📅 **{t}** ➡️ 👤 {info['klijent']} ({info['email']})")
                if col2.button("Otkaži", key=f"del_{t}"):
                    podaci["slobodni"].append(t)
                    if t in podaci.get("rezervirani", {}):
                        del podaci["rezervirani"][t]
                    if t in podaci.get("poslani_podsjetnici", []):
                        podaci["poslani_podsjetnici"].remove(t)
                    spremi_podatke(podaci)
                    st.warning(f"Termin {t} je otkazan.")
                    st.rerun()
            
            excel_data = io.BytesIO()
            wb.save(excel_data)
            excel_data.seek(0)
            
            st.markdown("---")
            st.download_button(
                label="📥 Preuzmi Excel tablicu",
                data=excel_data,
                file_name=f"rezervacije_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    elif upisana_lozinka != "":
        st.error("Pogrešna lozinka!")


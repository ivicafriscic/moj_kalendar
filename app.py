
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
import urllib.parse  # DODANO ZA SIGURAN LINK PREMA GOOGLE KALENDARU

DATOTEKA_PODATAKA = "podaci.json"
ADMIN_LOZINKA = "Pletern1c@"  # <--- PROMIJENITE OVU LOZINKU ZA ADMINA

# --- PODACI ZA EMAIL POŠILJATELJA ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
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
                    # Uzimamo samo prvi dio (prije zagrade za trajanje)
                    cisti_termin = termin_str.split(" (")[0]
                    vrijeme_termina = datetime.strptime(cisti_termin, "%Y-%m-%d %H:%M")
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
        
        # --- ISPRAVLJENO GRAFIČKO GENERIRANJE TERMINA ---
        st.subheader("🛠️ Alat za generiranje termina")
        
        # Pamćenje odabranog trajanja kroz gumbe
        if "odabrano_trajanje" not in st.session_state:
            st.session_state.odabrano_trajanje = 45 # Zadana vrijednost

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
            
        st.info(f"Trenutno označeno trajanje: **{st.session_state.odabrano_trajanje} minuta**")
        
        # GUMB KOJI STVARNO ZAPISUJE TERMIN
        if st.button("➕ Kreiraj i dodaj termin u sustav"):
            pocetak_str = f"{odabrani_datum} {odabrano_vrijeme}"
            pocetak_dt = datetime.strptime(pocetak_str, "%Y-%m-%d %H:%M")
            novi_termin_puni = f"{pocetak_dt.strftime('%Y-%m-%d %H:%M')} ({st.session_state.odabrano_trajanje} min)"
            
            if novi_termin_puni in podaci["slobodni"] or novi_termin_puni in podaci["rezervirani"]:
                st.error("Ovaj termin već postoji!")
            else:
                podaci["slobodni"].append(novi_termin_puni)
                spremi_podatke(podaci)
                st.success(f"Uspješno stvoren i objavljen termin: {novi_termin_puni}")
                st.rerun()

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
                
                st.markdown(f"📅 **{t}** ➡️ 👤 {info['klijent']} ({info['email']})")

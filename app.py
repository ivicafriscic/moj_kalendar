import streamlit as st
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import urllib.parse
import os
import json

DATOTEKA_BAZE = "lokalna_baza.json"
ADMIN_LOZINKA = "Ivo"  # <--- Vaša lozinka za ulaz u Admin Panel

# --- Službeni Google SMTP parametri ---
SMTP_SERVER = "://gmail.com"             
SMTP_PORT = 465
MOJ_EMAIL = "ana.koren1@gmail.com"            # Vaš Gmail račun preko kojeg se šalje
MOJA_LOZINKA = "dyyhszecummfwkej"             # Točna Google lozinka aplikacije (16 slova)
EMAIL_PONUDACA = "friscicivica69@gmail.com" # Mail na koji primate obavijesti o novoj rezervaciji

def ucitaj_trajne_podatke():
    if os.path.exists(DATOTEKA_BAZE):
        try:
            with open(DATOTEKA_BAZE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"slobodni": [], "rezervirani": {}, "podsjetnici": []}

def spremi_trajne_podatke(podaci_za_bazu):
    try:
        with open(DATOTEKA_BAZE, "w", encoding="utf-8") as f:
            json.dump(podaci_za_bazu, f, indent=4, ensure_ascii=False)
    except:
        pass

# --- INICIJALIZACIJA LOKALNE MEMORIJE ---
if "baza_lokalna" not in st.session_state:
    st.session_state.baza_lokalna = ucitaj_trajne_podatke()

baza = st.session_state.baza_lokalna

def posalji_email_genericki(primatelj, naslov, tekst):
    try:
        msg = MIMEText(tekst, "plain", "utf-8")
        msg["Subject"] = naslov
        msg["From"] = MOJ_EMAIL
        msg["To"] = primatelj
        
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=15)
        server.ehlo()
        server.login(MOJ_EMAIL, MOJA_LOZINKA)
        server.sendmail(MOJ_EMAIL, [primatelj], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP Greška pri slanju: {e}")
        return False

def posalji_email_potvrde_direktno(termin, ime_klijenta, email_klijenta):
    try:
        cisto_v_cal = termin[:16]
        p_pocetak = datetime.strptime(cisto_v_cal, "%Y-%m-%d %H:%M")
        t_trajanje = 45
        if "35 min" in termin: t_trajanje = 35
        elif "90 min" in termin: t_trajanje = 90
        p_kraj = p_pocetak + timedelta(minutes=t_trajanje)
        
        g_start = p_pocetak.strftime("%Y%m%dT%H%M%S")
        g_end = p_kraj.strftime("%Y%m%dT%H%M%S")
        g_naslov = urllib.parse.quote(f"Nastava: {ime_klijenta}")
        g_opis = urllib.parse.quote(f"Polaznik: {ime_klijenta}\nOpis: {termin}")
        
        google_cal_link = f"https://google.com{g_naslov}&dates={g_start}/{g_end}&details={g_opis}"
        dodatak_link = f"\n\n📅 Dodaj ovaj termin u svoj Google kalendar jednim klikom:\n{google_cal_link}"
    except:
        dodatak_link = ""

    naslov_ponudac = f"Nova rezervacija termina: {termin}"
    tekst_ponudac = f"Pozdrav,\n\nImate novu rezervaciju!\n\nTermin: {termin}\nKlijent: {ime_klijenta}\nE-mail klijenta: {email_klijenta}{dodatak_link}\n\nLijep pozdrav,\nVaš Web Sustav"
    
    naslov_klijent = "Potvrda rezervacije termina - Škola brzog čitanja i mudrog učenja Varaždin"
    tekst_klijent = f"Poštovani/a {ime_klijenta},\n\nOvim putem potvrđujemo Vašu rezervaciju termina.\n\nDetalji:\n📅 Termin: {termin}{dodatak_link}\n\nU slučaju bilo kakvih promjena ili dodatnih pitanja, slobodno nas kontaktirajte odgovaranjem na ovaj mail ili putem naših društvenih mreža.\n\nHvala Vam na povjerenju!\n\nSrdačan pozdrav,\nŠkola brzog čitanja i mudrog učenja Varaždin"
    
    posalji_email_genericki(EMAIL_PONUDACA, naslov_ponudac, tekst_ponudac)
    posalji_email_genericki(email_klijenta, naslov_klijent, tekst_klijent)
    return True

def provjeri_i_posalji_podsjetnike_brzo():
    try:
        sada = datetime.now()
        za_cetiri_sata = sada + timedelta(hours=4)
        promjena = False
        
        rezervirani_rjecnik = baza.get("rezervirani", {})
        for stavka in list(rezervirani_rjecnik.keys()):
            try:
                cisto_vrijeme = stavka[:16]
                pocetak = datetime.strptime(cisto_vrijeme, "%Y-%m-%d %H:%M")
                if sada < pocetak <= za_cetiri_sata and stavka not in baza.get("podsjetnici", []):
                    info = rezervirani_rjecnik.get(stavka)
                    if info:
                        naslov_podsjetnik = "Podsjetnik na Vaš termin"
                        tekst_podsjetnik = f"Poštovani/a {info['klijent']},\n\nOvo je automatski podsjetnik da imate rezerviran termin kod nas za točno 4 sata.\n\n📅 Termin: {stavka}\n\nRadujemo se Vašem dolasku!\n\nSrdačan pozdrav,\nVaš KREO tim"
                        if posalji_email_genericki(info["email"], naslov_podsjetnik, tekst_podsjetnik):
                            baza["podsjetnici"].append(stavka)
                            promjena = True
            except:
                continue
        if promjena:
            spremi_trajne_podatke(baza)
    except:
        pass

provjeri_i_posalji_podsjetnike_brzo()

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

    slobodni_prikaz = [t for t in baza.get("slobodni", []) if t not in baza.get("rezervirani", {})]
    
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
                    baza["slobodni"].remove(termin)
                    baza["rezervirani"][termin] = {"klijent": ime, "email": email_kupca}
                    
                    posalji_email_potvrde_direktno(termin, ime, email_kupca)
                    spremi_trajne_podatke(baza)
                    st.session_state.uspjeh_poruka = f"Uspješno ste rezervirali termin {termin}! Potvrda je poslana na Vaš e-mail."
                    st.rerun()

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

        if st.button("🚨 Očisti cijelu listu (Kreni ispočetka)"):
            baza["slobodni"] = []
            baza["rezervirani"] = {}
            baza["podsjetnici"] = []
            spremi_trajne_podatke(baza)
            st.warning("Svi podaci su u potpunosti očišćeni!")
            st.rerun()

        col_d, col_v = st.columns(2)
        odabrani_datum = col_d.date_input("1. Odaberite datum:", datetime.now())
        sati_opcije = [f"{h:02d}:{m:02d}" for h in range(8, 21) for m in (0, 15, 30, 45)]
        odabrano_vrijeme = col_v.selectbox("2. Odaberite vrijeme početka:", sati_opcije)
        
        st.write("3. Označite program lekcije:")
        opcije_trajanja = {
            "35 minuta - POMOĆ U ČITANJU": "35 min - POMOĆ U ČITANJU",
            "45 minuta - BESPLATNO TESTIRANJE ČITANJA": "45 min - BESPLATNO TESTIRANJE ČITANJA",
            "90 minuta - BRZO ČITANJE I MUDRO UČENJE": "90 min - BRZO ČITANJE I MUDRO UČENJE"
        }
        odabrani_opis = st.radio("Programi:", list(opcije_trajanja.keys()))
        text_programa = opcije_trajanja[odabrani_opis]
        
        if st.button("➕ Kreiraj i dodaj termin u sustav"):
            vrijeme_iso = f"{odabrani_datum} {odabrano_vrijeme}"
            novi_termin_puni = f"{vrijeme_iso} ({text_programa})"
            
            if novi_termin_puni in baza.get("slobodni", []):
                st.error("Ovaj termin već postoji kao slobodan!")
            else:
                baza["slobodni"].append(novi_termin_puni)
                spremi_trajne_podatke(baza)
                st.session_state.admin_uspjeh = f"Uspješno generiran termin: {novi_termin_puni}"
                st.rerun()

        st.subheader("📋 Trenutno objavljeni slobodni termini")
        slobodni_lista_prikaz = baza.get("slobodni", [])
        if not slobodni_lista_prikaz:
            st.info("Nema otvorenih slobodnih termina u sustavu.")
        else:
            st.dataframe(slobodni_lista_prikaz, use_container_width=True)
            termin_za_uklanjanje = st.selectbox("Odaberite termin ako ga želite obrisati:", sorted(slobodni_lista_prikaz))
            if st.button("❌ Trajno ukloni odabrani slobodan termin"):
                baza["slobodni"].remove(termin_za_uklanjanje)
                spremi_trajne_podatke(baza)
                st.warning(f"Slobodan termin {termin_za_uklanjanje} je uspješno obrisan.")
                st.rerun()

        st.subheader("📋 Pregled zauzetih rezervacija (Iskorišteni termini)")
        rezervirani_tablica = baza.get("rezervirani", {})
        if not rezervirani_tablica:
            st.info("Nema rezerviranih termina.")
        else:
            prikaz_rezervacija = []
            for t, info in rezervirani_tablica.items():
                prikaz_rezervacija.append({"Termin nastave": t, "Klijent": info["klijent"], "E-mail": info["email"]})
            st.dataframe(prikaz_rezervacija, use_container_width=True)
            
            termin_za_otkazivanje = st.selectbox("Odaberite rezervaciju ako je želite otkazati:", sorted(list(rezervirani_tablica.keys())))
            if st.button("❌ Trajno otkaži odabranu rezervaciju"):
                baza["slobodni"].append(termin_za_otkazivanje)
                del baza["rezervirani"][termin_za_otkazivanje]
                if termin_za_otkazivanje in baza.get("podsjetnici", []):
                    baza["podsjetnici"].remove(termin_za_otkazivanje)
                spremi_trajne_podatke(baza)
                st.warning(f"Rezervacija {termin_za_otkazivanje} je uspješno otkazana.")
                st.rerun()
            
    elif upisana_lozinka != "":
        st.error("Pogrešna lozinka!")

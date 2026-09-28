import streamlit as st
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import io
import openpyxl
import urllib.parse

ADMIN_LOZINKA = "Ivo"  # <--- Vaša lozinka za ulaz u Admin Panel

# --- PODACI ZA EMAIL POŠILJATELJA ---
SMTP_SERVER = "74.125.140.108"              
SMTP_PORT = 465
MOJ_EMAIL = "ana.koren1@gmail.com"            # Vaš Gmail račun preko kojeg se šalje
MOJA_LOZINKA = "dyyhszecummfwkej"             # Vaša Google aplikacijska lozinka (16 slova)
EMAIL_PONUDACA = "brzocitanjeiucenjevz@gmail.com" # Mail na koji primate obavijesti o novoj rezervaciji

# --- POTPUNO NOVI MEMORIJSKI SUSTAV (BEZ DATOTEKA) ---
if "baza_slobodni" not in st.session_state:
    st.session_state.baza_slobodni = []
if "baza_rezervirani" not in st.session_state:
    st.session_state.baza_rezervirani = {}
if "baza_podsjetnici" not in st.session_state:
    st.session_state.baza_podsjetnici = []

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
    
    ok_vlasnik = posalji_email_genericki(EMAIL_PONUDACA, naslov_ponudac, tekst_ponudac)
    ok_klijent = posalji_email_genericki(email_klijenta, naslov_klijent, tekst_klijent)
    return ok_vlasnik and ok_klijent

def provjeri_i_posalji_podsjetnike_brzo():
    try:
        sada = datetime.now()
        za_cetiri_sata = sada + timedelta(hours=4)
        
        for k in list(st.session_state.baza_rezervirani.keys()):
            try:
                cisto_vrijeme = k[:16]
                pocetak = datetime.strptime(cisto_vrijeme, "%Y-%m-%d %H:%M")
                if sada < pocetak <= za_cetiri_sata and k not in st.session_state.baza_podsjetnici:
                    info = st.session_state.baza_rezervirani.get(k)
                    if info:
                        naslov_podsjetnik = "Podsjetnik na Vaš termin"
                        tekst_podsjetnik = f"Poštovani/a {info['klijent']},\n\nOvo je automatski podsjetnik da imate rezerviran termin kod nas za točno 4 sata.\n\n📅 Termin: {k}\n\nRadujemo se Vašem dolasku!\n\nSrdačan pozdrav,\nVaš KREO tim"
                        if posalji_email_genericki(info["email"], naslov_podsjetnik, tekst_podsjetnik):
                            st.session_state.baza_podsjetnici.append(k)
            except:
                continue
    except:
        pass

# Pokretanje brze tihe provjere podsjetnika
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

    slobodni_prikaz = [t for t in st.session_state.baza_slobodni if t not in st.session_state.baza_rezervirani]
    
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
                    st.session_state.baza_slobodni.remove(termin)
                    st.session_state.baza_rezervirani[termin] = {"klijent": ime, "email": email_kupca}
                    with st.spinner("Slanje e-mail obavijesti..."):
                        slanje_uspjelo = posalji_email_potvrde_direktno(termin, ime, email_kupca)
                    if slanje_uspjelo:
                        st.session_state.uspjeh_poruka = f"Uspješno ste rezervirali termin {termin}! Potvrda je poslana na Vaš e-mail."
                        st.rerun()
                    else:
                        st.session_state.baza_slobodni.append(termin)
                        del st.session_state.baza_rezervirani[termin]

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
            st.session_state.baza_slobodni = []
            st.session_state.baza_rezervirani = {}
            st.session_state.baza_podsjetnici = []
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
        tekst_programa = opcije_trajanja[odabrani_opis]
        
        if st.button("➕ Kreiraj i dodaj termin u sustav"):
            vrijeme_iso = f"{odabrani_datum} {odabrano_vrijeme}"
            novi_termin_puni = f"{vrijeme_iso} ({tekst_programa})"
            
            if novi_termin_puni in st.session_state.baza_slobodni:
                st.error("Ovaj termin već postoji kao slobodan!")
            else:
                st.session_state.baza_slobodni.append(novi_termin_puni)
                st.session_state.admin_uspjeh = f"Uspješno generiran termin: {novi_termin_puni}"
                st.rerun()

        st.subheader("📋 Trenutno objavljeni slobodni termini")
        if not st.session_state.baza_slobodni:
            st.info("Nema otvorenih slobodnih termina u sustavu.")
        else:
            for slobodan in sorted(st.session_state.baza_slobodni):
                col_s1, col_s2 = st.columns(2)
                col_s1.write(f"🟢 {slobodan}")
                if col_s2.button("Ukloni slobodan", key=f"rem_{slobodan}"):
                    st.session_state.baza_slobodni.remove(slobodan)
                    st.warning(f"Slobodan termin {slobodan} je uklonjen.")
                    st.rerun()

        st.subheader("📋 Pregled zauzetih rezervacija (Iskorišteni termini)")
        if not st.session_state.baza_rezervirani:

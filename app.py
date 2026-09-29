import streamlit as st
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import io
import openpyxl
import urllib.parse
import os
import json

DATOTEKA_BAZE = "lokalna_baza.json"
ADMIN_LOZINKA = "Ivo"  # <--- Vaša lozinka za ulaz u Admin Panel

# --- PODACI ZA EMAIL POŠILJATELJA ---
SMTP_SERVER = "smtp.gmail.com"             
SMTP_PORT = 465
MOJ_EMAIL = "ana.koren1@gmail.com"            # Vaš Gmail račun preko kojeg se šalje
MOJA_LOZINKA = "dyyhszecummfwkej"             # Vaša Google aplikacijska lozinka (16 slova)
EMAIL_PONUDACA = "friscicivica69@gmail.com" # Mail na koji primate obavijesti o novoj rezervaciji

def ucitaj_trajne_podatke():
    if os.path.exists(DATOTEKA_BAZE):
        try:
            with open(DATOTEKA_BAZE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"slobodni": [], "rezervirani": {}, "podsjetnici": []}

def spremi_trajne_podatke(podaci):
    try:
        with open(DATOTEKA_BAZE, "w", encoding="utf-8") as f:
            json.dump(podaci, f, indent=4, ensure_ascii=False)
    except:
        pass

# --- INICIJALIZACIJA LOKALNE MEMORIJE ---
if "baza_lokalna" not in st.session_state:
    st.session_state.baza_lokalna = ucitaj_trajne_podatke()

baza = st.session_state.baza_lokalna

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
        # Uzimamo datum i vrijeme iz početka termina
        cisto_v_cal = termin[:16]
        p_pocetak = datetime.strptime(cisto_v_cal, "%Y-%m-%d %H:%M")

        # Zadano trajanje je 45 minuta
        t_trajanje = 45

        if "35 min" in termin:
            t_trajanje = 35
        elif "90 min" in termin:
            t_trajanje = 90

        p_kraj = p_pocetak + timedelta(minutes=t_trajanje)

        # Google Calendar format datuma
        g_start = p_pocetak.strftime("%Y%m%dT%H%M%S")
        g_end = p_kraj.strftime("%Y%m%dT%H%M%S")

        # Podaci za Google Calendar
        g_naslov = urllib.parse.quote(
            f"Nastava: {ime_klijenta}"
        )

        g_opis = urllib.parse.quote(
            f"Polaznik: {ime_klijenta}\n"
            f"Termin: {termin}"
        )

        # Ispravan Google Calendar link
        google_cal_link = (
            "https://calendar.google.com/calendar/render"
            "?action=TEMPLATE"
            f"&text={g_naslov}"
            f"&dates={g_start}/{g_end}"
            f"&details={g_opis}"
        )

        dodatak_link = (
            "\n\n"
            "📅 Dodaj ovaj termin u svoj Google kalendar jednim klikom:\n"
            f"{google_cal_link}"
        )

    except (ValueError, TypeError, IndexError):
        # Ako termin nije u očekivanom formatu,
        # email se i dalje šalje bez Calendar linka.
        dodatak_link = ""

    # ---------------------------------------------------------
    # EMAIL VLASNIKU / PONUDITELJU
    # ---------------------------------------------------------

    naslov_ponudac = f"Nova rezervacija termina: {termin}"

    tekst_ponudac = (
        f"Pozdrav,\n\n"
        f"Imate novu rezervaciju!\n\n"
        f"Termin: {termin}\n"
        f"Klijent: {ime_klijenta}\n"
        f"E-mail klijenta: {email_klijenta}"
        f"{dodatak_link}\n\n"
        f"Lijep pozdrav,\n"
        f"Vaš Web Sustav"
    )

    # ---------------------------------------------------------
    # EMAIL KLIJENTU
    # ---------------------------------------------------------

    naslov_klijent = (
        "Potvrda rezervacije termina - "
        "Škola brzog čitanja i mudrog učenja Varaždin"
    )

    tekst_klijent = (
        f"Poštovani/a {ime_klijenta},\n\n"
        f"Ovim putem potvrđujemo Vašu rezervaciju termina.\n\n"
        f"Detalji:\n"
        f"📅 Termin: {termin}"
        f"{dodatak_link}\n\n"
        f"U slučaju bilo kakvih promjena ili dodatnih pitanja, "
        f"slobodno nas kontaktirajte odgovaranjem na ovaj mail "
        f"ili putem naših društvenih mreža.\n\n"
        f"Hvala Vam na povjerenju!\n\n"
        f"Srdačan pozdrav,\n"
        f"Škola brzog čitanja i mudrog učenja Varaždin"
    )

    # ---------------------------------------------------------
    # SLANJE EMAILOVA
    # ---------------------------------------------------------

    ok_vlasnik = posalji_email_genericki(
        EMAIL_PONUDACA,
        naslov_ponudac,
        tekst_ponudac
    )

    ok_klijent = posalji_email_genericki(
        email_klijenta,
        naslov_klijent,
        tekst_klijent
    )

    return ok_vlasnik and ok_klijent

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
                    with st.spinner("Slanje e-mail obavijesti..."):
                        slanje_uspjelo = posalji_email_potvrde_direktno(termin, ime, email_kupca)
                    if slanje_uspjelo:
                        spremi_trajne_podatke(baza)
                        st.session_state.uspjeh_poruka = f"Uspješno ste rezervirali termin {termin}! Potvrda je poslana na Vaš e-mail."
                        st.rerun()
                    else:
                        baza["slobodni"].append(termin)
                        del baza["rezervirani"][termin]

    st.markdown("---")
    st.subheader("🔗 Kontakt i društvene mreže")
    st.markdown("""
    Pratite naš rad ili nas kontaktirajte putem interneta:
    * **Web stranica:** [www.kreo-vz.com](https://kreo-vz.com)
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
        tekst_programa = opcije_trajanja[odabrani_opis]
        
        if st.button("➕ Kreiraj i dodaj termin u sustav"):
            vrijeme_iso = f"{odabrani_datum} {odabrano_vrijeme}"
            novi_termin_puni = f"{vrijeme_iso} ({tekst_programa})"
            
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
            for slobodan in sorted(slobodni_lista_prikaz):
                col_s1, col_s2 = st.columns(2)
                col_s1.write(f"🟢 {slobodan}")
                if col_s2.button("Ukloni slobodan", key=f"rem_{slobodan}"):
                    baza["slobodni"].remove(slobodan)
                    spremi_trajne_podatke(baza)
                    st.warning(f"Slobodan termin {slobodan} je uklonjen.")
                    st.rerun()

        st.subheader("📋 Pregled zauzetih rezervacija (Iskorišteni termini)")
        rezervirani_tablica = baza.get("rezervirani", {})
        if not rezervirani_tablica:
            st.info("Nema rezerviranih termina.")
        else:
            for t, info in sorted(rezervirani_tablica.items()):
                st.markdown(f"📅 **{t}** ➡️ 👤 {info['klijent']} ({info['email']})")
                col_g1, col_g2 = st.columns(2)
                
                try:
                    cisto_v_cal = t[:16]
                    p_pocetak = datetime.strptime(cisto_v_cal, "%Y-%m-%d %H:%M")
                    t_trajanje = 45
                    if "35 min" in t: t_trajanje = 35
                    elif "90 min" in t: t_trajanje = 90
                    p_kraj = p_pocetak + timedelta(minutes=t_trajanje)
                    
                    g_start = p_pocetak.strftime("%Y%m%dT%H%M%S")
                    g_end = p_kraj.strftime("%Y%m%dT%H%M%S")
                    g_naslov = urllib.parse.quote(f"Nastava: {info['klijent']}")
                    g_opis = urllib.parse.quote(f"Polaznik: {info['klijent']}\nOpis: {t}")
                    google_cal_link = (
                    "https://calendar.google.com/calendar/render"
                    "?action=TEMPLATE"
                    f"&text={g_naslov}"
                    f"&dates={g_start}/{g_end}"
                    f"&details={g_opis}"
                    )
                    col_g1.markdown(f"[📅 Dodaj u Google kalendar]({google_cal_link})")
                except:
                    col_g1.write("📅 Poveznica stvorena")

                if col_g2.button("Otkaži rezervaciju", key=f"del_{t}"):
                    baza["slobodni"].append(t)
                    del baza["rezervirani"][t]
                    spremi_trajne_podatke(baza)
                    st.warning(f"Rezervacija {t} je otkazana.")
                    st.rerun()
                st.markdown("---")
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Rezervacije"
            ws.append(["Datum i Vrijeme", "Ime i Prezime", "E-mail klijenta"])
            for t, info in rezervirani_tablica.items():
                ws.append([t, info['klijent'], info['email']])
            
            excel_data = io.BytesIO()
            wb.save(excel_data)
            excel_data.seek(0)
            st.download_button(
                label="📥 Preuzmi Excel tablicu rezervacija",
                data=excel_data,
                file_name=f"rezervacije_{datetime.now().strftime('%d.%m.%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    elif upisana_lozinka != "":
        st.error("Pogrešna lozinka!")




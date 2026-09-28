import streamlit as st
import json
import os
import re
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText


# ============================================================
# POSTAVKE
# ============================================================

DATOTEKA_PODATAKA = "podaci.json"

# VAŽNO:
# Lozinke i Gmail podatke nemojte stavljati direktno u ovaj kod.
# Postavite ih u Streamlit Secrets ili kao environment varijable.

ADMIN_LOZINKA = st.secrets.get("ADMIN_LOZINKA", os.getenv("ADMIN_LOZINKA", ""))

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
MOJ_EMAIL = st.secrets.get("MOJ_EMAIL", os.getenv("MOJ_EMAIL", ""))
MOJA_LOZINKA = st.secrets.get("MOJA_LOZINKA", os.getenv("MOJA_LOZINKA", ""))
EMAIL_PONUDACA = st.secrets.get(
    "EMAIL_PONUDACA",
    os.getenv("EMAIL_PONUDACA", "")
)

IME_SLIKE = "logo.png"


# ============================================================
# RAD S BAZOM
# ============================================================

def prazna_baza():
    return {
        "slobodni": [],
        "rezervirani": {},
        "poslani_podsjetnici": [],
        "metapodaci": {}
    }


def ucitaj_podatke():
    if not os.path.exists(DATOTEKA_PODATAKA):
        return prazna_baza()

    try:
        with open(DATOTEKA_PODATAKA, "r", encoding="utf-8") as f:
            podaci = json.load(f)

        if not isinstance(podaci, dict):
            return prazna_baza()

        if "slobodni" not in podaci or not isinstance(podaci["slobodni"], list):
            podaci["slobodni"] = []

        if "rezervirani" not in podaci or not isinstance(podaci["rezervirani"], dict):
            podaci["rezervirani"] = {}

        if "poslani_podsjetnici" not in podaci or not isinstance(
            podaci["poslani_podsjetnici"], list
        ):
            podaci["poslani_podsjetnici"] = []

        if "metapodaci" not in podaci or not isinstance(
            podaci["metapodaci"], dict
        ):
            podaci["metapodaci"] = {}

        return podaci

    except Exception:
        return prazna_baza()


def spremi_podatke(podaci):
    with open(DATOTEKA_PODATAKA, "w", encoding="utf-8") as f:
        json.dump(podaci, f, indent=4, ensure_ascii=False)


# ============================================================
# EMAIL
# ============================================================

def email_postavke_ispravne():
    return bool(MOJ_EMAIL and MOJA_LOZINKA and EMAIL_PONUDACA)


def posalji_email_genericki(primatelj, naslov, tekst):
    if not email_postavke_ispravne():
        print("Email postavke nisu podešene.")
        return False

    if not primatelj:
        return False

    try:
        msg = MIMEText(tekst, "plain", "utf-8")
        msg["Subject"] = naslov
        msg["From"] = MOJ_EMAIL
        msg["To"] = primatelj

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.login(MOJ_EMAIL, MOJA_LOZINKA)
            server.sendmail(MOJ_EMAIL, [primatelj], msg.as_string())

        return True

    except Exception as e:
        print(f"Greška pri slanju emaila na {primatelj}: {e}")
        return False


def posalji_email_potvrde_direktno(termin, ime_klijenta, email_klijenta):
    naslov_ponudac = f"Nova rezervacija termina: {termin}"

    tekst_ponudac = (
        "Pozdrav,\n\n"
        "Imate novu rezervaciju!\n\n"
        f"Termin: {termin}\n"
        f"Klijent: {ime_klijenta}\n"
        f"E-mail klijenta: {email_klijenta}\n\n"
        "Lijep pozdrav,\n"
        "Vaš Web Sustav"
    )

    naslov_klijent = (
        "Potvrda rezervacije termina - "
        "Škola brzog čitanja i mudrog učenja Varaždin"
    )

    tekst_klijent = (
        f"Poštovani/a {ime_klijenta},\n\n"
        "Ovim putem potvrđujemo Vašu rezervaciju termina.\n\n"
        "Detalji:\n"
        f"📅 Termin: {termin}\n\n"
        "U slučaju bilo kakvih promjena ili dodatnih pitanja, "
        "slobodno nas kontaktirajte odgovaranjem na ovaj mail ili "
        "putem naših društvenih mreža.\n\n"
        "Hvala Vam na povjerenju!\n\n"
        "Srdačan pozdrav,\n"
        "Škola brzog čitanja i mudrog učenja Varaždin"
    )

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


def provjeri_i_posalji_podsjetnike(podaci_baza):
    """
    Šalje podsjetnik za termine koji počinju unutar sljedeća 4 sata.

    Napomena:
    Streamlit aplikacija mora biti pokrenuta/reloadana da bi se ova
    provjera izvršila.
    """
    try:
        promjena = False
        sada = datetime.now()
        za_cetiri_sata = sada + timedelta(hours=4)

        for k, v in list(podaci_baza.get("metapodaci", {}).items()):
            try:
                pocetak_text = v.get("pocetak")

                if not pocetak_text:
                    continue

                pocetak = datetime.strptime(
                    pocetak_text,
                    "%Y-%m-%d %H:%M"
                )

                if (
                    sada < pocetak <= za_cetiri_sata
                    and k not in podaci_baza.get(
                        "poslani_podsjetnici", []
                    )
                ):
                    info = podaci_baza.get("rezervirani", {}).get(k)

                    if info:
                        naslov_podsjetnik = "Podsjetnik na Vaš termin"

                        tekst_podsjetnik = (
                            f"Poštovani/a {info.get('klijent', '')},\n\n"
                            "Ovo je automatski podsjetnik da imate "
                            "rezerviran termin kod nas za manje od 4 sata.\n\n"
                            f"📅 Termin: {k}\n\n"
                            "Radujemo se Vašem dolasku!\n\n"
                            "Srdačan pozdrav,\n"
                            "Škola brzog čitanja i mudrog učenja Varaždin"
                        )

                        if posalji_email_genericki(
                            info.get("email", ""),
                            naslov_podsjetnik,
                            tekst_podsjetnik
                        ):
                            podaci_baza["poslani_podsjetnici"].append(k)
                            promjena = True

            except Exception:
                continue

        if promjena:
            spremi_podatke(podaci_baza)

    except Exception as e:
        print(f"Greška u podsjetnicima: {e}")


# ============================================================
# POMOĆNE FUNKCIJE
# ============================================================

def email_izgleda_ispravno(email):
    obrazac = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.match(obrazac, email.strip()))


def obrisi_termin(podaci, termin):
    """
    Briše termin iz slobodnih i rezerviranih termina te metapodataka.
    """
    if termin in podaci.get("slobodni", []):
        podaci["slobodni"].remove(termin)

    podaci.get("rezervirani", {}).pop(termin, None)
    podaci.get("metapodaci", {}).pop(termin, None)

    if termin in podaci.get("poslani_podsjetnici", []):
        podaci["poslani_podsjetnici"].remove(termin)


def vrati_termin_u_slobodne(podaci, termin):
    if termin not in podaci["slobodni"]:
        podaci["slobodni"].append(termin)

    podaci["rezervirani"].pop(termin, None)


def sortirani_slobodni_termini(podaci):
    return sorted(
        [
            t
            for t in podaci["slobodni"]
            if t not in podaci["rezervirani"]
        ]
    )


# ============================================================
# INICIJALIZACIJA
# ============================================================

podaci = ucitaj_podatke()

if "podaci" not in st.session_state:
    st.session_state.podaci = podaci

podaci = st.session_state.podaci

# Osiguraj da postoje svi ključevi.
podaci.setdefault("slobodni", [])
podaci.setdefault("rezervirani", {})
podaci.setdefault("poslani_podsjetnici", [])
podaci.setdefault("metapodaci", {})

# Provjera podsjetnika.
provjeri_i_posalji_podsjetnike(podaci)


# ============================================================
# IZGLED STRANICE
# ============================================================

st.set_page_config(
    page_title="Rezervacija Termina",
    page_icon="📅",
    layout="centered"
)

if os.path.exists(IME_SLIKE):
    st.image(IME_SLIKE, use_container_width=True)
else:
    st.header("Škola brzog čitanja i mudrog učenja Varaždin")

st.title("📅 Online Rezervacija Termina")

tab1, tab2 = st.tabs([
    "👤 Rezerviraj Termin",
    "🔐 Admin Panel"
])


# ============================================================
# TAB 1 - REZERVACIJA
# ============================================================

with tab1:
    st.write(
        "Dobrodošli! Odaberite jedan od slobodnih termina "
        "i unesite svoje podatke."
    )

    if "uspjeh_poruka" in st.session_state:
        st.success(st.session_state.uspjeh_poruka)
        del st.session_state.uspjeh_poruka

    slobodni = sortirani_slobodni_termini(podaci)

    with st.form("forma_rezervacija", clear_on_submit=True):
        ime = st.text_input("Ime i Prezime:")
        email_kupca = st.text_input("Vaš E-mail:")

        if not slobodni:
            st.info(
                "Trenutno nema slobodnih termina. "
                "Molimo pokušajte kasnije."
            )
            gumb_rezerviraj = False
            termin = None

        else:
            termin = st.selectbox(
                "Odaberite slobodan termin:",
                slobodni
            )
            gumb_rezerviraj = st.form_submit_button(
                "Potvrdi Rezervaciju"
            )

        if gumb_rezerviraj:
            ime = ime.strip()
            email_kupca = email_kupca.strip()

            if not ime or not email_kupca:
                st.warning("Molimo ispunite sva polja!")

            elif not email_izgleda_ispravno(email_kupca):
                st.warning("Molimo unesite ispravnu e-mail adresu.")

            elif termin not in podaci["slobodni"]:
                st.error(
                    "Ovaj termin više nije dostupan. "
                    "Molimo osvježite stranicu."
                )

            elif termin in podaci["rezervirani"]:
                st.error(
                    "Ovaj termin je upravo rezerviran. "
                    "Molimo odaberite drugi termin."
                )

            else:
                # Privremeno rezerviraj termin.
                podaci["slobodni"].remove(termin)

                podaci["rezervirani"][termin] = {
                    "klijent": ime,
                    "email": email_kupca
                }

                with st.spinner(
                    "Slanje e-mail obavijesti..."
                ):
                    slanje_uspjelo = (
                        posalji_email_potvrde_direktno(
                            termin,
                            ime,
                            email_kupca
                        )
                    )

                if slanje_uspjelo:
                    spremi_podatke(podaci)

                    st.session_state.uspjeh_poruka = (
                        f"Uspješno ste rezervirali termin "
                        f"{termin}! Potvrda je poslana na Vaš e-mail."
                    )

                    st.rerun()

                else:
                    # Ako email nije poslan, vrati termin.
                    podaci["slobodni"].append(termin)
                    podaci["rezervirani"].pop(termin, None)

                    st.error(
                        "Rezervacija nije dovršena jer nije bilo moguće "
                        "poslati e-mail. Termin nije zauzet."
                    )

    st.markdown("---")
    st.subheader("🔗 Kontakt i društvene mreže")

    st.markdown(
        """
**Web stranica:** [kreo-vz.com](https://kreo-vz.com)

**Facebook:** [Škola brzog čitanja i mudrog učenja - Varaždin](https://facebook.com)

**Instagram:** [@skola_brzog_citanja_varazdin](https://instagram.com)
        """
    )


# ============================================================
# TAB 2 - ADMIN PANEL
# ============================================================

with tab2:
    st.header("Administracija")

    if not ADMIN_LOZINKA:
        st.warning(
            "Admin lozinka nije postavljena. "
            "Postavite ADMIN_LOZINKA u Streamlit Secrets."
        )

    upisana_lozinka = st.text_input(
        "Unesite admin lozinku:",
        type="password"
    )

    if ADMIN_LOZINKA and upisana_lozinka == ADMIN_LOZINKA:
        st.success("Pristup odobren!")

        # ----------------------------------------------------
        # GENERIRANJE TERMINA
        # ----------------------------------------------------

        st.subheader("🛠️ Alat za generiranje termina")

        if "admin_uspjeh" in st.session_state:
            st.success(st.session_state.admin_uspjeh)
            del st.session_state.admin_uspjeh

        col_d, col_v = st.columns(2)

        odabrani_datum = col_d.date_input(
            "1. Odaberite datum:",
            datetime.now().date()
        )

        sati_opcije = [
            f"{h:02d}:{m:02d}"
            for h in range(8, 21)
            for m in (0, 15, 30, 45)
        ]

        odabrano_vrijeme = col_v.selectbox(
            "2. Odaberite vrijeme početka:",
            sati_opcije
        )

        st.write("3. Odaberite trajanje lekcije:")

        opcije_trajanja = {
            "35 minuta - POMOĆ U ČITANJU": 35,
            "45 minuta - BESPLATNO TESTIRANJE ČITANJA": 45,
            "90 minuta - BRZO ČITANJE I MUDRO UČENJE": 90
        }

        odabrani_opis = st.radio(
            "Označite željeni program:",
            list(opcije_trajanja.keys())
        )

        minute_trajanja = opcije_trajanja[odabrani_opis]

        # Čisti naziv programa.
        if "POMOĆ" in odabrani_opis:
            cisti_opis_tekst = "POMOĆ U ČITANJU"
        elif "TESTIRANJE" in odabrani_opis:
            cisti_opis_tekst = "BESPLATNO TESTIRANJE ČITANJA"
        elif "MUDRO" in odabrani_opis:
            cisti_opis_tekst = "BRZO ČITANJE I MUDRO UČENJE"
        else:
            cisti_opis_tekst = "Nastava"

        st.info(
            f"Trenutno označeno: **{minute_trajanja} minuta - "
            f"{cisti_opis_tekst}**"
        )

        if st.button("➕ Kreiraj i dodaj termin u sustav"):
            pocetak_dt = datetime.combine(
                odabrani_datum,
                datetime.strptime(
                    odabrano_vrijeme,
                    "%H:%M"
                ).time()
            )

            kraj_dt = (
                pocetak_dt
                + timedelta(minutes=minute_trajanja)
            )

            novi_termin_puni = (
                f"{pocetak_dt.strftime('%d.%m.%Y.')} "
                f"{pocetak_dt.strftime('%H:%M')} "
                f"({minute_trajanja} min - {cisti_opis_tekst})"
            )

            preklapa_se = False

            # Provjeri preklapanje s postojećim terminima.
            for k, v in podaci.get("metapodaci", {}).items():
                try:
                    p_pocetak_text = v.get("pocetak")
                    p_kraj_text = v.get("kraj")

                    if not p_pocetak_text or not p_kraj_text:
                        continue

                    p_pocetak = datetime.strptime(
                        p_pocetak_text,
                        "%Y-%m-%d %H:%M"
                    )

                    p_kraj = datetime.strptime(
                        p_kraj_text,
                        "%Y-%m-%d %H:%M"
                    )

                    if (
                        max(pocetak_dt, p_pocetak)
                        < min(kraj_dt, p_kraj)
                    ):
                        preklapa_se = True
                        break

                except Exception:
                    continue

            if preklapa_se:
                st.error(
                    "⚠️ Greška! Odabrano vrijeme se preklapa "
                    "s već postojećim terminom u rasporedu!"
                )

            elif novi_termin_puni in podaci["slobodni"]:
                st.warning(
                    "⚠️ Ovaj termin već postoji u sustavu!"
                )

            elif novi_termin_puni in podaci["rezervirani"]:
                st.warning(
                    "⚠️ Ovaj termin je već rezerviran!"
                )

            else:
                podaci["slobodni"].append(novi_termin_puni)

                podaci["metapodaci"][novi_termin_puni] = {
                    "pocetak": pocetak_dt.strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    "kraj": kraj_dt.strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    "trajanje": minute_trajanja,
                    "opis": cisti_opis_tekst
                }

                spremi_podatke(podaci)

                st.session_state.admin_uspjeh = (
                    f"✅ Termin {novi_termin_puni} "
                    "uspješno je dodan!"
                )

                st.rerun()

        # ----------------------------------------------------
        # PREGLED SLOBODNIH TERMINA
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader("📋 Slobodni termini")

        slobodni_admin = sortirani_slobodni_termini(podaci)

        if slobodni_admin:
            for termin in slobodni_admin:
                col1, col2 = st.columns([5, 1])

                col1.write(f"📅 {termin}")

                if col2.button(
                    "🗑️",
                    key=f"obrisi_slobodni_{termin}"
                ):
                    obrisi_termin(podaci, termin)
                    spremi_podatke(podaci)
                    st.rerun()
        else:
            st.info("Nema slobodnih termina.")

        # ----------------------------------------------------
        # REZERVIRANI TERMINI
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader("👥 Rezervirani termini")

        rezervirani = podaci.get("rezervirani", {})

        if rezervirani:
            for termin in sorted(rezervirani.keys()):
                info = rezervirani[termin]

                with st.expander(
                    f"📅 {termin} — {info.get('klijent', '')}"
                ):
                    st.write(
                        f"**Klijent:** {info.get('klijent', '')}"
                    )
                    st.write(
                        f"**E-mail:** {info.get('email', '')}"
                    )

                    col_a, col_b = st.columns(2)

                    if col_a.button(
                        "↩️ Oslobodi termin",
                        key=f"oslobodi_{termin}"
                    ):
                        vrati_termin_u_slobodne(
                            podaci,
                            termin
                        )
                        spremi_podatke(podaci)
                        st.rerun()

                    if col_b.button(
                        "🗑️ Obriši termin",
                        key=f"obrisi_rezervirani_{termin}"
                    ):
                        obrisi_termin(podaci, termin)
                        spremi_podatke(podaci)
                        st.rerun()

        else:
            st.info("Nema rezerviranih termina.")

        # ----------------------------------------------------
        # EMAIL STATUS
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader("📧 Status e-maila")

        if email_postavke_ispravne():
            st.success(
                "SMTP postavke su pronađene. "
                f"Pošiljatelj: {MOJ_EMAIL}"
            )
        else:
            st.warning(
                "SMTP podaci nisu potpuno postavljeni. "
                "Rezervacije se neće moći potvrditi e-mailom."
            )

        # ----------------------------------------------------
        # PODACI
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader("💾 Podaci")

        st.write(
            f"Slobodnih termina: **{len(podaci['slobodni'])}**"
        )

        st.write(
            f"Rezerviranih termina: "
            f"**{len(podaci['rezervirani'])}**"
        )

        if st.button("🔄 Osvježi podatke"):
            st.session_state.podaci = ucitaj_podatke()
            st.rerun()
            
            if preklapa_se:
                st.error("⚠️ Greška! Odabrano vrijeme se preklapa s već postojećim terminom u rasporedu!")
            elif novi_termin_puni in podaci["slobodni"]:

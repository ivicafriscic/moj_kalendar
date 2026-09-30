import io
import os
import smtplib
import urllib.parse
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

import openpyxl
import streamlit as st
from supabase import create_client, Client


# ============================================================
# KONFIGURACIJA
# ============================================================

st.set_page_config(
    page_title="Online Rezervacija Termina",
    page_icon="📅",
    layout="centered",
)

# Svi osjetljivi podaci dolaze iz Streamlit Secrets.
# U lokalnom radu koristi .streamlit/secrets.toml.
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]

SMTP_SERVER = st.secrets.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(st.secrets.get("SMTP_PORT", 465))
MOJ_EMAIL = st.secrets["MOJ_EMAIL"]
MOJA_LOZINKA = st.secrets["MOJA_LOZINKA"]
EMAIL_PONUDACA = st.secrets["EMAIL_PONUDACA"]
ADMIN_LOZINKA = st.secrets["ADMIN_LOZINKA"]

APP_PUBLIC_URL = "https://mojkalendar-xff53d3yjcy6fwekctcmxg.streamlit.app/"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

PROGRAMI = {
    "35 minuta - POMOĆ U ČITANJU": {
        "trajanje": 35,
        "opis": "35 min - POMOĆ U ČITANJU",
    },
    "45 minuta - BESPLATNO TESTIRANJE ČITANJA": {
        "trajanje": 45,
        "opis": "45 min - BESPLATNO TESTIRANJE ČITANJA",
    },
    "90 minuta - BRZO ČITANJE I MUDRO UČENJE": {
        "trajanje": 90,
        "opis": "90 min - BRZO ČITANJE I MUDRO UČENJE",
    },
}


# ============================================================
# POMOĆNE FUNKCIJE
# ============================================================

def sada_utc():
    return datetime.now(timezone.utc)


def parse_termin_text(termin):
    """
    Prima termin u formatu:
    2026-10-05 17:00 (35 min - POMOĆ U ČITANJU)
    """
    return datetime.strptime(termin[:16], "%Y-%m-%d %H:%M")


def format_localni_termin(start_time, program):
    dt = start_time.astimezone()
    return f"{dt.strftime('%Y-%m-%d %H:%M')} ({program})"


def google_calendar_link(start_time, trajanje, ime_klijenta, opis):
    kraj = start_time + timedelta(minutes=trajanje)

    # Google Calendar prihvaća UTC vrijeme s oznakom Z.
    start_utc = start_time.astimezone(timezone.utc)
    kraj_utc = kraj.astimezone(timezone.utc)

    g_start = start_utc.strftime("%Y%m%dT%H%M%SZ")
    g_end = kraj_utc.strftime("%Y%m%dT%H%M%SZ")

    naslov = urllib.parse.quote(f"Nastava: {ime_klijenta}")
    detalji = urllib.parse.quote(
        f"Polaznik: {ime_klijenta}\n"
        f"Opis: {opis}"
    )

    return (
        "https://calendar.google.com/calendar/render"
        "?action=TEMPLATE"
        f"&text={naslov}"
        f"&dates={g_start}/{g_end}"
        f"&details={detalji}"
    )


def napravi_token_otkazivanja(appointment_id, email):
    """
    Sigurni token za otkazivanje bez prijave.
    Token je vezan uz ID termina i e-mail korisnika.
    """
    poruka = f"{appointment_id}|{email.strip().lower()}"
    return hmac.new(
        SUPABASE_SERVICE_KEY.encode("utf-8"),
        poruka.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def link_za_otkazivanje(appointment_id, email):
    token = napravi_token_otkazivanja(appointment_id, email)
    return (
        f"{APP_PUBLIC_URL}"
        f"?otkazi={urllib.parse.quote(str(appointment_id))}"
        f"&token={token}"
    )



def posalji_email_genericki(primatelj, naslov, tekst):
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.login(MOJ_EMAIL, MOJA_LOZINKA)

        msg = MIMEText(tekst, "plain", "utf-8")
        msg["Subject"] = naslov
        msg["From"] = MOJ_EMAIL
        msg["To"] = primatelj

        server.sendmail(
            MOJ_EMAIL,
            [primatelj],
            msg.as_string(),
        )
        server.quit()
        return True

    except Exception as e:
        print(f"Greška pri slanju e-maila: {e}")
        return False


def posalji_email_potvrde(rezervacija):
    start_time = datetime.fromisoformat(
        rezervacija["start_time"].replace("Z", "+00:00")
    )

    trajanje = rezervacija["duration_minutes"]
    ime = rezervacija["client_name"]
    email = rezervacija["client_email"]
    program = rezervacija["program"]

    link = google_calendar_link(
        start_time,
        trajanje,
        ime,
        program,
    )

    termin = format_localni_termin(start_time, program)
    link_otkazivanja = link_za_otkazivanje(rezervacija["id"], email)

    tekst_klijent = (
        f"Poštovani/a {ime},\n\n"
        "ovim putem potvrđujemo Vašu rezervaciju termina.\n\n"
        f"📅 Termin: {termin}\n"
        f"⏱️ Trajanje: {trajanje} minuta\n\n"
        "📅 Dodaj termin u Google kalendar:\n"
        f"{link}\n\n"
        "❌ Ako ne možete doći, možete otkazati termin ovdje:\n"
        f"{link_otkazivanja}\n\n"
        "Molimo Vas da budete spremni nekoliko minuta prije "
        "početka termina.\n\n"
        "Ako imate pitanja ili ne možete doći na termin, "
        "slobodno nam odgovorite na ovaj e-mail.\n\n"
        "Srdačan pozdrav,\n"
        "Škola brzog čitanja i mudrog učenja Varaždin"
    )

    tekst_ponudac = (
        "Pozdrav,\n\n"
        "imate novu rezervaciju!\n\n"
        f"📅 Termin: {termin}\n"
        f"⏱️ Trajanje: {trajanje} minuta\n"
        f"👤 Klijent: {ime}\n"
        f"📧 E-mail: {email}\n\n"
        f"Google Calendar:\n{link}\n\n"
        "Vaš Web Sustav"
    )

    ok_klijent = posalji_email_genericki(
        email,
        "Potvrda rezervacije termina - Škola brzog čitanja i mudrog učenja Varaždin",
        tekst_klijent,
    )

    ok_ponudac = posalji_email_genericki(
        EMAIL_PONUDACA,
        f"Nova rezervacija termina: {termin}",
        tekst_ponudac,
    )

    return ok_klijent and ok_ponudac


def posalji_email_otkazivanja(rezervacija):
    start_time = datetime.fromisoformat(
        rezervacija["start_time"].replace("Z", "+00:00")
    )

    trajanje = rezervacija["duration_minutes"]
    ime = rezervacija["client_name"]
    email = rezervacija["client_email"]
    program = rezervacija["program"]

    termin = format_localni_termin(start_time, program)

    tekst = (
        f"Poštovani/a {ime},\n\n"
        "obavještavamo Vas da je Vaša rezervacija termina otkazana.\n\n"
        f"📅 Termin: {termin}\n"
        f"⏱️ Trajanje: {trajanje} minuta\n\n"
        "Ako želite rezervirati novi termin, možete to učiniti putem naše stranice.\n\n"
        "Ako imate dodatnih pitanja, slobodno nam odgovorite na ovaj e-mail.\n\n"
        "Srdačan pozdrav,\n"
        "Škola brzog čitanja i mudrog učenja Varaždin"
    )

    return posalji_email_genericki(
        email,
        "Otkazivanje rezerviranog termina - Škola brzog čitanja i mudrog učenja Varaždin",
        tekst,
    )


def posalji_podsjetnik(rezervacija):
    start_time = datetime.fromisoformat(
        rezervacija["start_time"].replace("Z", "+00:00")
    )

    trajanje = rezervacija["duration_minutes"]
    ime = rezervacija["client_name"]
    email = rezervacija["client_email"]
    program = rezervacija["program"]

    termin = format_localni_termin(start_time, program)

    tekst = (
        f"Poštovani/a {ime},\n\n"
        "ovo je ljubazni podsjetnik na Vaš rezervirani termin.\n\n"
        f"📅 Termin: {termin}\n"
        f"⏱️ Trajanje: {trajanje} minuta\n\n"
        "Vaš termin počinje za približno 4 sata.\n\n"
        "Molimo Vas da budete spremni nekoliko minuta prije "
        "početka termina.\n\n"
        "Ako ne možete doći na termin, molimo Vas da nam se "
        "što prije javite odgovaranjem na ovaj e-mail.\n\n"
        "Srdačan pozdrav,\n"
        "Škola brzog čitanja i mudrog učenja Varaždin"
    )

    return posalji_email_genericki(
        email,
        "⏰ Podsjetnik na Vaš rezervirani termin",
        tekst,
    )


def ocisti_istekle_i_posalji_podsjetnike():
    """
    Radi pri svakom učitavanju aplikacije i periodički dok je
    otvorena. Za potpuno neovisno 24/7 slanje podsjetnika vidi
    napomenu u README-u / uputama.
    """
    try:
        supabase.rpc("cleanup_expired_appointments").execute()
    except Exception as e:
        print(f"Čišćenje isteka: {e}")

    try:
        due = (
            supabase
            .rpc("get_due_reminders")
            .execute()
        )

        rezervacije = due.data or []

        for rezervacija in rezervacije:
            if posalji_podsjetnik(rezervacija):
                try:
                    supabase.rpc(
                        "mark_reminder_sent",
                        {"p_appointment_id": rezervacija["id"]},
                    ).execute()
                except Exception as e:
                    print(f"Greška označavanja podsjetnika: {e}")

    except Exception as e:
        print(f"Provjera podsjetnika: {e}")


def dohvati_slobodne_termine():
    try:
        result = (
            supabase
            .table("appointments")
            .select("*")
            .eq("status", "available")
            .gt("start_time", sada_utc().isoformat())
            .order("start_time")
            .execute()
        )
        return result.data or []
    except Exception as e:
        st.error(f"Greška pri dohvaćanju termina: {e}")
        return []


def dohvati_rezervacije():
    try:
        result = (
            supabase
            .table("appointments")
            .select("*")
            .eq("status", "reserved")
            .order("start_time")
            .execute()
        )
        return result.data or []
    except Exception as e:
        st.error(f"Greška pri dohvaćanju rezervacija: {e}")
        return []


def obradi_otkazivanje_klijenta():
    """
    Omogućuje klijentu otkazivanje preko sigurnog linka iz e-maila.
    Nakon otkazivanja šalje potvrdu klijentu i obavijest administratoru.
    """
    otkazi = st.query_params.get("otkazi")
    token = st.query_params.get("token")

    if not otkazi or not token:
        return

    try:
        appointment_id = str(otkazi)

        result = (
            supabase
            .table("appointments")
            .select("*")
            .eq("id", appointment_id)
            .eq("status", "reserved")
            .limit(1)
            .execute()
        )

        if not result.data:
            st.error(
                "Ovaj termin više nije moguće otkazati. "
                "Možda je već otkazan ili više nije rezerviran."
            )
            st.query_params.clear()
            return

        rezervacija = result.data[0]
        email = rezervacija["client_email"]

        ocekivani_token = napravi_token_otkazivanja(
            appointment_id,
            email,
        )

        if not hmac.compare_digest(token, ocekivani_token):
            st.error("Neispravan link za otkazivanje.")
            st.query_params.clear()
            return

        supabase.table("appointments").update(
            {
                "status": "available",
                "client_name": None,
                "client_email": None,
                "reserved_at": None,
                "reminder_sent": False,
            }
        ).eq("id", appointment_id).execute()

        start_time = datetime.fromisoformat(
            rezervacija["start_time"].replace("Z", "+00:00")
        )
        termin = format_localni_termin(
            start_time,
            rezervacija["program"],
        )

        tekst_klijent = (
            f"Poštovani/a {rezervacija['client_name']},\n\n"
            "Vaša rezervacija termina je uspješno otkazana.\n\n"
            f"📅 Termin: {termin}\n"
            f"⏱️ Trajanje: {rezervacija['duration_minutes']} minuta\n\n"
            "Ako želite, možete rezervirati novi termin putem naše "
            "stranice.\n\n"
            "Srdačan pozdrav,\n"
            "Škola brzog čitanja i mudrog učenja Varaždin"
        )

        tekst_ponudac = (
            "Klijent je sam otkazao rezervaciju.\n\n"
            f"📅 Termin: {termin}\n"
            f"👤 Klijent: {rezervacija['client_name']}\n"
            f"📧 E-mail: {email}\n\n"
            "Termin je ponovno slobodan za rezervaciju."
        )

        posalji_email_genericki(
            email,
            "Potvrda otkazivanja termina - Škola brzog čitanja i mudrog učenja Varaždin",
            tekst_klijent,
        )

        posalji_email_genericki(
            EMAIL_PONUDACA,
            f"Klijent je otkazao rezervaciju: {termin}",
            tekst_ponudac,
        )

        st.success(
            "Vaša rezervacija je uspješno otkazana. "
            "Na Vaš e-mail poslali smo potvrdu otkazivanja."
        )
        st.info("Termin je sada ponovno slobodan za rezervaciju.")

        st.query_params.clear()

    except Exception as e:
        st.error(f"Otkazivanje nije uspjelo: {e}")
        st.query_params.clear()



# ============================================================
# AUTOMATSKA PROVJERA
# ============================================================

obradi_otkazivanje_klijenta()
ocisti_istekle_i_posalji_podsjetnike()


@st.fragment(run_every="60s")
def automatska_provjera():
    ocisti_istekle_i_posalji_podsjetnike()
    st.caption("Sustav automatski provjerava podsjetnike i istekle termine.")


automatska_provjera()


# ============================================================
# LOGO / NASLOV
# ============================================================

IME_SLIKE = "logo.png"

if os.path.exists(IME_SLIKE):
    st.image(IME_SLIKE, use_container_width=True)
else:
    st.header("Škola brzog čitanja i mudrog učenja Varaždin")

st.title("📅 Online Rezervacija Termina")
st.markdown(
    "Ovdje možete brzo i izravno rezervirati termin "
    "za nastavu."
)


# ============================================================
# TABOVI
# ============================================================

tab1, tab2 = st.tabs(
    ["👤 Rezerviraj Termin", "🔐 Admin Panel"]
)


# ============================================================
# JAVNA REZERVACIJA
# ============================================================

with tab1:
    st.write(
        "Dobrodošli! Odaberite jedan od slobodnih termina "
        "i unesite svoje podatke."
    )

    if "uspjeh_poruka" in st.session_state:
        st.success(st.session_state.uspjeh_poruka)
        del st.session_state.uspjeh_poruka

    slobodni = dohvati_slobodne_termine()

    if not slobodni:
        st.info(
            "Trenutno nema slobodnih termina. "
            "Molimo pokušajte kasnije."
        )
    else:
        opcije = {}

        for termin in slobodni:
            start = datetime.fromisoformat(
                termin["start_time"].replace("Z", "+00:00")
            )
            prikaz = format_localni_termin(
                start,
                termin["program"],
            )
            opcije[prikaz] = termin

        with st.form(
            "forma_rezervacija",
            clear_on_submit=True,
        ):
            ime = st.text_input("Ime i Prezime:")
            email_kupca = st.text_input("Vaš E-mail:")

            odabrani_prikaz = st.selectbox(
                "Odaberite slobodan termin:",
                list(opcije.keys()),
            )

            gumb_rezerviraj = st.form_submit_button(
                "Potvrdi Rezervaciju"
            )

            if gumb_rezerviraj:
                if not ime.strip() or not email_kupca.strip():
                    st.warning("Molimo ispunite sva polja!")
                elif "@" not in email_kupca:
                    st.warning(
                        "Molimo unesite ispravnu e-mail adresu."
                    )
                else:
                    odabrani = opcije[odabrani_prikaz]

                    try:
                        result = supabase.rpc(
                            "reserve_appointment",
                            {
                                "p_appointment_id": odabrani["id"],
                                "p_client_name": ime.strip(),
                                "p_client_email": email_kupca.strip(),
                            },
                        ).execute()

                        if not result.data:
                            st.error(
                                "Ovaj termin je upravo rezervirao "
                                "netko drugi. Molimo odaberite "
                                "drugi termin."
                            )
                            st.rerun()

                        rezervacija = result.data[0]

                        with st.spinner(
                            "Šaljem potvrdu rezervacije..."
                        ):
                            email_ok = posalji_email_potvrde(
                                rezervacija
                            )

                        if email_ok:
                            st.session_state.uspjeh_poruka = (
                                f"Uspješno ste rezervirali termin "
                                f"{odabrani_prikaz}. "
                                "Potvrda je poslana na Vaš e-mail."
                            )
                        else:
                            st.session_state.uspjeh_poruka = (
                                f"Rezervacija termina "
                                f"{odabrani_prikaz} je spremljena, "
                                "ali slanje jednog ili oba e-maila "
                                "nije uspjelo. Molimo provjerite "
                                "e-mail postavke."
                            )

                        st.rerun()

                    except Exception as e:
                        st.error(
                            "Rezervacija nije uspjela. "
                            f"Detalj: {e}"
                        )

    st.markdown("---")
    st.subheader("🔗 Kontakt i društvene mreže")

    st.markdown(
        """
**Web stranica:** [www.kreo-vz.com](https://kreo-vz.com)

**Facebook:** [Škola brzog čitanja i mudrog učenja - Varaždin](https://www.facebook.com/SBCiMUVarazdin/?locale=hr_HR)

**Instagram:** [@brzocitanjeimudroucenjevz](https://www.instagram.com/brzocitanjeimudroucenjevz/)
"""
    )


# ============================================================
# ADMIN PANEL
# ============================================================

with tab2:
    st.header("Administracija")

    upisana_lozinka = st.text_input(
        "Unesite admin lozinku:",
        type="password",
    )

    if upisana_lozinka == ADMIN_LOZINKA:
        st.success("Pristup odobren!")

        # ----------------------------------------------------
        # ČIŠĆENJE
        # ----------------------------------------------------

        if st.button(
            "🧹 Očisti istekle termine odmah",
            use_container_width=True,
        ):
            try:
                supabase.rpc(
                    "cleanup_expired_appointments"
                ).execute()

                st.success(
                    "Istekli termini su uklonjeni iz aktivnih rezervacija."
                )
                st.rerun()

            except Exception as e:
                st.error(f"Greška: {e}")

        # ----------------------------------------------------
        # GENERIRANJE TERMINA
        # ----------------------------------------------------

        st.subheader("🛠️ Alat za generiranje termina")

        col_d, col_v = st.columns(2)

        odabrani_datum = col_d.date_input(
            "1. Odaberite datum:",
            datetime.now().date(),
        )

        sati_opcije = [
            f"{h:02d}:{m:02d}"
            for h in range(8, 21)
            for m in (0, 15, 30, 45)
        ]

        odabrano_vrijeme = col_v.selectbox(
            "2. Odaberite vrijeme početka:",
            sati_opcije,
        )

        st.write("3. Označite program lekcije:")

        odabrani_opis = st.radio(
            "Programi:",
            list(PROGRAMI.keys()),
        )

        program_podaci = PROGRAMI[odabrani_opis]

        if st.button(
            "➕ Kreiraj i dodaj termin u sustav",
            use_container_width=True,
        ):
            try:
                # Termin se sprema kao lokalno vrijeme Europe/Zagreb.
                # PostgreSQL ga pretvara u timestamptz.
                lokalni_string = (
                    f"{odabrani_datum} {odabrano_vrijeme}"
                )

                novi_termin = datetime.strptime(
                    lokalni_string,
                    "%Y-%m-%d %H:%M",
                )

                result = supabase.table(
                    "appointments"
                ).insert(
                    {
                        "start_time": novi_termin.isoformat(),
                        "duration_minutes": program_podaci["trajanje"],
                        "program": program_podaci["opis"],
                        "status": "available",
                    }
                ).execute()

                st.success(
                    "Uspješno generiran termin: "
                    f"{lokalni_string} "
                    f"({program_podaci['opis']})"
                )
                st.rerun()

            except Exception as e:
                st.error(
                    "Termin nije moguće dodati. "
                    "Možda već postoji isti termin."
                )
                st.caption(str(e))

        # ----------------------------------------------------
        # SLOBODNI TERMINI
        # ----------------------------------------------------

        st.subheader("📋 Trenutno objavljeni slobodni termini")

        slobodni_admin = dohvati_slobodne_termine()

        if not slobodni_admin:
            st.info(
                "Nema otvorenih slobodnih termina u sustavu."
            )
        else:
            for termin in slobodni_admin:
                start = datetime.fromisoformat(
                    termin["start_time"].replace("Z", "+00:00")
                )

                prikaz = format_localni_termin(
                    start,
                    termin["program"],
                )

                c1, c2 = st.columns([4, 1])

                c1.write(f"🟢 {prikaz}")

                if c2.button(
                    "Ukloni",
                    key=f"remove_{termin['id']}",
                ):
                    supabase.table(
                        "appointments"
                    ).update(
                        {"status": "cancelled"}
                    ).eq(
                        "id",
                        termin["id"],
                    ).execute()

                    st.rerun()

        # ----------------------------------------------------
        # REZERVACIJE
        # ----------------------------------------------------

        st.subheader(
            "📋 Pregled zauzetih rezervacija"
        )

        rezervacije = dohvati_rezervacije()

        if not rezervacije:
            st.info("Nema rezerviranih termina.")
        else:
            for rezervacija in rezervacije:
                start = datetime.fromisoformat(
                    rezervacija["start_time"].replace("Z", "+00:00")
                )

                trajanje = rezervacija["duration_minutes"]

                prikaz = format_localni_termin(
                    start,
                    rezervacija["program"],
                )

                st.markdown(
                    f"📅 **{prikaz}**  \n"
                    f"👤 {rezervacija['client_name']}  \n"
                    f"📧 {rezervacija['client_email']}"
                )

                link = google_calendar_link(
                    start,
                    trajanje,
                    rezervacija["client_name"],
                    rezervacija["program"],
                )

                c1, c2 = st.columns(2)

                c1.markdown(
                    f"[📅 Dodaj u Google kalendar]({link})"
                )

                if c2.button(
                    "Otkaži rezervaciju",
                    key=f"cancel_{rezervacija['id']}",
                ):
                    supabase.table(
                        "appointments"
                    ).update(
                        {
                            "status": "available",
                            "client_name": None,
                            "client_email": None,
                            "reserved_at": None,
                            "reminder_sent": False,
                        }
                    ).eq(
                        "id",
                        rezervacija["id"],
                    ).execute()

                    email_otkazivanja_ok = posalji_email_otkazivanja(
                        rezervacija
                    )

                    if email_otkazivanja_ok:
                        st.success(
                            "Rezervacija je otkazana, termin je ponovno slobodan "
                            "i klijentu je poslana obavijest e-mailom."
                        )
                    else:
                        st.warning(
                            "Rezervacija je otkazana i termin je ponovno slobodan, "
                            "ali obavijest e-mailom nije poslana."
                        )

                    st.rerun()

                st.markdown("---")

            # ------------------------------------------------
            # EXCEL
            # ------------------------------------------------

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Rezervacije"

            ws.append(
                [
                    "Datum i Vrijeme",
                    "Trajanje",
                    "Program",
                    "Ime i Prezime",
                    "E-mail klijenta",
                    "Podsjetnik poslan",
                ]
            )

            for rezervacija in rezervacije:
                start = datetime.fromisoformat(
                    rezervacija["start_time"].replace("Z", "+00:00")
                )

                ws.append(
                    [
                        start.astimezone().strftime(
                            "%d.%m.%Y %H:%M"
                        ),
                        rezervacija["duration_minutes"],
                        rezervacija["program"],
                        rezervacija["client_name"],
                        rezervacija["client_email"],
                        "DA"
                        if rezervacija["reminder_sent"]
                        else "NE",
                    ]
                )

            excel_data = io.BytesIO()
            wb.save(excel_data)
            excel_data.seek(0)

            st.download_button(
                label="📥 Preuzmi Excel tablicu rezervacija",
                data=excel_data,
                file_name=(
                    f"rezervacije_"
                    f"{datetime.now().strftime('%d.%m.%Y')}.xlsx"
                ),
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
            )

        # ----------------------------------------------------
        # OPREZNO ČIŠĆENJE SVIH TERMINA
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader("🚨 Potpuno čišćenje")

        potvrda_ciscenja = st.checkbox(
            "Želim obrisati sve termine i rezervacije."
        )

        if potvrda_ciscenja:
            if st.button(
                "🚨 OČISTI CIJELI SUSTAV",
                type="secondary",
            ):
                try:
                    supabase.rpc(
                        "clear_all_appointments"
                    ).execute()

                    st.success(
                        "Svi termini i rezervacije su očišćeni."
                    )
                    st.rerun()

                except Exception as e:
                    st.error(f"Greška: {e}")

    elif upisana_lozinka:
        st.error("Pogrešna lozinka!")

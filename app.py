import io
import os
import smtplib
import urllib.parse
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

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]

SMTP_SERVER = st.secrets.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(st.secrets.get("SMTP_PORT", 465))
MOJ_EMAIL = st.secrets["MOJ_EMAIL"]
MOJA_LOZINKA = st.secrets["MOJA_LOZINKA"]
EMAIL_PONUDACA = st.secrets["EMAIL_PONUDACA"]
ADMIN_LOZINKA = st.secrets["ADMIN_LOZINKA"]

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

GRUPNI_PROGRAM = "GRUPNO TESTIRANJE ČITANJA"
GRUPNO_TRAJANJE = 45


# ============================================================
# POMOĆNE FUNKCIJE
# ============================================================

def sada_utc():
    return datetime.now(timezone.utc)


def format_localni_termin(start_time, program):
    dt = start_time.astimezone()
    return f"{dt.strftime('%d.%m.%Y. %H:%M')} ({program})"


def google_calendar_link(start_time, trajanje, ime_klijenta, opis):
    kraj = start_time + timedelta(minutes=trajanje)
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

    link = google_calendar_link(start_time, trajanje, ime, program)
    termin = format_localni_termin(start_time, program)

    tekst_klijent = (
        f"Poštovani/a {ime},\n\n"
        "ovim putem potvrđujemo Vašu rezervaciju termina.\n\n"
        f"📅 Termin: {termin}\n"
        f"⏱️ Trajanje: {trajanje} minuta\n\n"
        "📅 Dodaj termin u Google kalendar:\n"
        f"{link}\n\n"
        "Molimo Vas da budete spremni nekoliko minuta prije početka termina.\n\n"
        "Ako imate pitanja ili ne možete doći na termin, slobodno nam odgovorite na ovaj e-mail.\n\n"
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


def posalji_email_potvrde_grupno(rezervacija, termin_podaci):
    start_time = datetime.fromisoformat(
        termin_podaci["start_time"].replace("Z", "+00:00")
    )
    ime = rezervacija["client_name"]
    email = rezervacija["client_email"]
    kapacitet = termin_podaci["capacity"]
    zauzeto = termin_podaci["reserved_count"]

    link = google_calendar_link(
        start_time,
        termin_podaci["duration_minutes"],
        ime,
        GRUPNI_PROGRAM,
    )
    termin = format_localni_termin(start_time, GRUPNI_PROGRAM)

    tekst_klijent = (
        f"Poštovani/a {ime},\n\n"
        "potvrđujemo Vašu rezervaciju za grupno testiranje čitanja.\n\n"
        f"📅 Termin: {termin}\n"
        f"⏱️ Trajanje: {termin_podaci['duration_minutes']} minuta\n"
        f"👥 Kapacitet grupe: {kapacitet} osoba\n"
        f"🪑 Trenutno zauzeto: {zauzeto}/{kapacitet}\n\n"
        "📅 Dodaj termin u Google kalendar:\n"
        f"{link}\n\n"
        "Ako ne možete doći na termin, molimo Vas da nam se javite što prije.\n\n"
        "Srdačan pozdrav,\n"
        "Škola brzog čitanja i mudrog učenja Varaždin"
    )

    tekst_ponudac = (
        "Pozdrav,\n\n"
        "nova prijava na GRUPNO TESTIRANJE!\n\n"
        f"📅 Termin: {termin}\n"
        f"👤 Polaznik: {ime}\n"
        f"📧 E-mail: {email}\n"
        f"👥 Popunjenost: {zauzeto}/{kapacitet}\n\n"
        f"Google Calendar:\n{link}\n\n"
        "Vaš Web Sustav"
    )

    ok_klijent = posalji_email_genericki(
        email,
        "Potvrda prijave - grupno testiranje čitanja",
        tekst_klijent,
    )
    ok_ponudac = posalji_email_genericki(
        EMAIL_PONUDACA,
        f"Nova prijava na grupno testiranje: {termin}",
        tekst_ponudac,
    )
    return ok_klijent and ok_ponudac


def posalji_podsjetnik(rezervacija, grupno=False, termin_podaci=None):
    if grupno:
        start_time = datetime.fromisoformat(
            termin_podaci["start_time"].replace("Z", "+00:00")
        )
        trajanje = termin_podaci["duration_minutes"]
        program = GRUPNI_PROGRAM
        tekst = (
            f"Poštovani/a {rezervacija['client_name']},\n\n"
            "ovo je ljubazni podsjetnik na Vašu prijavu za grupno testiranje.\n\n"
            f"📅 Termin: {format_localni_termin(start_time, program)}\n"
            f"⏱️ Trajanje: {trajanje} minuta\n\n"
            "Vaš termin počinje za približno 4 sata.\n\n"
            "Srdačan pozdrav,\n"
            "Škola brzog čitanja i mudrog učenja Varaždin"
        )
        return posalji_email_genericki(
            rezervacija["client_email"],
            "⏰ Podsjetnik - grupno testiranje čitanja",
            tekst,
        )

    start_time = datetime.fromisoformat(
        rezervacija["start_time"].replace("Z", "+00:00")
    )
    trajanje = rezervacija["duration_minutes"]
    ime = rezervacija["client_name"]
    email = rezervacija["client_email"]
    program = rezervacija["program"]

    tekst = (
        f"Poštovani/a {ime},\n\n"
        "ovo je ljubazni podsjetnik na Vaš rezervirani termin.\n\n"
        f"📅 Termin: {format_localni_termin(start_time, program)}\n"
        f"⏱️ Trajanje: {trajanje} minuta\n\n"
        "Vaš termin počinje za približno 4 sata.\n\n"
        "Molimo Vas da budete spremni nekoliko minuta prije početka termina.\n\n"
        "Srdačan pozdrav,\n"
        "Škola brzog čitanja i mudrog učenja Varaždin"
    )
    return posalji_email_genericki(
        email,
        "⏰ Podsjetnik na Vaš rezervirani termin",
        tekst,
    )


def ocisti_istekle_i_posalji_podsjetnike():
    try:
        supabase.rpc("cleanup_expired_appointments").execute()
    except Exception as e:
        print(f"Čišćenje isteka: {e}")

    try:
        due = supabase.rpc("get_due_reminders").execute()
        for item in due.data or []:
            if item.get("reservation_type") == "group":
                reservation = {
                    "id": item["reservation_id"],
                    "client_name": item["client_name"],
                    "client_email": item["client_email"],
                }
                if posalji_podsjetnik(True, reservation, item):
                    supabase.rpc(
                        "mark_group_reminder_sent",
                        {"p_reservation_id": item["reservation_id"]},
                    ).execute()
            else:
                reservation = {
                    "id": item["reservation_id"],
                    "client_name": item["client_name"],
                    "client_email": item["client_email"],
                    "start_time": item["start_time"],
                    "duration_minutes": item["duration_minutes"],
                    "program": item["program"],
                }
                if posalji_podsjetnik(reservation):
                    supabase.rpc(
                        "mark_reminder_sent",
                        {"p_appointment_id": item["appointment_id"]},
                    ).execute()
    except Exception as e:
        print(f"Provjera podsjetnika: {e}")


def dohvati_slobodne_termine():
    try:
        result = supabase.rpc("get_public_appointments").execute()
        return result.data or []
    except Exception as e:
        st.error(f"Greška pri dohvaćanju termina: {e}")
        return []


def dohvati_rezervacije():
    try:
        result = (
            supabase.table("appointments")
            .select("*")
            .in_("status", ["reserved", "available"])
            .order("start_time")
            .execute()
        )
        return result.data or []
    except Exception as e:
        st.error(f"Greška pri dohvaćanju termina: {e}")
        return []


def dohvati_grupne_prijave():
    try:
        result = (
            supabase.table("group_reservations")
            .select("*, appointments(start_time,duration_minutes,program,capacity)")
            .eq("status", "reserved")
            .order("reserved_at")
            .execute()
        )
        return result.data or []
    except Exception as e:
        st.error(f"Greška pri dohvaćanju grupnih prijava: {e}")
        return []


ocisti_istekle_i_posalji_podsjetnike()


@st.fragment(run_every="60s")
def automatska_provjera():
    ocisti_istekle_i_posalji_podsjetnike()
    st.caption("Sustav automatski provjerava podsjetnike i istekle termine.")


automatska_provjera()


# ============================================================
# NASLOV
# ============================================================

IME_SLIKE = "logo.png"

if os.path.exists(IME_SLIKE):
    st.image(IME_SLIKE, use_container_width=True)
else:
    st.header("Škola brzog čitanja i mudrog učenja Varaždin")

st.title("📅 Online Rezervacija Termina")
st.markdown("Ovdje možete brzo i izravno rezervirati termin za nastavu.")


tab1, tab2 = st.tabs(["👤 Rezerviraj Termin", "🔐 Admin Panel"])


# ============================================================
# JAVNA REZERVACIJA
# ============================================================

with tab1:
    st.write("Dobrodošli! Odaberite slobodan termin i unesite svoje podatke.")

    if "uspjeh_poruka" in st.session_state:
        st.success(st.session_state.uspjeh_poruka)
        del st.session_state.uspjeh_poruka

    slobodni = dohvati_slobodne_termine()

    if not slobodni:
        st.info("Trenutno nema slobodnih termina. Molimo pokušajte kasnije.")
    else:
        opcije = {}
        for termin in slobodni:
            start = datetime.fromisoformat(
                termin["start_time"].replace("Z", "+00:00")
            )
            if termin["is_group"]:
                prikaz = (
                    f"{format_localni_termin(start, GRUPNI_PROGRAM)} - "
                    f"🪑 {termin['remaining_places']}/{termin['capacity']} mjesta"
                )
            else:
                prikaz = format_localni_termin(start, termin["program"])
            opcije[prikaz] = termin

        with st.form("forma_rezervacija", clear_on_submit=True):
            ime = st.text_input("Ime i Prezime:")
            email_kupca = st.text_input("Vaš E-mail:")
            odabrani_prikaz = st.selectbox(
                "Odaberite slobodan termin:",
                list(opcije.keys()),
            )
            gumb_rezerviraj = st.form_submit_button("Potvrdi Rezervaciju")

            if gumb_rezerviraj:
                if not ime.strip() or not email_kupca.strip():
                    st.warning("Molimo ispunite sva polja!")
                elif "@" not in email_kupca or "." not in email_kupca.split("@")[-1]:
                    st.warning("Molimo unesite ispravnu e-mail adresu.")
                else:
                    odabrani = opcije[odabrani_prikaz]

                    try:
                        if odabrani["is_group"]:
                            result = supabase.rpc(
                                "reserve_group_appointment",
                                {
                                    "p_appointment_id": odabrani["id"],
                                    "p_client_name": ime.strip(),
                                    "p_client_email": email_kupca.strip(),
                                },
                            ).execute()

                            if not result.data:
                                st.error(
                                    "Grupa je u međuvremenu popunjena. "
                                    "Molimo odaberite drugi termin."
                                )
                                st.rerun()

                            rezervacija = result.data[0]
                            termin_podaci = {
                                "start_time": odabrani["start_time"],
                                "duration_minutes": odabrani["duration_minutes"],
                                "capacity": odabrani["capacity"],
                                "reserved_count": odabrani["reserved_count"] + 1,
                            }

                            with st.spinner("Šaljem potvrdu prijave..."):
                                email_ok = posalji_email_potvrde_grupno(
                                    rezervacija, termin_podaci
                                )
                        else:
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
                                    "Ovaj termin je upravo rezervirao netko drugi. "
                                    "Molimo odaberite drugi termin."
                                )
                                st.rerun()

                            rezervacija = result.data[0]
                            with st.spinner("Šaljem potvrdu rezervacije..."):
                                email_ok = posalji_email_potvrde(rezervacija)

                        if email_ok:
                            st.session_state.uspjeh_poruka = (
                                f"Uspješno ste rezervirali termin {odabrani_prikaz}. "
                                "Potvrda je poslana na Vaš e-mail."
                            )
                        else:
                            st.session_state.uspjeh_poruka = (
                                f"Rezervacija {odabrani_prikaz} je spremljena, "
                                "ali slanje e-maila nije uspjelo."
                            )
                        st.rerun()

                    except Exception as e:
                        st.error(f"Rezervacija nije uspjela. Detalj: {e}")

    st.markdown("---")
    st.subheader("🔗 Kontakt i društvene mreže")
    st.markdown(
        """
**Web stranica:** [www.kreo-vz.com](https://kreo-vz.com)

**Facebook:** Škola brzog čitanja i mudrog učenja - Varaždin

**Instagram:** @skola_brzog_citanja_varazdin
"""
    )


# ============================================================
# ADMIN PANEL
# ============================================================

with tab2:
    st.header("Administracija")
    upisana_lozinka = st.text_input("Unesite admin lozinku:", type="password")

    if upisana_lozinka == ADMIN_LOZINKA:
        st.success("Pristup odobren!")

        if st.button("🧹 Očisti istekle termine odmah", use_container_width=True):
            try:
                supabase.rpc("cleanup_expired_appointments").execute()
                st.success("Istekli termini su obrađeni.")
                st.rerun()
            except Exception as e:
                st.error(f"Greška: {e}")

        # ----------------------------------------------------
        # OBIČNI TERMINI
        # ----------------------------------------------------

        st.subheader("🛠️ Alat za generiranje običnih termina")

        col_d, col_v = st.columns(2)
        odabrani_datum = col_d.date_input(
            "1. Odaberite datum:", datetime.now().date(), key="obicni_datum"
        )
        sati_opcije = [
            f"{h:02d}:{m:02d}"
            for h in range(8, 21)
            for m in (0, 15, 30, 45)
        ]
        odabrano_vrijeme = col_v.selectbox(
            "2. Odaberite vrijeme početka:",
            sati_opcije,
            key="obicno_vrijeme",
        )
        odabrani_opis = st.radio(
            "3. Programi:",
            list(PROGRAMI.keys()),
            key="obicni_program",
        )
        program_podaci = PROGRAMI[odabrani_opis]

        if st.button("➕ Kreiraj obični termin", use_container_width=True):
            try:
                lokalni_string = f"{odabrani_datum} {odabrano_vrijeme}"
                novi_termin = datetime.strptime(lokalni_string, "%Y-%m-%d %H:%M")
                supabase.table("appointments").insert(
                    {
                        "start_time": novi_termin.isoformat(),
                        "duration_minutes": program_podaci["trajanje"],
                        "program": program_podaci["opis"],
                        "capacity": 1,
                        "status": "available",
                    }
                ).execute()
                st.success(f"Uspješno dodan termin: {lokalni_string}")
                st.rerun()
            except Exception as e:
                st.error("Termin nije moguće dodati. Možda već postoji isti početak termina.")
                st.caption(str(e))

        # ----------------------------------------------------
        # GRUPNO TESTIRANJE
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader("👥 Grupno testiranje")
        st.info(
            "Ovdje se kreira JEDAN grupni termin. "
            "Kapacitet je od 1 do najviše 10 osoba."
        )

        g1, g2 = st.columns(2)
        grupni_datum = g1.date_input(
            "Datum grupnog testiranja:",
            datetime.now().date(),
            key="grupni_datum",
        )
        grupno_vrijeme = g2.selectbox(
            "Vrijeme grupnog testiranja:",
            sati_opcije,
            key="grupno_vrijeme",
        )
        grupni_kapacitet = st.number_input(
            "Kapacitet grupe:",
            min_value=1,
            max_value=10,
            value=10,
            step=1,
            key="grupni_kapacitet",
        )

        st.caption(
            f"Program: {GRUPNI_PROGRAM} • Trajanje: {GRUPNO_TRAJANJE} minuta • "
            f"Kapacitet: {grupni_kapacitet} osoba"
        )

        if st.button("👥 Kreiraj grupni termin", use_container_width=True):
            try:
                lokalni_string = f"{grupni_datum} {grupno_vrijeme}"
                novi_termin = datetime.strptime(lokalni_string, "%Y-%m-%d %H:%M")

                supabase.table("appointments").insert(
                    {
                        "start_time": novi_termin.isoformat(),
                        "duration_minutes": GRUPNO_TRAJANJE,
                        "program": GRUPNI_PROGRAM,
                        "capacity": int(grupni_kapacitet),
                        "status": "available",
                    }
                ).execute()

                st.success(
                    f"Grupni termin je kreiran: {lokalni_string} — "
                    f"{grupni_kapacitet} mjesta."
                )
                st.rerun()
            except Exception as e:
                st.error("Grupni termin nije moguće dodati.")
                st.caption(str(e))

        # ----------------------------------------------------
        # SVI TERMINI
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader("📋 Objavljeni termini")

        try:
            svi = supabase.rpc("get_public_appointments").execute().data or []
        except Exception:
            svi = []

        if not svi:
            st.info("Nema aktivnih termina.")
        else:
            for termin in svi:
                start = datetime.fromisoformat(
                    termin["start_time"].replace("Z", "+00:00")
                )

                if termin["is_group"]:
                    oznaka = (
                        f"👥 {format_localni_termin(start, GRUPNI_PROGRAM)} — "
                        f"{termin['reserved_count']}/{termin['capacity']} zauzeto"
                    )
                else:
                    oznaka = f"🟢 {format_localni_termin(start, termin['program'])}"

                c1, c2 = st.columns([5, 1])
                c1.write(oznaka)

                if c2.button("Ukloni", key=f"remove_{termin['id']}"):
                    supabase.table("appointments").update(
                        {"status": "cancelled"}
                    ).eq("id", termin["id"]).execute()
                    st.rerun()

        # ----------------------------------------------------
        # OBIČNE REZERVACIJE
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader("📋 Obične rezervacije")

        obicne_rezervacije = [
            x for x in dohvati_rezervacije()
            if x.get("status") == "reserved" and x.get("capacity", 1) == 1
        ]

        if not obicne_rezervacije:
            st.info("Nema običnih rezervacija.")
        else:
            for rezervacija in obicne_rezervacije:
                start = datetime.fromisoformat(
                    rezervacija["start_time"].replace("Z", "+00:00")
                )
                prikaz = format_localni_termin(start, rezervacija["program"])

                st.markdown(
                    f"📅 **{prikaz}**  \n"
                    f"👤 {rezervacija['client_name']}  \n"
                    f"📧 {rezervacija['client_email']}"
                )

                link = google_calendar_link(
                    start,
                    rezervacija["duration_minutes"],
                    rezervacija["client_name"],
                    rezervacija["program"],
                )
                c1, c2 = st.columns(2)
                c1.markdown(f"[📅 Dodaj u Google kalendar]({link})")

                if c2.button(
                    "Otkaži rezervaciju",
                    key=f"cancel_normal_{rezervacija['id']}",
                ):
                    supabase.table("appointments").update(
                        {
                            "status": "available",
                            "client_name": None,
                            "client_email": None,
                            "reserved_at": None,
                            "reminder_sent": False,
                        }
                    ).eq("id", rezervacija["id"]).execute()
                    st.success("Rezervacija je otkazana.")
                    st.rerun()

                st.markdown("---")

        # ----------------------------------------------------
        # GRUPNE PRIJAVE
        # ----------------------------------------------------

        st.subheader("👥 Prijave na grupna testiranja")

        grupne = dohvati_grupne_prijave()
        if not grupne:
            st.info("Nema prijavljenih polaznika na grupna testiranja.")
        else:
            for prijava in grupne:
                termin = prijava.get("appointments") or {}
                start_text = termin.get("start_time")

                if start_text:
                    start = datetime.fromisoformat(
                        start_text.replace("Z", "+00:00")
                    )
                    prikaz = format_localni_termin(
                        start, GRUPNI_PROGRAM
                    )
                else:
                    prikaz = "Nepoznat termin"

                st.markdown(
                    f"📅 **{prikaz}**  \n"
                    f"👤 {prijava['client_name']}  \n"
                    f"📧 {prijava['client_email']}"
                )

                if st.button(
                    "Otkaži ovu prijavu",
                    key=f"cancel_group_{prijava['id']}",
                ):
                    try:
                        supabase.rpc(
                            "cancel_group_reservation",
                            {"p_reservation_id": prijava["id"]},
                        ).execute()
                        st.success("Grupna prijava je otkazana.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Greška pri otkazivanju: {e}")

                st.markdown("---")

        # ----------------------------------------------------
        # EXCEL
        # ----------------------------------------------------

        st.subheader("📥 Excel izvještaj")

        sve_grupne = []
        try:
            sve_grupne = dohvati_grupne_prijave()
        except Exception:
            pass

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Rezervacije"
        ws.append(
            [
                "Tip",
                "Datum i Vrijeme",
                "Trajanje",
                "Program",
                "Ime i Prezime",
                "E-mail klijenta",
                "Podsjetnik poslan",
            ]
        )

        for r in obicne_rezervacije:
            start = datetime.fromisoformat(
                r["start_time"].replace("Z", "+00:00")
            )
            ws.append(
                [
                    "Obični termin",
                    start.astimezone().strftime("%d.%m.%Y %H:%M"),
                    r["duration_minutes"],
                    r["program"],
                    r["client_name"],
                    r["client_email"],
                    "DA" if r["reminder_sent"] else "NE",
                ]
            )

        for r in sve_grupne:
            ap = r.get("appointments") or {}
            start_text = ap.get("start_time")
            if not start_text:
                continue
            start = datetime.fromisoformat(start_text.replace("Z", "+00:00"))
            ws.append(
                [
                    "Grupno testiranje",
                    start.astimezone().strftime("%d.%m.%Y %H:%M"),
                    ap.get("duration_minutes", GRUPNO_TRAJANJE),
                    GRUPNI_PROGRAM,
                    r["client_name"],
                    r["client_email"],
                    "DA" if r.get("reminder_sent") else "NE",
                ]
            )

        excel_data = io.BytesIO()
        wb.save(excel_data)
        excel_data.seek(0)

        st.download_button(
            label="📥 Preuzmi Excel tablicu rezervacija",
            data=excel_data,
            file_name=f"rezervacije_{datetime.now().strftime('%d.%m.%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # ----------------------------------------------------
        # POTPUNO ČIŠĆENJE
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader("🚨 Potpuno čišćenje")

        potvrda_ciscenja = st.checkbox(
            "Želim obrisati sve termine i rezervacije."
        )

        if potvrda_ciscenja:
            if st.button("🚨 OČISTI CIJELI SUSTAV", type="secondary"):
                try:
                    supabase.rpc("clear_all_appointments").execute()
                    st.success("Svi termini i rezervacije su očišćeni.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Greška: {e}")

    elif upisana_lozinka:
        st.error("Pogrešna lozinka!")


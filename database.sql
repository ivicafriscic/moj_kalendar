-- ============================================================
-- ONLINE REZERVACIJSKI SUSTAV
-- Supabase / PostgreSQL
-- ============================================================

create extension if not exists pgcrypto;

-- ------------------------------------------------------------
-- TABLICA TERMINA
-- ------------------------------------------------------------

create table if not exists public.appointments (
    id uuid primary key default gen_random_uuid(),

    start_time timestamptz not null,

    duration_minutes integer not null
        check (duration_minutes in (35, 45, 90)),

    program text not null,

    client_name text,
    client_email text,

    status text not null default 'available'
        check (status in ('available', 'reserved', 'cancelled', 'expired')),

    reserved_at timestamptz,

    reminder_sent boolean not null default false,

    created_at timestamptz not null default now()
);

-- Jedan početak termina može postojati samo jednom.
create unique index if not exists appointments_unique_start_time
on public.appointments (start_time);

create index if not exists appointments_status_start_idx
on public.appointments (status, start_time);

create index if not exists appointments_reminder_idx
on public.appointments (status, reminder_sent, start_time);


-- ============================================================
-- FUNKCIJA: ATOMSKA REZERVACIJA
-- ============================================================

create or replace function public.reserve_appointment(
    p_appointment_id uuid,
    p_client_name text,
    p_client_email text
)
returns setof public.appointments
language plpgsql
security definer
set search_path = public
as $$
begin

    return query
    update public.appointments
    set
        status = 'reserved',
        client_name = trim(p_client_name),
        client_email = lower(trim(p_client_email)),
        reserved_at = now(),
        reminder_sent = false
    where id = p_appointment_id
      and status = 'available'
      and start_time > now()
    returning *;

end;
$$;


-- ============================================================
-- FUNKCIJA: AUTOMATSKO ČIŠĆENJE ZAVRŠENIH TERMINA
-- ============================================================

create or replace function public.cleanup_expired_appointments()
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
    broj integer;
begin

    update public.appointments
    set status = 'expired'
    where status in ('available', 'reserved')
      and start_time
          + make_interval(mins => duration_minutes)
          <= now();

    get diagnostics broj = row_count;

    return broj;
end;
$$;


-- ============================================================
-- FUNKCIJA: TERMINI KOJIMA TREBA POSLATI PODSJETNIK
--
-- Podaci se vraćaju aplikaciji koja onda šalje e-mail.
-- Podsjetnik se smatra dospjelim kada je termin približno
-- 4 sata udaljen (+/- 5 minuta).
-- ============================================================

create or replace function public.get_due_reminders()
returns setof public.appointments
language plpgsql
security definer
set search_path = public
as $$
begin

    return query
    select *
    from public.appointments
    where status = 'reserved'
      and reminder_sent = false
      and start_time > now()
      and start_time <= now() + interval '4 hours 5 minutes'
      and start_time >= now() + interval '3 hours 55 minutes'
    order by start_time;

end;
$$;


-- ============================================================
-- FUNKCIJA: OZNAČI PODSJETNIK KAO POSLAN
-- ============================================================

create or replace function public.mark_reminder_sent(
    p_appointment_id uuid
)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
    broj integer;
begin

    update public.appointments
    set reminder_sent = true
    where id = p_appointment_id
      and status = 'reserved'
      and reminder_sent = false;

    get diagnostics broj = row_count;

    return broj = 1;
end;
$$;


-- ============================================================
-- FUNKCIJA: POTPUNO ČIŠĆENJE
-- Koristi je samo admin aplikacija.
-- ============================================================

create or replace function public.clear_all_appointments()
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin

    delete from public.appointments;

    return true;
end;
$$;


-- ============================================================
-- DOZVOLE
--
-- Aplikacija koristi SUPABASE_SERVICE_KEY na serverskoj strani.
-- Service role zaobilazi RLS.
--
-- Dodatno ograničavamo funkcije tako da ih može koristiti
-- service_role.
-- ============================================================

revoke all on function public.reserve_appointment(uuid, text, text)
from public, anon, authenticated;

grant execute on function public.reserve_appointment(uuid, text, text)
to service_role;


revoke all on function public.cleanup_expired_appointments()
from public, anon, authenticated;

grant execute on function public.cleanup_expired_appointments()
to service_role;


revoke all on function public.get_due_reminders()
from public, anon, authenticated;

grant execute on function public.get_due_reminders()
to service_role;


revoke all on function public.mark_reminder_sent(uuid)
from public, anon, authenticated;

grant execute on function public.mark_reminder_sent(uuid)
to service_role;


revoke all on function public.clear_all_appointments()
from public, anon, authenticated;

grant execute on function public.clear_all_appointments()
to service_role;


-- ============================================================
-- RLS
--
-- U ovoj arhitekturi javna web stranica ne koristi anon ključ
-- za bazu. Streamlit server koristi SERVICE ROLE ključ.
-- Zato javni korisnik nikada ne dobiva pristup bazi.
-- ============================================================

alter table public.appointments enable row level security;


-- Uklanjamo eventualne stare politike koje bi slučajno
-- otvorile bazu javnosti.
drop policy if exists "Public can read appointments"
on public.appointments;

drop policy if exists "Public can insert appointments"
on public.appointments;

drop policy if exists "Public can update appointments"
on public.appointments;


-- ============================================================
-- OPCIONALNI SUPABASE CRON
--
-- Ako je pg_cron omogućen u Supabase projektu, možeš uključiti
-- ovaj dio kako bi se istekli termini čistili i kada nitko
-- nema otvoren Streamlit.
--
-- Podsjetnike NE šalje PostgreSQL jer slanje SMTP e-maila
-- nije posao ove SQL funkcije. Streamlit ih šalje kada izvrši
-- get_due_reminders().
-- ============================================================

-- create extension if not exists pg_cron with schema extensions;

-- select cron.schedule(
--     'cleanup-expired-appointments',
--     '*/5 * * * *',
--     $$select public.cleanup_expired_appointments();$$
-- );

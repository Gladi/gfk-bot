"""
GFK-Bot - SQLite-Zugriff.

Eine Datei (Standard /app/data/gfk.db, Umgebungsvariable GFK_DB_FILE). Jede Funktion öffnet ihre eigene Verbindung
(Commit bei Erfolg, Rollback bei Fehler); die async-Varianten laufen in einem Worker-Thread, damit der Bot nicht
blockiert. Tabellen wie im Design-Dokument (Abschnitt 7); spätere Pakete füllen sie.
"""
import asyncio
import contextlib
import functools
import os
import sqlite3
from typing import Dict, Optional

DB_FILE = os.environ.get("GFK_DB_FILE") or ("/app/data/gfk.db" if os.path.isdir("/app/data") else "gfk.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
    guild_id INTEGER NOT NULL,
    key      TEXT    NOT NULL,
    value    TEXT    NOT NULL,
    PRIMARY KEY (guild_id, key)
);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL, thread_id INTEGER, reporter_id INTEGER NOT NULL,
    category TEXT NOT NULL, alliance TEXT, player TEXT NOT NULL, description TEXT NOT NULL,
    created_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', closed_by INTEGER, closed_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL, type TEXT NOT NULL, category TEXT NOT NULL,
    start_at TEXT NOT NULL, end_at TEXT NOT NULL, description TEXT, creator_id INTEGER NOT NULL, title TEXT,
    message_id INTEGER, thread_id INTEGER, voice_channel_id INTEGER, discord_event_id INTEGER,
    status TEXT NOT NULL DEFAULT 'planned', reminded INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS event_participants (
    event_id INTEGER NOT NULL, user_id INTEGER NOT NULL, state TEXT NOT NULL,
    PRIMARY KEY (event_id, user_id)
);
CREATE TABLE IF NOT EXISTS role_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL, actor_id INTEGER NOT NULL, target_id INTEGER NOT NULL,
    old_role TEXT, new_role TEXT, at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stfc_roster (
    player_id INTEGER PRIMARY KEY, name TEXT NOT NULL, tag TEXT NOT NULL, rank TEXT NOT NULL,
    fetched_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS notices (
    guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, message_id INTEGER NOT NULL,
    PRIMARY KEY (guild_id, message_id)
);
CREATE TABLE IF NOT EXISTS members (
    guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
    alliance TEXT NOT NULL, game_name TEXT NOT NULL, stfc_player_id INTEGER, nick_synced_at TEXT,
    PRIMARY KEY (guild_id, user_id)
);
"""


@contextlib.contextmanager
def _conn():
    """Eigene Verbindung pro Aufruf: Commit bei Erfolg, Rollback bei Fehler, immer schließen."""
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    try:
        conn.execute("PRAGMA busy_timeout=10000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _async(fn):
    """Führt eine synchrone DB-Funktion in einem Worker-Thread aus."""
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        return await asyncio.to_thread(fn, *args, **kwargs)
    return wrapper


def init():
    with _conn() as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.executescript(SCHEMA)
        # Nachträglich hinzugekommene Spalten (ältere Datenbanken)
        columns = {r[1] for r in conn.execute("PRAGMA table_info(events)")}
        if "title" not in columns:
            conn.execute("ALTER TABLE events ADD COLUMN title TEXT")
        columns = {r[1] for r in conn.execute("PRAGMA table_info(reports)")}
        if "progress_by" not in columns:
            conn.execute("ALTER TABLE reports ADD COLUMN progress_by INTEGER")
            conn.execute("ALTER TABLE reports ADD COLUMN progress_at TEXT")


# ----------------- Konfiguration (pro Server, Schlüssel -> Wert) -----------------
def get_config_sync(guild_id: int) -> Dict[str, str]:
    with _conn() as conn:
        return dict(conn.execute("SELECT key, value FROM config WHERE guild_id = ?", (guild_id,)))


def set_config_sync(guild_id: int, values: Dict[str, Optional[str]]):
    """Setzt mehrere Werte auf einmal; None löscht den Schlüssel."""
    with _conn() as conn:
        for key, value in values.items():
            if value is None:
                conn.execute("DELETE FROM config WHERE guild_id = ? AND key = ?", (guild_id, key))
            else:
                conn.execute("INSERT INTO config (guild_id, key, value) VALUES (?, ?, ?) "
                             "ON CONFLICT (guild_id, key) DO UPDATE SET value = excluded.value", (guild_id, key, value))


get_config = _async(get_config_sync)
set_config = _async(set_config_sync)


# ----------------- Mitglieder (Eingangskontrolle, Abgleich mit stfc.pro) -----------------
def save_member_sync(guild_id: int, user_id: int, alliance: str, game_name: str, player_id: Optional[int]):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO members (guild_id, user_id, alliance, game_name, stfc_player_id, nick_synced_at) "
            "VALUES (?, ?, ?, ?, ?, datetime('now')) ON CONFLICT (guild_id, user_id) DO UPDATE SET "
            "alliance = excluded.alliance, game_name = excluded.game_name, stfc_player_id = excluded.stfc_player_id, "
            "nick_synced_at = excluded.nick_synced_at", (guild_id, user_id, alliance, game_name, player_id))


def get_member_sync(guild_id: int, user_id: int):
    with _conn() as conn:
        return conn.execute("SELECT alliance, game_name, stfc_player_id FROM members WHERE guild_id = ? AND user_id = ?",
                            (guild_id, user_id)).fetchone()


def linked_members_sync(guild_id: int):
    """(user_id, alliance, game_name, stfc_player_id) aller Mitglieder mit Spieler-ID."""
    with _conn() as conn:
        return conn.execute("SELECT user_id, alliance, game_name, stfc_player_id FROM members "
                            "WHERE guild_id = ? AND stfc_player_id IS NOT NULL", (guild_id,)).fetchall()


def unlinked_gfk_members_sync(guild_id: int, tag: str = "GFK"):
    """(user_id, game_name) von Mitgliedern mit GFK-Kürzel, die noch keiner Spieler-ID zugeordnet sind."""
    with _conn() as conn:
        return conn.execute("SELECT user_id, game_name FROM members WHERE guild_id = ? AND upper(alliance) = ? "
                            "AND stfc_player_id IS NULL", (guild_id, tag)).fetchall()


# ----------------- letzte Mitgliederliste von stfc.pro (nur aktueller Stand, kein Verlauf) -----------------
def save_roster_sync(players, fetched_at: float):
    """players: Iterable von (player_id, name, tag, rank). Ersetzt den gespeicherten Stand komplett."""
    with _conn() as conn:
        conn.execute("DELETE FROM stfc_roster")
        conn.executemany("INSERT INTO stfc_roster (player_id, name, tag, rank, fetched_at) VALUES (?, ?, ?, ?, ?)",
                         [(*p, fetched_at) for p in players])


def load_roster_sync():
    """(Liste von (player_id, name, tag, rank), Zeitpunkt des Abrufs als Unix-Zeit) - leer: ([], None)."""
    with _conn() as conn:
        rows = conn.execute("SELECT player_id, name, tag, rank, fetched_at FROM stfc_roster").fetchall()
    return ([r[:4] for r in rows], rows[0][4]) if rows else ([], None)


def delete_member_sync(guild_id: int, user_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM members WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))


def log_role_change_sync(guild_id: int, actor_id: int, target_id: int, old: str, new: str):
    with _conn() as conn:
        conn.execute("INSERT INTO role_log (guild_id, actor_id, target_id, old_role, new_role, at) "
                     "VALUES (?, ?, ?, ?, ?, datetime('now'))", (guild_id, actor_id, target_id, old, new))


save_member = _async(save_member_sync)
get_member = _async(get_member_sync)
linked_members = _async(linked_members_sync)
delete_member = _async(delete_member_sync)
unlinked_gfk_members = _async(unlinked_gfk_members_sync)
save_roster = _async(save_roster_sync)
load_roster = _async(load_roster_sync)
log_role_change = _async(log_role_change_sync)


# ----------------- Meldungen -----------------
def _row(conn):
    conn.row_factory = sqlite3.Row
    return conn


def create_report_sync(guild_id: int, reporter_id: int, category: str, alliance: str, player: str,
                       description: str) -> int:
    with _conn() as conn:
        cur = conn.execute("INSERT INTO reports (guild_id, reporter_id, category, alliance, player, description, "
                           "created_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                           (guild_id, reporter_id, category, alliance, player, description))
        return cur.lastrowid


def set_report_thread_sync(report_id: int, thread_id: int):
    with _conn() as conn:
        conn.execute("UPDATE reports SET thread_id = ? WHERE id = ?", (thread_id, report_id))


def get_report_sync(report_id: int):
    with _conn() as conn:
        row = _row(conn).execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        return dict(row) if row else None


def close_report_sync(report_id: int, closed_by: int) -> bool:
    """True, wenn die Meldung bis eben offen oder in Bearbeitung war (doppelte Klicks schließen nicht zweimal)."""
    with _conn() as conn:
        cur = conn.execute("UPDATE reports SET status = 'done', closed_by = ?, closed_at = datetime('now') "
                           "WHERE id = ? AND status IN ('open', 'progress')", (closed_by, report_id))
        return cur.rowcount == 1


def progress_report_sync(report_id: int, user_id: int) -> bool:
    """Offen -> In Bearbeitung. True nur beim ersten Mal."""
    with _conn() as conn:
        cur = conn.execute("UPDATE reports SET status = 'progress', progress_by = ?, progress_at = datetime('now') "
                           "WHERE id = ? AND status = 'open'", (user_id, report_id))
        return cur.rowcount == 1


def report_rows_sync(guild_id: int):
    """(Kategorie, Allianz, Spieler, Zeitpunkt als Unix-Zeit) aller Meldungen - Grundlage der Statistik."""
    with _conn() as conn:
        return conn.execute("SELECT category, alliance, player, CAST(strftime('%s', created_at) AS INTEGER) "
                            "FROM reports WHERE guild_id = ? AND thread_id IS NOT NULL", (guild_id,)).fetchall()


def delete_report_sync(report_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))


create_report = _async(create_report_sync)
set_report_thread = _async(set_report_thread_sync)
get_report = _async(get_report_sync)
close_report = _async(close_report_sync)
progress_report = _async(progress_report_sync)
report_rows = _async(report_rows_sync)
delete_report = _async(delete_report_sync)


# ----------------- Events -----------------
EVENT_FIELDS = {"title", "category", "start_at", "end_at", "description", "message_id", "thread_id", "voice_channel_id",
                "discord_event_id", "status", "reminded"}


def create_event_sync(guild_id: int, kind: str, title: str, category: str, start_at: str, end_at: str,
                      description: str, creator_id: int, reminded: int) -> int:
    with _conn() as conn:
        cur = conn.execute("INSERT INTO events (guild_id, type, title, category, start_at, end_at, description, "
                           "creator_id, reminded) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (guild_id, kind, title, category, start_at, end_at, description, creator_id, reminded))
        return cur.lastrowid


def update_event_sync(event_id: int, **fields):
    bad = set(fields) - EVENT_FIELDS
    if bad:
        raise ValueError(bad)
    if not fields:
        return
    with _conn() as conn:
        conn.execute(f"UPDATE events SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?",
                     (*fields.values(), event_id))


def get_event_sync(event_id: int):
    with _conn() as conn:
        row = _row(conn).execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        return dict(row) if row else None


def active_events_sync(guild_id: int):
    """Alle noch nicht aufgeräumten Events (geplant, beendet, abgesagt), früheste zuerst."""
    with _conn() as conn:
        return [dict(r) for r in _row(conn).execute(
            "SELECT * FROM events WHERE guild_id = ? AND status IN ('planned', 'ended', 'cancelled') "
            "ORDER BY start_at, id", (guild_id,))]


def event_by_voice_sync(voice_channel_id: int):
    with _conn() as conn:
        row = _row(conn).execute("SELECT * FROM events WHERE voice_channel_id = ?", (voice_channel_id,)).fetchone()
        return dict(row) if row else None


def set_participant_sync(event_id: int, user_id: int, state: Optional[str]):
    """state None entfernt den Eintrag."""
    with _conn() as conn:
        if state is None:
            conn.execute("DELETE FROM event_participants WHERE event_id = ? AND user_id = ?", (event_id, user_id))
        else:
            conn.execute("INSERT INTO event_participants (event_id, user_id, state) VALUES (?, ?, ?) "
                         "ON CONFLICT (event_id, user_id) DO UPDATE SET state = excluded.state",
                         (event_id, user_id, state))


def participants_sync(event_id: int) -> Dict[int, str]:
    """{user_id: state} in Reihenfolge der Anmeldung."""
    with _conn() as conn:
        return dict(conn.execute("SELECT user_id, state FROM event_participants WHERE event_id = ? ORDER BY rowid",
                                 (event_id,)))


create_event = _async(create_event_sync)
update_event = _async(update_event_sync)
get_event = _async(get_event_sync)
active_events = _async(active_events_sync)
event_by_voice = _async(event_by_voice_sync)
set_participant = _async(set_participant_sync)
participants = _async(participants_sync)


# ----------------- Karten in "Verwaltung" (neuer Gast, Kürzel entfernt) - verschwinden, sobald entschieden -----------------
def add_notice_sync(guild_id: int, user_id: int, message_id: int):
    with _conn() as conn:
        conn.execute("INSERT OR IGNORE INTO notices (guild_id, user_id, message_id) VALUES (?, ?, ?)",
                     (guild_id, user_id, message_id))


def pop_notices_sync(guild_id: int, user_id: int):
    """Nachrichten-IDs der Karten zu einer Person - und aus der Tabelle entfernen."""
    with _conn() as conn:
        ids = [r[0] for r in conn.execute("SELECT message_id FROM notices WHERE guild_id = ? AND user_id = ?",
                                          (guild_id, user_id))]
        conn.execute("DELETE FROM notices WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    return ids


add_notice = _async(add_notice_sync)
pop_notices = _async(pop_notices_sync)

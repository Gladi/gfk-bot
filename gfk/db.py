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
    start_at TEXT NOT NULL, end_at TEXT NOT NULL, description TEXT, creator_id INTEGER NOT NULL,
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
log_role_change = _async(log_role_change_sync)

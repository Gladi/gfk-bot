"""
GFK-Bot - SQLite-Zugriff: alles aus botcore.db (Einstellungen, Meldungen, Events) plus die GFK-eigenen Tabellen
(Mitglieder mit stfc.pro-Verknüpfung, gespeicherte stfc.pro-Liste, Karten in Verwaltung, Rollen-Protokoll).
"""
from typing import Optional

from botcore.db import *  # noqa: F401,F403
from botcore.db import _async, _conn, register

SCHEMA_GFK = """
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
# Deinstallation: auch die gespeicherte stfc.pro-Liste löschen
register(SCHEMA_GFK, guild_tables=["role_log", "notices", "members"], global_tables=["stfc_roster"])


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


def all_notices_sync(guild_id: int):
    """Nachrichten-IDs aller offenen Karten in Verwaltung."""
    with _conn() as conn:
        return [r[0] for r in conn.execute("SELECT message_id FROM notices WHERE guild_id = ?", (guild_id,))]


def delete_member_sync(guild_id: int, user_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM members WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))


def log_role_change_sync(guild_id: int, actor_id: int, target_id: int, old: str, new: str):
    with _conn() as conn:
        conn.execute("INSERT INTO role_log (guild_id, actor_id, target_id, old_role, new_role, at) "
                     "VALUES (?, ?, ?, ?, ?, datetime('now'))", (guild_id, actor_id, target_id, old, new))


all_notices = _async(all_notices_sync)
save_member = _async(save_member_sync)
get_member = _async(get_member_sync)
linked_members = _async(linked_members_sync)
delete_member = _async(delete_member_sync)
unlinked_gfk_members = _async(unlinked_gfk_members_sync)
save_roster = _async(save_roster_sync)
load_roster = _async(load_roster_sync)
log_role_change = _async(log_role_change_sync)


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

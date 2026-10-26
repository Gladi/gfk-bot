"""
GFK-Bot - welche Rollen und Kanäle der Bot kennen muss, und Prüfungen dafür (ohne Discord-Aufrufe, gut testbar).

Die Werte setzen Server-Admins mit /setup; gespeichert werden IDs in der Tabelle config.
"""
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

# Status-Rollen von oben nach unten (Hierarchie im Discord: Owner -> Bots -> Admiral -> Führung -> ... -> Gast).
# Neue Nutzer haben keine Rolle; bei neuen Vorfällen wird die Führung markiert.
STATUS_ROLES = ["admiral", "fuehrung", "mitglied", "freund", "gast"]
ROLE_KEYS = {
    "admiral": "Admiral", "fuehrung": "Führung", "mitglied": "Mitglied", "freund": "Freund", "gast": "Gast",
}
CHANNEL_KEYS = {
    "eingang": "Eingangskanal", "meldungen": "Meldungskanal", "vorfallforum": "Vorfallforum", "events": "Eventkanal",
    "event_kategorie": "Event-Kategorie (Sprachkanäle)", "verwaltung": "Verwaltung (Nachrichten an die Führung)",
}
# Server-Logs (ersetzen SCNX): optional, leer = aus
LOG_KEYS = {"log_user": "user-log", "log_rollen": "rollen-log", "log_kanal": "kanal-log", "log_msg": "msg-log"}
MSG_DAYS_KEY = "msg_tage"
MSG_DAYS_DEFAULT, MSG_DAYS_MIN, MSG_DAYS_MAX = 7, 1, 30
# Meldungen: Kategorien und Forum-Tags (Kategorie + Status)
REPORT_CATEGORIES = {"roe": "ROE-Verstoß", "nullnode": "Null-Node", "sonstiges": "Sonstiges"}
REPORT_STATUS_TAGS = {"open": "Offen", "done": "Erledigt"}
REPORT_TAGS = list(REPORT_CATEGORIES.values()) + list(REPORT_STATUS_TAGS.values())
# Schon vorhandene Forum-Tags, die als Bot-Tag zählen (GFK-Server: "0-Node", "Neue Meldung") - keine Doppelten anlegen
REPORT_TAG_ALIASES = {"Null-Node": ["0-Node"], "Offen": ["Neue Meldung"]}
REPORT_CLEARED_ON_DONE = ["In Bearbeitung"]      # von Hand gesetzte Zwischenstände, die "Erledigt" entfernt


def tag_names(name: str) -> List[str]:
    """Ein Bot-Tag und die vorhandenen Tags, die dafür zählen (in dieser Reihenfolge gesucht)."""
    return [name] + REPORT_TAG_ALIASES.get(name, [])


def has_tag(existing: Iterable[str], name: str) -> bool:
    have = {n.casefold() for n in existing}
    return any(n.casefold() in have for n in tag_names(name))
REMINDER_KEY = "erinnerung_minuten"
REMINDER_DEFAULT, REMINDER_MIN, REMINDER_MAX = 30, 5, 240
# Rollen, die der Bot selbst vergibt - die Bot-Rolle muss über all diesen stehen
MANAGED_ROLES = ["fuehrung", "mitglied", "freund", "gast"]


def role_key(name: str) -> str:
    return f"role_{name}"


def channel_key(name: str) -> str:
    return f"channel_{name}"


def reminder_minutes(config: Dict[str, str]) -> int:
    try:
        value = int(config.get(REMINDER_KEY, REMINDER_DEFAULT))
    except ValueError:
        return REMINDER_DEFAULT
    return min(max(value, REMINDER_MIN), REMINDER_MAX)


def msg_days(config: Dict[str, str]) -> int:
    """Wie lange der msg-log Nachrichten im Arbeitsspeicher behält (Tage)."""
    try:
        value = int(config.get(MSG_DAYS_KEY, MSG_DAYS_DEFAULT))
    except ValueError:
        return MSG_DAYS_DEFAULT
    return min(max(value, MSG_DAYS_MIN), MSG_DAYS_MAX)


def missing(config: Dict[str, str]) -> List[str]:
    """Noch nicht eingerichtete Einträge (Anzeigenamen)."""
    out = [label for key, label in ROLE_KEYS.items() if role_key(key) not in config]
    out += [label for key, label in CHANNEL_KEYS.items() if channel_key(key) not in config]
    return out


@dataclass
class RoleInfo:
    key: str
    name: str
    position: int


def unmanageable(bot_top_position: int, roles: Iterable[RoleInfo]) -> List[str]:
    """Rollen, die der Bot nicht vergeben kann, weil sie nicht unter seiner höchsten Rolle stehen."""
    return [r.name for r in roles if r.position >= bot_top_position]


def order_problems(roles: Dict[str, Optional[int]]) -> List[str]:
    """Prüft die Reihenfolge der Status-Rollen (Position: größer = weiter oben). Liefert Hinweise auf Vertauschungen."""
    present = [(key, roles[key]) for key in STATUS_ROLES if roles.get(key) is not None]
    return [f"{ROLE_KEYS[a]} sollte über {ROLE_KEYS[b]} stehen"
            for (a, pa), (b, pb) in zip(present, present[1:]) if pa <= pb]

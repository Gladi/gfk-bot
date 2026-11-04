"""
GFK-Bot - welche Rollen und Kanäle der Bot kennen muss. Prüfungen und Grundwerte kommen aus botcore.settings; hier
stehen die GFK-eigenen Einträge (Status-Rollen, Eingang, Verwaltung, Server-Logs).

Die Werte setzen Server-Admins mit /setup; gespeichert werden IDs in der Tabelle config.
"""
from typing import Dict

from botcore import settings as _core
from botcore.settings import *  # noqa: F401,F403

# Status-Rollen von oben nach unten (Hierarchie im Discord: Owner -> Bots -> Admiral -> Führung -> ... -> Gast).
# Neue Nutzer haben keine Rolle; bei neuen Vorfällen wird die Führung markiert.
STATUS_ROLES = ["admiral", "fuehrung", "mitglied", "freund", "gast"]
ROLE_KEYS.update({
    "admiral": "Admiral", "fuehrung": "Führung", "mitglied": "Mitglied", "freund": "Freund", "gast": "Gast",
})
ROLE_ORDER[:] = STATUS_ROLES
CHANNEL_KEYS.update({
    "eingang": "Eingangskanal", "meldungen": "Meldungskanal", "vorfallforum": "Vorfallforum", "events": "Eventkanal",
    "event_kategorie": "Event-Kategorie (Sprachkanäle)", "verwaltung": "Verwaltung (Nachrichten an die Führung)",
})
# Optionale Kanäle (fehlen nicht in der Prüfung): weitere Stelle für die Nachricht "Namen ändern"
OPTIONAL_CHANNEL_KEYS.update({"eingang_info": "Zusätzlich „Namen ändern“",
                              "namen_log": "Namensänderungen (Spielname geändert)",
                              "logbuch": "Logbuch (Beitrag „Vorfall Statistik“)"})
# Zusätzliche Kanäle je fester Nachricht (Art -> Kanal-Schlüssel)
PANEL_EXTRA_CHANNELS.update({"lobby": ["eingang_info"]})
CHANNEL_PERMS.update({
    "eingang": ["view_channel", "send_messages", "embed_links"],
    **{k: _core.PERMS[k] for k in ("meldungen", "vorfallforum", "events", "event_kategorie", "verwaltung")},
    "eingang_info": ["view_channel", "send_messages", "embed_links"],
    "namen_log": ["view_channel", "send_messages_in_threads"],
    "logbuch": _core.PERMS["logbuch"],
})
GUILD_PERMS[:] = ["manage_roles", "manage_nicknames"] + _core.EVENT_GUILD_PERMS
# Server-Logs (ersetzen SCNX): optional, leer = aus
LOG_KEYS = {"log_user": "user-log", "log_rollen": "rollen-log", "log_kanal": "kanal-log", "log_msg": "msg-log"}
MSG_DAYS_KEY = "msg_tage"
MSG_DAYS_DEFAULT, MSG_DAYS_MIN, MSG_DAYS_MAX = 7, 1, 30
# Rollen, die der Bot selbst vergibt - die Bot-Rolle muss über all diesen stehen
MANAGED_ROLES[:] = ["fuehrung", "mitglied", "freund", "gast"]


def msg_days(config: Dict[str, str]) -> int:
    """Wie lange der msg-log Nachrichten im Arbeitsspeicher behält (Tage)."""
    try:
        value = int(config.get(MSG_DAYS_KEY, MSG_DAYS_DEFAULT))
    except ValueError:
        return MSG_DAYS_DEFAULT
    return min(max(value, MSG_DAYS_MIN), MSG_DAYS_MAX)

"""GFK-Bot - Texte (Deutsch). Platzhalter in {geschweiften Klammern}."""

T = {
    "error": "⚠️ Da ist etwas schiefgelaufen. Bitte versuche es noch einmal oder melde dich bei einem Admin.",
    "admin_only": "🔒 Das dürfen nur Server-Admins.",
    "follows": "🛠️ Diese Funktion kommt in einem der nächsten Pakete.",
    "setup_saved": "✅ Gespeichert: {items}",
    "setup_nothing": "ℹ️ Nichts angegeben - es wurde nichts geändert.",
    "setup_reminder": "✅ Erinnerung kommt {minutes} Minuten vor Beginn.",
    "setup_title": "⚙️ GFK-Bot - Einstellungen",
    "setup_roles": "Rollen",
    "setup_channels": "Kanäle",
    "setup_reminder_field": "Erinnerung",
    "setup_reminder_value": "{minutes} Minuten vor Beginn",
    "setup_unset": "– nicht gesetzt –",
    "setup_checks": "Prüfung",
    "setup_ok": "✅ Alles eingerichtet.",
    "setup_missing": "Fehlt noch: {items}",
    "setup_hierarchy": "Die Bot-Rolle muss über diesen Rollen stehen: {items}",
    "setup_order": "Reihenfolge der Rollen: {items}",
    "setup_perm": "Fehlende Rechte: {items}",
    "panels_posted": "✅ Feste Nachrichten gepostet: {items}",
    "panels_missing": "⚠️ Erst die Kanäle einrichten (`/setup kanäle`): {items}",
    # Feste Nachrichten (Panels)
    "panel_lobby_title": "👋 Willkommen!",
    "panel_lobby_text": "Bitte trage deine **Allianz** und deinen **Spielnamen** ein. Danach heißt du hier `[ALLY] Name`.",
    "panel_lobby_button": "Namen ändern",
    "panel_report_title": "🚨 Vorfall melden",
    "panel_report_text": "ROE-Verstoß, Null-Node oder etwas anderes? Melde es hier - mit Screenshots.",
    "panel_report_button": "Meldung erstellen",
    "panel_event_title": "📅 Events",
    "panel_event_text": "Plane ein Armada, eine Welle, einen Ansturm oder etwas anderes - für die ganze Allianz oder privat.",
    "panel_event_button": "Neues Event planen",
    "log_setup": "⚙️ {user} hat die Einstellungen geändert: {items}",
}


def t(key: str, **kw) -> str:
    text = T[key]
    return text.format(**kw) if kw else text

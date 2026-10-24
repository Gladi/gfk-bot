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
    "panel_lobby_text": "Bitte trage dein **Allianzkürzel** (optional) und deinen **Spielnamen** ein. Danach heißt du "
                        "hier `[ALLY] Name` - ohne Allianz einfach `Name`.",
    "panel_lobby_button": "Namen ändern",
    "panel_report_title": "🚨 Vorfall melden",
    "panel_report_text": "ROE-Verstoß, Null-Node oder etwas anderes? Melde es hier - mit Screenshots.",
    "panel_report_button": "Meldung erstellen",
    "panel_event_title": "📅 Events",
    "panel_event_text": "Plane ein Armada, eine Welle, einen Ansturm oder etwas anderes - für die ganze Allianz oder privat.",
    "panel_event_button": "Neues Event planen",
    "log_setup": "⚙️ {user} hat die Einstellungen geändert: {items}",
    # Eingangskontrolle
    "name_modal_title": "Namen ändern",
    "name_tag_label": "Allianzkürzel (optional)",
    "name_tag_placeholder": "z. B. GFK - leer lassen, wenn du in keiner Allianz bist",
    "name_name_label": "Spielname",
    "name_bad_input": "⚠️ Bitte prüfe deine Eingabe: Das Kürzel darf nur Buchstaben und Ziffern haben (höchstens 6), "
                      "der Spielname darf nicht leer sein.",
    "name_done": "✅ Du heißt jetzt **{nick}**.",
    "name_done_guest": "Willkommen! Die Führung schaut sich deinen Eintrag gleich an.",
    "name_no_nick_perm": "⚠️ Deinen Nickname kann der Bot nicht ändern (Server-Owner oder Rolle über dem Bot). "
                         "Bitte stelle ihn selbst auf **{nick}**.",
    "name_not_found": "🔎 **{name}** steht nicht genau so in der GFK-Mitgliederliste auf stfc.pro. Wähle deinen Namen "
                      "aus der Liste - sonst prüfe die Schreibweise (genau wie im Spiel).",
    "name_not_found_none": "🔎 **{name}** steht nicht in der GFK-Mitgliederliste auf stfc.pro. Bitte schreibe deinen Namen "
                           "genau wie im Spiel. Gerade erst GFK beigetreten? stfc.pro aktualisiert nur alle paar "
                           "Stunden - versuche es später noch einmal.",
    "name_stfc_down": "⚠️ stfc.pro ist gerade nicht erreichbar, deshalb kann dein GFK-Name nicht geprüft werden. Bitte "
                      "versuche es in ein paar Minuten noch einmal.",
    "name_select_placeholder": "Spielname auswählen",
    "verw_new_guest_title": "🆕 Neuer Gast",
    "verw_new_guest": "{user} heißt jetzt **{nick}**.",
    "verw_stfc_ok": "✅ In der GFK-Liste gefunden ({rank})",
    "verw_stfc_missing": "❔ Nicht in der GFK-Liste gefunden",
    "verw_alliance": "Allianz",
    "verw_no_ally": "ohne Allianz",
    "verw_status_set": "➡️ {target} ist jetzt **{role}** (durch {actor})",
    "status_denied": "🔒 Das darfst du nicht. Freund und Mitglied vergibt die Führung, Führung nur der Admiral.",
    "status_gone": "⚠️ Die Person ist nicht mehr auf dem Server.",
    "name_demoted": "ℹ️ Ohne das Kürzel GFK bist du jetzt Gast - Mitglied und Führung gibt es nur für GFK.",
    "verw_demoted_title": "⬇️ GFK-Kürzel entfernt",
    "verw_demoted": "{user} heißt jetzt **{nick}** und ist deshalb wieder Gast (vorher: {old}). "
                    "Soll {user} Freund werden?",
    "status_gfk_only": "🔒 {role} gibt es nur für GFK. {target} ist mit {tag} eingetragen - erst den Namen mit dem "
                       "Kürzel GFK ändern lassen (Button „Namen ändern“).",
    "status_done": "✅ {target} ist jetzt **{role}**.",
    "status_already": "ℹ️ {target} ist schon **{role}**.",
    "sync_renamed": "✏️ Abgleich mit stfc.pro: {user} heißt jetzt **{nick}** (vorher {old}).",
    "sync_left": "👋 {user} ({name}) steht laut stfc.pro nicht mehr in der GFK-Liste.",
    "sync_linked": "🔗 Abgleich mit stfc.pro: {user} steht jetzt in der GFK-Liste ({name}, {rank}) und ist verknüpft.",
}


def t(key: str, **kw) -> str:
    text = T[key]
    return text.format(**kw) if kw else text

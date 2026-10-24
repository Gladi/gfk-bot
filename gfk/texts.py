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
    "setup_off": "aus",
    "setup_logs": "Server-Logs",
    "setup_msg_days": "msg-log merkt sich Nachrichten {days} Tage (nur im Arbeitsspeicher)",
    "setup_log_off": "{log} aus",
    "setup_msg_intent": "msg-log: Der Message Content Intent ist im Developer Portal aus (Bot -> Privileged Gateway "
                        "Intents) - ohne ihn sieht der Bot keine Nachrichtentexte und der msg-log bleibt leer.",
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
    # Server-Logs
    "log_by": "durch {user}{reason}",
    "log_by_bot": "({reason})",
    "log_join": "📥 Beigetreten", "log_leave": "📤 Verlassen", "log_kick": "👢 Gekickt", "log_ban": "🔨 Gebannt",
    "log_unban": "🔓 Entbannt", "log_nick": "✏️ Nickname geändert", "log_member_roles": "🎭 Rollen geändert",
    "log_timeout": "⏳ Timeout", "log_timeout_end": "⏳ Timeout beendet", "log_until": "Bis",
    "log_timeout_until": "{until}",
    "log_account": "Konto erstellt", "log_new_account": "⚠️ neues Konto,", "log_members": "Mitglieder",
    "log_roles": "Rollen", "log_joined": "Beigetreten", "log_before": "Vorher", "log_after": "Nachher",
    "log_added": "Hinzugefügt", "log_removed": "Entfernt", "log_changes": "Änderungen",
    "log_role_create": "➕ Rolle erstellt", "log_role_delete": "➖ Rolle gelöscht", "log_role_update": "🛠️ Rolle geändert",
    "log_channel_create": "➕ Kanal erstellt", "log_channel_delete": "➖ Kanal gelöscht",
    "log_channel_update": "🛠️ Kanal geändert",
    "log_name_change": "Name: {before} → {after}", "log_color_change": "Farbe: {before} → {after}",
    "log_hoist": "Getrennt anzeigen: {value}", "log_mentionable": "Erwähnbar: {value}",
    "log_category": "Kategorie: {before} → {after}", "log_topic": "Thema: {after}",
    "log_msg_edit": "✏️ Nachricht bearbeitet", "log_msg_delete": "🗑️ Nachricht gelöscht",
    "log_msg_bulk": "🗑️ {count} Nachrichten auf einmal gelöscht",
    "log_msg_where": "{user} in {channel} - [zur Nachricht]({link})", "log_msg_where_short": "{user} in {channel}",
    "log_content": "Inhalt", "log_files": "Dateien",
    "yes": "ja", "no": "nein",
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
    "status_not_self": "🔒 Deinen eigenen Status und den von Bots kannst du hier nicht ändern.",
    "status_none": "kein Status",
    "status_menu": "Status von {target} (aktuell: **{current}**) ändern auf:",
    "status_no_options": "ℹ️ Für {target} (aktuell: **{current}**) kannst du nichts ändern. Mitglied und Führung gibt "
                         "es nur mit geprüftem GFK-Kürzel („Namen ändern“), Führung vergibt nur der Admiral.",
    "status_stale": "⚠️ Das geht inzwischen nicht mehr (Status oder Kürzel haben sich geändert). Bitte neu öffnen.",
    "name_demoted": "ℹ️ Ohne das Kürzel GFK bist du jetzt Gast - Mitglied und Führung gibt es nur für GFK.",
    "verw_demoted_title": "⬇️ GFK-Kürzel entfernt",
    "verw_demoted": "{user} heißt jetzt **{nick}** und ist deshalb wieder Gast (vorher: {old}). "
                    "Soll {user} Freund werden?",
    "status_gfk_only": "🔒 {role} gibt es nur für GFK. {target} hat kein (geprüftes) GFK-Kürzel - erst über den "
                       "Button „Namen ändern“ mit Kürzel GFK eintragen lassen.",
    "status_done": "✅ {target} ist jetzt **{role}**.",
    "status_already": "ℹ️ {target} ist schon **{role}**.",
    "sync_renamed": "✏️ Abgleich mit stfc.pro: {user} heißt jetzt **{nick}** (vorher {old}).",
    "sync_left": "👋 {user} ({name}) steht laut stfc.pro nicht mehr in der GFK-Liste.",
    "sync_linked": "🔗 Abgleich mit stfc.pro: {user} steht jetzt in der GFK-Liste ({name}, {rank}) und ist verknüpft.",
}


def t(key: str, **kw) -> str:
    text = T[key]
    return text.format(**kw) if kw else text

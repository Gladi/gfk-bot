"""GFK-Bot - Texte (Deutsch) zusätzlich zu bzw. anstelle von botcore.texts. Platzhalter in {geschweiften Klammern}."""
from botcore.texts import T, t  # noqa: F401

T.update({
    "internal_only_report": "🔒 Meldungen über den Bot sind nur für GFK-Mitglieder. Gäste und Freunde melden bitte "
                            "von Hand in ihrem Forum.",
    "setup_logs": "Server-Logs",
    "setup_msg_days": "msg-log merkt sich Nachrichten {days} Tage (nur im Arbeitsspeicher)",
    "setup_log_off": "{log} aus",
    "setup_msg_intent": "msg-log: Der Message Content Intent ist im Developer Portal aus (Bot -> Privileged Gateway "
                        "Intents) - ohne ihn sieht der Bot keine Nachrichtentexte und der msg-log bleibt leer.",
    "uninstall_confirm": "⚠️ **GFK-Bot deinstallieren?**\n"
                         "• Gelöscht werden: alle Einstellungen, Verknüpfungen mit stfc.pro, Meldungsdaten, das "
                         "Rollen-Protokoll und alle offenen Events (mit Discord-Event, Karte, Thread und Sprachkanal), "
                         "dazu die Button-Nachrichten und Karten des Bots.\n"
                         "• Es bleiben: Rollen, Kanäle, Nicknames, Beiträge im Vorfallforum und die Log-Kanäle.\n"
                         "• Danach verlässt der Bot den Server. Tägliche Server-Backups enthalten die Daten noch, bis "
                         "sie ablaufen (bis zu 30 Tage).\n\nDas lässt sich nicht rückgängig machen.",
    # Feste Nachrichten (Panels)
    "panel_lobby_title": "👋 Willkommen!",
    "panel_lobby_text": "Bitte trage dein **Allianzkürzel** (optional) und deinen **Spielnamen** ein. Danach heißt du "
                        "hier `[ALLY] Name` - ohne Allianz einfach `Name`.",
    "panel_lobby_button": "Namen ändern",
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
    "status_denied": "🔒 Das darfst du nicht. Freund und Mitglied vergibt die Führung, Führung nur der Admiral.",
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
    "name_change_sync": "✏️ {user} heißt im Spiel jetzt **{new}** (vorher **{old}**) - automatisch erkannt über "
                        "stfc.pro, Nickname angepasst.",
    "name_change_self": "✏️ {user} heißt im Spiel jetzt **{new}** (vorher **{old}**) - selbst über „Namen ändern“ "
                        "eingetragen.",
    "sync_left": "👋 {user} ({name}) steht laut stfc.pro nicht mehr in der GFK-Liste - Nickname jetzt **{nick}**.",
    "sync_left_admiral": "👋 {user} ({name}) steht laut stfc.pro nicht mehr in der GFK-Liste. Beim Admiral ändert "
                         "der Bot weder Nickname noch Rollen - bitte von Hand prüfen.",
    "sync_left_no_perm": "⚠️ {user} ({name}) steht laut stfc.pro nicht mehr in der GFK-Liste, aber der Bot darf "
                         "Nickname oder Rollen nicht ändern (Rolle über der Bot-Rolle) - bitte von Hand anpassen.",
    "sync_left_many": "⚠️ Laut stfc.pro fehlen auf einmal **{n}** verknüpfte Personen in der GFK-Liste: {people}\n"
                      "Zur Sicherheit ändert der Bot nichts automatisch (die Liste könnte fehlerhaft sein) - bitte "
                      "prüfen und bei Bedarf per `/status` anpassen. Solange das so bleibt, kommt diese Meldung bei "
                      "jedem täglichen Abgleich.",
    "verw_left_title": "👋 GFK verlassen",
    "verw_left": "{user} steht laut stfc.pro nicht mehr in der GFK-Liste, heißt jetzt **{nick}** und ist deshalb "
                 "wieder Gast (vorher: {old}). Soll {user} Freund werden?",
    "verw_info_title": "📋 Rollenvergabe - so geht's",
    "verw_info_text": "**1. Neue Leute**\nSie tragen in {eingang} über „Namen ändern“ Kürzel und Spielnamen ein und "
                      "werden automatisch **Gast**. Hier erscheint dann eine Karte mit Buttons.\n\n"
                      "**2. Status vergeben**\nAuf der Karte **Freund**, **Mitglied** oder **Führung** anklicken. "
                      "Später jederzeit: Rechtsklick auf die Person (Handy: lange tippen) → **Apps** → **Status "
                      "ändern**, oder `/status`. Sobald jemand Freund, Mitglied oder Führung ist, verschwindet die "
                      "Karte von selbst.\n\n"
                      "**3. Wer darf was**\n• Führung: Gast, Freund, Mitglied\n• Admiral: zusätzlich Führung\n"
                      "• Niemand ändert sich selbst, den Admiral ändert der Bot nie.\n\n"
                      "**4. Mitglied und Führung nur mit geprüftem GFK-Kürzel**\nDer Nickname beginnt mit `[GFK]` "
                      "**und** der Spielname wurde über „Namen ändern“ auf stfc.pro gefunden. Sonst gibt es nur "
                      "**Freund**. Wer noch nicht verknüpft ist, steht in der Liste darunter.\n\n"
                      "**5. Kürzel entfernt oder GFK verlassen**\nNimmt jemand `[GFK]` aus dem Nickname oder steht "
                      "laut stfc.pro nicht mehr in der GFK-Liste (täglicher Abgleich, der Bot setzt dann den Nickname "
                      "ohne Kürzel), wird er automatisch **Gast** und hier erscheint eine Karte.\n\n"
                      "Jede Änderung steht im user-log.",
    "verw_reports_title": "🚨 Vorfälle - so geht's",
    "verw_reports_text": "**Neue Meldung** (außer 0-Node): Wer sich kümmert, klickt im Beitrag **🔵 In Bearbeitung** - "
                         "dann sehen alle, wer dran ist. Fertig? **✅ Erledigt** - der Beitrag wird archiviert.\n\n"
                         "**0-Node** sind nur Nachweise: keine Buttons, nach **{null_days} Tagen** automatisch "
                         "gelöscht.\n\n"
                         "**Aufräumen** in {forum}: Erledigte Beiträge verschwinden nach **{done_days} Tagen** ohne "
                         "Aktivität. Angepinnte Beiträge bleiben immer.\n\n"
                         "**Statistik**: Wer wie oft gemeldet wurde, steht in {stats} - je Allianz eine Tabelle, "
                         "aktualisiert sich automatisch.",
    "verw_reports_no_stats": "der Vorfall-Statistik im Logbuch",
    "verw_unlinked_title": "🔗 Noch nicht mit stfc.pro verknüpft ({n})",
    "verw_unlinked_none": "✅ Alle [GFK]-Mitglieder sind verknüpft.",
    "verw_unlinked_what": "Was tun?",
    "verw_unlinked_footer": "Aktualisiert sich automatisch",
    "verw_link_title": "🔗 Abgleich der Mitglieder mit stfc.pro",
    "verw_link_summary": "{linked} verknüpft, {already} waren schon verknüpft, {missing} nicht in der GFK-Liste gefunden. "
                         "Rollen und Nicknames wurden nicht verändert.",
    "verw_link_missing": "Nicht gefunden (Nickname-Name)",
    "verw_link_missing_hint": "Bitte „Namen ändern“ im Eingangskanal nutzen. Sonst verknüpft der tägliche Abgleich sie "
                              "automatisch, sobald stfc.pro sie unter diesem Namen listet.",
    "verw_link_untagged": "Mitglied oder Führung ohne [GFK] im Nickname",
    "verw_link_untagged_hint": "Nur zur Info - der Bot ändert nichts. Ändert jemand davon seinen Nickname, ohne [GFK] "
                               "voranzustellen, wird er automatisch Gast.",
})

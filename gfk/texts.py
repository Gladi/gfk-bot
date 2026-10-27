"""GFK-Bot - Texte (Deutsch). Platzhalter in {geschweiften Klammern}."""

T = {
    "error": "⚠️ Da ist etwas schiefgelaufen. Bitte versuche es noch einmal oder melde dich bei einem Admin.",
    "admin_only": "🔒 Das dürfen nur Server-Admins.",
    "follows": "🛠️ Diese Funktion kommt in einem der nächsten Pakete.",
    "internal_only_report": "🔒 Meldungen über den Bot sind nur für GFK-Mitglieder. Gäste und Freunde melden bitte "
                            "von Hand in ihrem Forum.",
    "internal_only_event": "🔒 Events sind nur für GFK-Mitglieder.",
    # Meldungen
    "rep_modal_title": "Vorfall melden",
    "rep_f_category": "Kategorie", "rep_cat_placeholder": "ROE-Verstoß, Null-Node oder Sonstiges",
    "rep_f_alliance": "Allianz", "rep_alliance_hint": "Optional - leer lassen, wenn der Spieler in keiner Allianz ist",
    "rep_alliance_placeholder": "z. B. ABC",
    "rep_f_player": "Spieler", "rep_f_description": "Was ist passiert?",
    "rep_desc_placeholder": "Wann, wo (System), was genau?",
    "rep_f_files": "Screenshots", "rep_files_hint": "Optional, bis zu 5 Bilder",
    "rep_f_reporter": "Gemeldet von", "rep_f_status": "Status", "rep_open": "🟡 Offen",
    "rep_no_alliance": "keine", "rep_footer": "Meldung #{id}",
    "rep_new_content": "neue Meldung von {user}",
    "rep_bad_input": "⚠️ Spieler und Beschreibung dürfen nicht leer sein.",
    "rep_no_forum": "⚠️ Das Vorfallforum ist noch nicht eingerichtet - bitte einem Admin Bescheid geben.",
    "rep_created": "✅ Danke! Deine Meldung steht hier: {thread}\nWeitere Screenshots kannst du einfach im Beitrag "
                   "posten.",
    "rep_files_skipped": "⚠️ Nicht angehängt (zu groß): {files} - bitte direkt im Beitrag posten.",
    "rep_done_button": "Erledigt", "rep_done_button_done": "Erledigt ✓",
    "rep_progress_button": "In Bearbeitung", "rep_progress_button_done": "In Bearbeitung ✓",
    "rep_progress_by": "🔵 In Bearbeitung: {user} seit {when}",
    "rep_progress_note": "🔵 {user} kümmert sich darum.",
    "rep_progress_denied": "🔒 Übernehmen kann nur die Führung.",
    "rep_progress_already": "ℹ️ Diese Meldung ist schon in Bearbeitung oder erledigt.",
    "rep_proof": "📎 Nachweis - wird nach {days} Tagen automatisch gelöscht",
    "stats_title": "Vorfall Statistik",
    "stats_header": "📊 **Vorfall-Statistik**\nStand: {when} · aktualisiert sich automatisch",
    "rep_done_denied": "🔒 Als erledigt markieren kann nur die Führung.",
    "rep_already_done": "ℹ️ Diese Meldung ist schon erledigt.",
    "rep_done_by": "✅ Erledigt von {user} am {when}",
    "rep_done_note": "✅ Erledigt durch {user}. Der Beitrag wird archiviert - eine neue Antwort holt ihn zurück.",
    # Events
    "ev_choose_kind": "Für wen ist das Event?\n🌐 **Allianzweit** - alle Mitglieder können sich anmelden "
                      "(mit Discord-Event).\n🔒 **Privat** - nur die Leute, die du auswählst.",
    "ev_b_alliance": "Allianzweit", "ev_b_private": "Privat", "ev_b_retry": "Nochmal öffnen",
    "ev_b_cancel_confirm": "Ja, absagen",
    "ev_b_join": "Ich nehme teil", "ev_b_maybe": "Vielleicht", "ev_b_leave": "Abmelden",
    "ev_b_ask": "Ich möchte mitmachen / Habt ihr noch Platz?", "ev_b_edit": "Bearbeiten", "ev_b_cancel": "Absagen",
    "ev_b_accept": "Annehmen", "ev_b_decline": "Ablehnen",
    "ev_modal_alliance": "Allianzweites Event", "ev_modal_private": "Privates Event",
    "ev_modal_edit": "Event bearbeiten",
    "ev_f_category": "Art", "ev_cat_placeholder": "Armada, Welle, Ansturm oder Sonstiges",
    "ev_f_title": "Titel", "ev_title_placeholder": "z. B. Borg-Armada", "ev_title_hint": "Name für Karte, Thread und "
                                                                                          "Sprachkanal",
    "ev_f_when_input": "Wann?", "ev_when_placeholder": "z. B. 25.10. 20:00",
    "ev_when_hint": "TT.MM. HH:MM oder TT.MM.JJJJ HH:MM, auch „morgen 20:00“ - deutsche Zeit",
    "ev_f_duration_input": "Dauer", "ev_duration_placeholder": "1",
    "ev_duration_hint": "In Stunden (1, 1,5, 2) oder Minuten (90min) - leer = 1 Stunde",
    "ev_f_people": "Wer ist dabei?", "ev_people_placeholder": "Mitglieder auswählen",
    "ev_people_hint": "Bis zu 25 GFK-Mitglieder; du bist automatisch dabei",
    "ev_bad_format": "⚠️ Die Zeit habe ich nicht verstanden. Bitte so: `25.10. 20:00` oder `25.10.2026 20:00`.",
    "ev_bad_past": "⚠️ Die Zeit liegt in der Vergangenheit.",
    "ev_bad_far": "⚠️ Höchstens ein Jahr im Voraus.",
    "ev_bad_duration": "⚠️ Die Dauer habe ich nicht verstanden (15 Minuten bis 24 Stunden), z. B. `1`, `1,5` oder "
                       "`90min`.",
    "ev_bad_title": "⚠️ Bitte gib dem Event einen Titel.",
    "ev_f_kind": "Art",
    "ev_ask_creator": "ℹ️ Das ist dein Event - der Button ist für die anderen Mitglieder (Discord zeigt allen "
                      "dieselben Buttons). Du kannst es über „Bearbeiten“ und „Absagen“ verwalten.",
    "ev_created": "✅ Event angelegt: {link}",
    "ev_saved": "✅ Änderungen gespeichert.",
    "ev_skipped": "ℹ️ Nicht eingeladen (keine GFK-Mitglieder): {users}",
    "ev_no_discord_event": "⚠️ Das Discord-Event ließ sich nicht anlegen (Recht „Events erstellen“ fehlt?) - die "
                           "Karte gibt es trotzdem.",
    "ev_no_thread": "⚠️ Der Thread ließ sich nicht anlegen.",
    "ev_location_pending": "Sprachkanal folgt 1 Stunde vor Beginn",
    "ev_everyone": "@everyone 📅 Neues Allianz-Event: **{title}** ({when})",
    "ev_discord_desc": "Absprache und Anmeldung im Thread: {thread}\n{url}",
    "ev_private": "Privat", "ev_cancelled": "Abgesagt", "ev_ended": "Beendet",
    "ev_f_when": "Wann", "ev_f_duration": "Dauer", "ev_f_creator": "Geplant von",
    "ev_f_going": "Dabei ({n})", "ev_f_maybe": "Vielleicht ({n})", "ev_f_voice": "Sprachkanal",
    "ev_voice_later": "kommt 1 Stunde vor Beginn", "ev_f_thread": "Absprache", "ev_footer": "Event #{id}",
    "ev_intro_alliance": "📅 Absprache zum Event von {creator} ({when}). Anmelden über die Buttons an der Karte: {card}",
    "ev_intro_private": "🔒 {creator} hat euch zu einem privaten Event eingeladen ({when}). Die Karte: {card}",
    "ev_closed": "ℹ️ Dieses Event ist vorbei oder abgesagt.",
    "ev_join_done": "✅ Du bist dabei.", "ev_maybe_done": "❔ Als „vielleicht“ eingetragen.",
    "ev_leave_done": "🚪 Abgemeldet.",
    "ev_manage_denied_alliance": "🔒 Bearbeiten und absagen dürfen nur der Ersteller und die Führung.",
    "ev_manage_denied_private": "🔒 Ein privates Event kann nur der Ersteller bearbeiten oder absagen.",
    "ev_cancel_confirm": "Event wirklich absagen? Alle Teilnehmer werden benachrichtigt.",
    "ev_cancel_done": "🗑️ Event abgesagt.",
    "ev_cancelled_note": "❌ {user} hat das Event abgesagt.",
    "ev_changed": "🛠️ {user} hat das Event geändert - Beginn: {when}",
    "ev_ask_already_in": "ℹ️ Du bist schon dabei - schau in den Thread.",
    "ev_ask_pending": "ℹ️ Deine Anfrage läuft schon.",
    "ev_ask_sent": "✅ Anfrage geschickt. Wirst du angenommen, landest du automatisch im Thread.",
    "ev_ask_msg": "🙋 {creator}: {user} möchte mitmachen.",
    "ev_request_denied": "🔒 Annehmen oder ablehnen kann nur der Ersteller.",
    "ev_request_accepted": "✅ {user} ist dabei (angenommen von {creator}).",
    "ev_request_declined": "❌ Anfrage von {user} abgelehnt.",
    "ev_request_declined_dm": "Deine Anfrage für das private Event von {creator} wurde leider abgelehnt: {card}",
    "ev_voice_ready": "🔊 Der Sprachkanal ist da: {voice}",
    "ev_no_voice": "kein Sprachkanal",
    "ev_remind_msg": "⏰ Erinnerung: Das Event beginnt {when} - Sprachkanal: {voice}",
    "ev_start_msg": "🚀 Es geht los! Sprachkanal: {voice}",
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
    "setup_forum_tags": "Im Vorfallforum fehlen die Tags: {items} - `/setup panels` legt sie an, wenn der Bot dort "
                        "„Kanäle verwalten“ hat; sonst bitte von Hand anlegen.",
    "setup_not_forum": "Das Vorfallforum ist kein Forum-Kanal.",
    "setup_lead_mention": "Die Rolle {role} ist nicht erwähnbar und der Bot darf nicht alle Rollen erwähnen - bei "
                          "neuen Meldungen käme kein Ping. Rolle erwähnbar machen oder dem Bot das Recht geben.",
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
    "name_change_sync": "✏️ {user} heißt im Spiel jetzt **{new}** (vorher **{old}**) - automatisch erkannt über "
                        "stfc.pro, Nickname angepasst.",
    "name_change_self": "✏️ {user} heißt im Spiel jetzt **{new}** (vorher **{old}**) - selbst über „Namen ändern“ "
                        "eingetragen.",
    "sync_left": "👋 {user} ({name}) steht laut stfc.pro nicht mehr in der GFK-Liste.",
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
                      "**5. Kürzel entfernt**\nNimmt jemand `[GFK]` aus dem Nickname, wird er automatisch **Gast** "
                      "und hier erscheint eine Karte.\n\n"
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
}


def t(key: str, **kw) -> str:
    text = T[key]
    return text.format(**kw) if kw else text

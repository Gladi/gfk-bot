# GFK-Bot – Design-Dokument

Zweiter Discord-Bot neben YATB, für die private Community eines Spiels. Ziel: Verwaltung vereinfachen.
Der Bot ist nur allianzintern nutzbar (Mitglied, Führung, Admiral). Einzige Ausnahme ist die Eingangskontrolle für Neulinge. Umsetzung mit Claude Code in VS Code (Remote-SSH auf dem Oracle-Server).

## 1. Rahmen und Technik

- Sprache: Python 3.12, discord.py 2.x (Buttons, Selects, Modals, Scheduled Events)
- Betrieb: eigener Docker-Container `gfk-bot` in der bestehenden docker-compose.yml unter `/home/ubuntu/discord-bot/`, eigenes Git-Repo (getrennt von `bot/`)
- Persistenz: SQLite in `data/gfk/` (Events, Anmeldungen, Meldungen, Konfiguration)
- Konfiguration: Bot-Token in der zentralen `.env` (`GFK_DISCORD_TOKEN`); Kanal- und Rollen-IDs per Admin-Slash-Command `/setup` in der Datenbank
- Persistente Views: alle Buttons mit festen `custom_id`, damit sie nach einem Neustart weiter funktionieren
- Texte: Deutsch
- Intents: Guilds, Members (privilegiert, für Teilnehmerauswahl und Umbenennung)
- Bot-Rechte: Rollen verwalten, Nicknames verwalten, Events verwalten, Threads/Forenbeiträge erstellen und verwalten, Nachrichten senden, Dateien anhängen,
  Kanäle verwalten (nur auf der Event-Kategorie, für die Event-Sprachkanäle)
- Rollen-Hierarchie (von oben): Owner → Bots → Admiral → Führung → Mitglied → Freund → Gast → Neuling.
  Die Bot-Rolle steht über allen Rollen, die sie vergibt.

## 2. Konfiguration (/setup, nur Server-Admins)

- Admiral-Rolle und Führungsrolle
- Status-Rollen: „Neuling“ (isoliert, beim Beitritt), „Gast“ (nach der Namensänderung), „Freund“, „Mitglied“ und
  „Führung“ (vergibt die Führung, siehe Abschnitt 3)
- Kanäle: Meldungskanal, Vorfallforum, Eingangskanal, Eventkanal (nur allianzintern sichtbar), Event-Kategorie für die Sprachkanäle
- Diplomaten-Rolle (wird bei neuen Meldungen erwähnt)
- Erinnerungsvorlauf für Events (Standard 30 Minuten)
- `/setup panels` postet die Button-Nachrichten in die Kanäle neu

## 3. Modul Rollenverwaltung

Ziel: Die Führung vergibt den Status, ohne selbst das Recht „Rollen verwalten“ zu haben.

- Status-Rollen schließen sich gegenseitig aus: Gast, Freund, Mitglied, Führung (jede Person hat genau eine davon)
- Nach der Namensänderung ist jeder zunächst **Gast** (siehe Abschnitt 5).
- Wer darf was (entschieden 2026-10-22):
  - **Führung:** setzt Gast, Freund, Mitglied
  - **Admiral:** zusätzlich zur Führung befördern und von der Führung degradieren
  - Niemand kann über den Bot Admiral, Admin- oder andere Rollen vergeben
- Bedienung ohne Slash-Befehle (die Nutzer sind nicht Discord-affin):
  - **Kontextmenü:** Rechtsklick (Handy: lange tippen) auf eine Person → „Apps“ → **„Status ändern“** → Buttons
    nur mit den Status, die der Aufrufer vergeben darf
  - Buttons direkt in der Benachrichtigung über neue Gäste
  - `/status @person` zusätzlich für Geübte
  - Die Admins können das Kontextmenü unter Servereinstellungen → Integrationen auf Admiral und Führung beschränken;
    der Bot prüft die Berechtigung in jedem Fall selbst
- Prüfung: Aufrufer hat die nötige Rolle, nur die Status-Rollen sind vergebbar, niemand kann sich selbst ändern
- Der Bot entfernt die bisherige Status-Rolle und setzt die neue
- Die Bot-Rolle muss in der Hierarchie über allen vergebbaren Rollen stehen
- Log: jede Änderung als kurze Nachricht in einen optionalen Log-Kanal (wer, wem, alt → neu)

## 4. Modul Meldungen (ROE und Vorfälle)

### Ablauf

1. Im Meldungskanal steht eine feste Nachricht „Vorfall melden“ mit Button „Meldung erstellen“.
   Nutzbar nur allianzintern (Mitglied, Führung, Admiral); andere erhalten eine ephemere Ablehnung.
   Gäste und Freunde melden ohne Bot, von Hand in ihrem eigenen Forum (vom Bot nicht verwaltet).
2. Klick öffnet ein Modal mit:
   - Kategorie (Select im Modal): ROE-Verstoß, Null-Node-Meldung, Sonstiges
   - Allianz (optional, leer = keine Allianz)
   - Spielername (Pflicht)
   - Beschreibung (Paragraph, Pflicht)
   - Screenshots (Datei-Upload-Komponente im Modal, bis 5 Bilder)
3. Fallback, falls Select oder Upload im Modal nicht verfügbar sind: zuerst ephemeres Kategorie-Select, dann Modal, danach fordert der Bot ephemer auf, Bilder innerhalb von 5 Minuten als Antwort hochzuladen, oder Bilder werden direkt in den Forenbeitrag gepostet.
4. Der Bot erstellt einen Beitrag im Vorfallforum:
   - Titel: `[Kategorie] Allianz – Spieler – TT.MM.JJJJ` (ohne Allianz: `[Kategorie] Spieler – Datum`)
   - Startnachricht: Embed mit Melder, Kategorie, Allianz, Spieler, Datum, Beschreibung; Screenshots als Anhänge
   - Button „Erledigt“ unter der Startnachricht
   - Forum-Tags: Kategorie und Status (Offen/Erledigt)
   - Erwähnung der Diplomaten-Rolle
5. Führung und Mitglieder können im Beitrag antworten.
6. „Erledigt“: nur Führungsrolle; setzt Tag „Erledigt“, vermerkt wer und wann, deaktiviert den Button, archiviert den Beitrag (optional sperren). Andere erhalten eine ephemere Ablehnung.

## 5. Modul Eingangskontrolle

1. Neue Nutzer erhalten automatisch die Rolle „Neuling“ und sehen nur den Eingangskanal.
2. Dort steht eine feste Nachricht mit Button „Namen ändern“.
3. Modal: Allianz und In-Game-Name (beide Pflicht).
4. Bot setzt den Server-Nickname im Format `[Allianz] Name` (maximal 32 Zeichen, sonst kürzen und Hinweis).
5. Nach der Umbenennung entfernt der Bot „Neuling“ und gibt automatisch „Gast“.
6. Die Führung erhält eine Benachrichtigung (Führungs- oder Log-Kanal) mit Buttons „Freund“, „Mitglied“, „Führung“;
   alternativ später per `/status`.
7. Hinweis: Den Nickname des Server-Eigentümers und von Personen mit Rollen über der Bot-Rolle kann der Bot nicht ändern.

## 6. Modul Eventplanung

### Einstieg

Im Eventkanal (nur allianzintern sichtbar) steht eine feste Nachricht mit Button „Neues Event planen“, nutzbar nur für
Mitglied, Führung und Admiral (Gäste und Freunde nicht). Danach ephemer die Wahl: allianzweit oder privat.

### Sprachkanal je Event

- Der Bot legt **1 Stunde vor Beginn** einen Sprachkanal in der Event-Kategorie an (Name z. B. `🔊 Armada 24.10. 20:00`)
  und postet den Link in die Event-Karte bzw. den privaten Thread
- Allianzweit: Kanal sichtbar für Mitglied, Führung, Admiral. Privat: nur für die ausgewählten Teilnehmer
- Gelöscht wird er, **wenn das Event zu Ende ist und niemand mehr im Kanal ist** (Prüfung im Minuten-Task bzw. beim
  Verlassen des Kanals); bei Absage sofort
- Discord-Event (allianzweit): bei der Planung als Ort „extern“ angelegt, 1 Stunde vorher auf den neuen Sprachkanal
  umgestellt (Discord erlaubt das Ändern des Orts) - **auf dem Test-Server prüfen**
- Privates Event: kein Discord-Event bei der Planung (ein externes Event wäre für alle sichtbar); ob 1 Stunde vorher
  ein Event im privaten Sprachkanal nur für die Teilnehmer sichtbar ist, auf dem Test-Server prüfen

### Formular (beide Arten)

- Kategorie: Armadas, Welle, Ansturm, Sonstiges
- Datum und Uhrzeit: Discord hat keinen Datumspicker im Modal; Eingabe als Textfeld im Format `TT.MM.JJJJ HH:MM`, Zeitzone Europe/Berlin, Validierung (muss in der Zukunft liegen). Alternative: Selects für Tag (nächste 14 Tage) und Uhrzeit (Viertelstunden).
- Beschreibung (kurz)
- Optional: Dauer (Standard 1 Stunde), da Discord-Events eine Endzeit brauchen

### Allianzweites Event

- Bot legt ein Discord Scheduled Event im Event-Sprachkanal an
- Bot postet eine Event-Karte (Embed) im Eventkanal: Kategorie, Zeit als Discord-Timestamp, Beschreibung, Ersteller, Teilnehmerliste
- Buttons: „Anmelden“, „Abmelden“, optional „Vielleicht“
- Teilnehmer werden in SQLite gespeichert, die Karte wird bei jeder Änderung aktualisiert
- Ersteller und Führung können über einen Button „Absagen“ das Event löschen (Discord-Event wird mitgelöscht)

### Privates Event

- Zusätzlich User-Select (bis 25 Mitglieder) zur Auswahl der Teilnehmer
- Siehe „Sprachkanal je Event“: kein öffentliches Discord-Event; privater Sprachkanal 1 Stunde vorher
- Event-Karte im privaten Thread, in den der Bot die gewählten Teilnehmer einlädt (zusagen/absagen)

### Erinnerungen

- Hintergrund-Task (`discord.ext.tasks`, jede Minute) prüft anstehende Events
- Zum konfigurierten Vorlauf pingt der Bot alle angemeldeten bzw. ausgewählten Teilnehmer (allianzweit im Eventkanal, privat im Thread)
- Optional zweite Erinnerung zum Start
- Erinnerungsstatus in SQLite, damit nach einem Neustart nichts doppelt oder gar nicht gesendet wird

## 7. Datenmodell (SQLite)

- `config(guild_id, key, value)`
- `reports(id, guild_id, thread_id, reporter_id, category, alliance, player, description, created_at, status, closed_by, closed_at)`
- `events(id, guild_id, type, category, start_at, end_at, description, creator_id, message_id, thread_id, discord_event_id, status, reminded)`
- `event_participants(event_id, user_id, state)`
- `role_log(id, guild_id, actor_id, target_id, old_role, new_role, at)`

## 8. Projektstruktur

- `gfk/main.py` – Start, Laden der Cogs, Registrierung persistenter Views
- `gfk/db.py` – SQLite-Zugriff
- `gfk/cogs/setup.py`, `roles.py`, `reports.py`, `onboarding.py`, `events.py`
- `gfk/views/` – Buttons, Selects, Modals
- `Dockerfile`, `requirements.txt`, `README.md`

## 9. Umsetzungsreihenfolge (Pakete)

1. Grundgerüst: Container, Token, DB, `/setup`, persistente Views
2. Eingangskontrolle
3. Rollenverwaltung
4. Meldungen mit Forum und „Erledigt“
5. Allianzweite Events mit Anmeldung
6. Private Events
7. Erinnerungen
8. Feinschliff: Logs, Fehlertexte, Tests auf einem Testserver

## 10. Offene Entscheidungen

- ~~Eingangskontrolle~~ entschieden (2026-10-22): nach der Namensänderung automatisch Gast; Führung macht zu Freund oder Mitglied, der Admiral auch zur Führung
- ~~Führung ernennen~~ entschieden: nur der Admiral
- ~~Events~~ entschieden: nur Mitglied, Führung, Admiral
- ~~Meldungen durch Gäste/Freunde~~ entschieden: nicht über den Bot, sie melden von Hand in ihrem eigenen Forum
- Private Events: Vorschlag privater Thread + privater Sprachkanal 1 Stunde vorher, kein öffentliches Discord-Event (Sichtbarkeit auf dem Test-Server prüfen)
- ~~Rollenverwaltung~~ entschieden: freie Auswahl unter den Status-Rollen
- Wer darf Events absagen oder bearbeiten? (Vorschlag: Ersteller, Führung, Admiral)
- ~~Event-Sprachkanal~~ entschieden: 1 Stunde vorher anlegen, löschen wenn Event vorbei und Kanal leer
- Nickname-Format für die Eingangskontrolle (Vorschlag: `[ALLY] Name`, bei mehr als 32 Zeichen wird der Name gekürzt)

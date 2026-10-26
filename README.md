# GFK-Bot

*A Discord bot for the German Star Trek Fleet Command alliance GFK: onboarding with roster check against
stfc.pro, status roles without "Manage Roles" for officers, incident reports with a forum workflow and statistics,
event planning with voice channels and reminders, and server logs. German UI. Licensed under AGPL-3.0.*

Discord-Bot für die GFK-Allianz in Star Trek Fleet Command. Er ist auf einen Server zugeschnitten (Texte Deutsch,
Allianz GFK), alle Rollen und Kanäle werden aber per `/setup` eingestellt. Entscheidungen und Abläufe im Detail:
[GFK-Bot_Design.md](GFK-Bot_Design.md).

## Funktionen

- **Eingangskontrolle:** Button „Namen ändern“ → Nickname `[ALLY] Spielname`. Bei GFK wird der Name mit der
  Mitgliederliste auf [stfc.pro](https://stfc.pro) abgeglichen und die Spieler-ID gemerkt; spätere Namensänderungen
  im Spiel zieht der Bot täglich nach. Neue Leute werden Gast, die Führung bekommt eine Karte mit Buttons.
- **Status-Rollen:** Gast, Freund, Mitglied, Führung - vergeben über Buttons, Kontextmenü „Status ändern“ oder
  `/status`, ohne dass die Führung selbst „Rollen verwalten“ braucht. Mitglied/Führung nur mit geprüftem Kürzel.
- **Meldungen:** Formular mit Kategorie, Allianz, Spieler, Beschreibung und Screenshots → Beitrag im Vorfallforum,
  „In Bearbeitung“ / „Erledigt“ für die Führung, automatisches Aufräumen, Statistik je Allianz im Logbuch.
- **Events:** allianzweit (mit Discord-Event und Anmeldung) oder privat (eingeladene Teilnehmer, privater Thread),
  Sprachkanal 1 Stunde vorher, Erinnerung, Aufräumen nach dem Ende.
- **Server-Logs:** Beitritte/Austritte, Rollen-, Nickname-, Kanal- und Rollenänderungen, bearbeitete und gelöschte
  Nachrichten (alter Text nur im Arbeitsspeicher).

## Einrichten

1. Discord-Anwendung anlegen, unter *Bot* die Intents **Server Members** und **Message Content** einschalten (Message
   Content nur für den msg-log; ohne ihn startet der Bot trotzdem).
2. Bot einladen. Rechte: Kanäle sehen, Nachrichten senden, Links einbetten, Dateien anhängen, Verlauf lesen, Alle
   erwähnen, Nicknames verwalten, Rollen verwalten, Events erstellen und verwalten, öffentliche und private Threads
   erstellen, Threads verwalten, in Threads schreiben, Audit-Log anzeigen, Verbinden, Sprechen. **Kanäle verwalten**
   nur auf der Event-Kategorie (und am Vorfallforum, falls der Bot Tags anlegen soll). Die Bot-Rolle muss über den
   Status-Rollen stehen.
3. Starten (Docker):
   ```
   docker build -t gfk-bot .
   docker run -d --name gfk-bot -e DISCORD_TOKEN=... -e GFK_GUILD=<Server-ID> -v $PWD/data:/app/data gfk-bot
   ```
   `GFK_GUILD` meldet die Befehle sofort auf diesem Server an (sonst global, das kann bis zu einer Stunde dauern).
   `GFK_DB_FILE` ändert den Ort der SQLite-Datenbank (Standard `/app/data/gfk.db`).
4. Auf dem Server als Admin: `/setup rollen`, `/setup kanäle`, `/setup logs`, dann `/setup anzeigen` (zeigt fehlende
   Einstellungen und Rechte) und `/setup panels` (postet die festen Nachrichten mit Buttons). Bestehende Mitglieder
   mit `[GFK]` im Nickname einmalig mit `/setup abgleich` verknüpfen.

Für eine andere Allianz: `ALLIANCE_ID` und `ALLIANCE_TAG` in `gfk/stfc.py` anpassen. stfc.pro wird höflich genutzt:
nur die normale Allianzseite, höchstens alle 15 Minuten, eigener User-Agent; die letzte Liste wird gespeichert.

## Entwicklung

- Unit-Tests (ohne Netz): `docker run --rm --network none -v $PWD:/src:ro -w /src gfk-bot python -m unittest
  discover -s tests`
- Test-Server (nur mit `GFK_DEV_GUILD`, nie auf dem echten Server): `python -m gfk.devtools seed|panels|status`
  richtet Kanäle und Rollen ein; `python -m gfk.devtools selftest` spielt Meldung und Events gegen Discord durch
  (laufenden Bot vorher stoppen).

| Pfad | Inhalt |
|---|---|
| `gfk/main.py` | Start, Lebenszeichen (Docker-Healthcheck), Fehlerbehandlung, Anmeldung der Befehle |
| `gfk/db.py` | SQLite |
| `gfk/settings.py` | Rollen/Kanäle, die der Bot kennen muss, und Prüfungen |
| `gfk/cogs/setup.py` | `/setup`, feste Nachrichten, Info für die Führung |
| `gfk/cogs/onboarding.py`, `roles.py` | Eingangskontrolle, Status-Rollen, Abgleich mit stfc.pro |
| `gfk/cogs/reports.py`, `gfk/reportstats.py` | Meldungen, Aufräumen, Statistik |
| `gfk/cogs/events.py`, `gfk/eventlogic.py` | Eventplanung; Zeit-Eingaben und Fälligkeiten ohne Discord |
| `gfk/cogs/logs.py`, `gfk/logfmt.py` | Server-Logs |
| `gfk/stfc.py`, `gfk/names.py` | stfc.pro-Liste, Nicknames und Status-Regeln |
| `gfk/texts.py` | alle Texte (Deutsch) |
| `gfk/devtools.py` | Werkzeuge nur für den Test-Server |

## Lizenz

[GNU Affero General Public License v3.0](LICENSE). Wer den Bot verändert und für andere betreibt, muss den
geänderten Quellcode den Nutzern zugänglich machen.

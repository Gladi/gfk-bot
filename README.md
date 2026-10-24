# GFK-Bot (privat)

Discord-Bot für die GFK-Allianz in Star Trek Fleet Command: Eingangskontrolle, Status-Rollen, Vorfallmeldungen und
Eventplanung. Nur allianzintern. Umfang und Entscheidungen: [GFK-Bot_Design.md](GFK-Bot_Design.md).

## Stand

Paket 1 (Grundgerüst): Container, SQLite, `/setup` (Rollen, Kanäle, Erinnerung, Anzeige mit Prüfung, feste
Nachrichten), Buttons mit fester `custom_id`, die Neustarts überleben. Die Funktionen hinter den Buttons folgen in
den nächsten Paketen.

Paket 2/3: Eingangskontrolle mit stfc.pro-Abgleich, Status-Rollen (Kontextmenü „Status ändern“, `/status`).

Server-Logs (ersetzen SCNX): user-, rollen-, kanal-, msg-log, je Kanal über `/setup logs`, abschalten mit
`/setup log_aus`. Der msg-log merkt sich Nachrichten nur im Arbeitsspeicher (Standard 7 Tage, `msg_tage` 1–30).

## Aufbau

| Pfad | Inhalt |
|---|---|
| `gfk/main.py` | Start, Lebenszeichen (Docker-Healthcheck), Fehlerbehandlung, Anmeldung der Befehle |
| `gfk/db.py` | SQLite (`/app/data/gfk.db`), Tabellen laut Design |
| `gfk/settings.py` | Rollen/Kanäle, die der Bot kennen muss, und Prüfungen (Hierarchie, Reihenfolge) |
| `gfk/cogs/setup.py` | `/setup` |
| `gfk/cogs/onboarding.py`, `roles.py` | Eingangskontrolle, Status-Rollen |
| `gfk/cogs/logs.py`, `gfk/logfmt.py` | Server-Logs, Vergleiche und Nachrichten-Zwischenspeicher |
| `gfk/views/panels.py` | feste Nachrichten mit Buttons |
| `gfk/devtools.py` | nur Test-Server: Kanäle zuordnen, Rollen anlegen, Prüfung, Panels posten |
| `gfk/texts.py` | Texte (Deutsch) |

## Betrieb (auf dem Oracle-Server, Ordner `~/discord-bot`)

- Test-Bot: `docker compose --profile test up -d --build gfk-bot-test` (Token in `.env.gfk-test`, DB `data/gfk-test/`,
  Befehle sofort auf dem Test-Server über `GFK_DEV_GUILD`)
- Test-Server einrichten: `docker compose --profile test run --rm gfk-bot-test python -m gfk.devtools seed|panels|status`
- Unit-Tests: `docker run --rm --network none -v $PWD/gfk-bot:/src:ro -w /src <image> python -m unittest discover -s tests`
- Der Live-Dienst `gfk-bot` (`.env.gfk`, `data/gfk/`) kommt zum Live-Gang dazu.

## Rechte des Bots

Kanäle sehen, Nachrichten senden, Links einbetten, Dateien anhängen, Nachrichtenverlauf lesen, Nicknames verwalten,
Rollen verwalten, Events erstellen und verwalten, öffentliche und private Threads erstellen, Threads verwalten, in
Threads schreiben, Audit-Log anzeigen (wer etwas geändert hat). **Kanäle verwalten nur auf der Event-Kategorie.**
Die Log-Kanäle muss der Bot sehen und beschreiben können. Intents: Server Members, Message Content (nur für den
msg-log; ist er im Developer Portal aus, startet der Bot ohne ihn und `/setup anzeigen` weist darauf hin). Die
Bot-Rolle muss über Führung, Mitglied, Freund und Gast stehen.

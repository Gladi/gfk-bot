"""GFK-Bot - baut auf botcore auf (Unterordner bot-core, Git-Submodul): Meldungen, Events und /setup-Grundlage kommen
von dort, Eingangskontrolle, Status-Rollen und Server-Logs sind GFK-eigen."""
import botcore

# Präfix "gfk" und Datenbank gfk.db: so stehen sie seit dem Live-Gang - nie ändern (Buttons alter Nachrichten)
botcore.configure(name="GFK-Bot", tag="GFK", prefix="gfk", db_file=botcore.default_db_file("GFK_DB_FILE", "gfk.db"))

# Vor dem ersten db.init(): GFK-Tabellen anmelden, Rollen/Kanäle und Texte eintragen
from gfk import db, settings, texts  # noqa: E402,F401
from gfk.views import panels  # noqa: E402,F401

"""
GFK-Bot - Start (Grundlage: botcore.runner).

    python -m gfk.main

Umgebung: DISCORD_TOKEN (Pflicht), GFK_GUILD (Live) bzw. GFK_DEV_GUILD (Test-Server; nur damit läuft auch
gfk.devtools) - optional: Server-ID, auf dem die Befehle sofort erscheinen; ohne werden sie global angemeldet, das
kann bis zu einer Stunde dauern. GFK_DB_FILE (optional).
"""
import gfk  # noqa: F401  (botcore.configure)
from botcore import runner

HEARTBEAT_FILE = "/tmp/gfk_heartbeat"     # Docker-Healthcheck prüft das Alter dieser Datei
COGS = ["gfk.cogs.setup", "gfk.cogs.onboarding", "gfk.cogs.roles", "gfk.cogs.logs", "botcore.cogs.reports",
        "botcore.cogs.events"]


def main():
    # Message Content nur für den msg-log (alter Text bei Bearbeitung/Löschung); ohne ihn startet der Bot trotzdem
    runner.run(COGS, ("GFK_GUILD", "GFK_DEV_GUILD"), HEARTBEAT_FILE, ".env.gfk bzw. .env.gfk-test",
               message_content=True)


if __name__ == "__main__":
    main()

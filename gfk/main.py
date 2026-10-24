"""
GFK-Bot - Start.

    python -m gfk.main

Umgebung: DISCORD_TOKEN (Pflicht), GFK_DEV_GUILD (optional: Server-ID, auf dem die Befehle sofort erscheinen -
für den Test-Bot; ohne die Variable werden sie global angemeldet, das kann bis zu einer Stunde dauern),
GFK_DB_FILE (optional).
"""
import logging
import math
import os
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from gfk import db
from gfk.texts import t
from gfk.views.panels import PanelButton

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("gfk")

HEARTBEAT_FILE = "/tmp/gfk_heartbeat"     # Docker-Healthcheck prüft das Alter dieser Datei
WATCHDOG_SECONDS = 600                     # so lange ohne Discord-Verbindung -> Prozess beenden, Docker startet neu
COGS = ["gfk.cogs.setup"]


class GfkBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True              # Rollen, Nicknames, Teilnehmer-Auswahl
        super().__init__(command_prefix=commands.when_mentioned, intents=intents,
                         allowed_mentions=discord.AllowedMentions.none())
        self._last_connected = time.monotonic()

    async def setup_hook(self):
        db.init()
        self.add_dynamic_items(PanelButton)   # Buttons der festen Nachrichten, auch nach einem Neustart
        for cog in COGS:
            await self.load_extension(cog)
        self.tree.on_error = on_app_command_error
        dev_guild = os.environ.get("GFK_DEV_GUILD", "").strip()
        if dev_guild:
            guild = discord.Object(int(dev_guild))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("%d Befehle auf dem Test-Server %s angemeldet.", len(synced), dev_guild)
        else:
            synced = await self.tree.sync()
            log.info("%d Befehle global angemeldet.", len(synced))
        self.heartbeat.start()

    async def close(self):
        self.heartbeat.cancel()
        await super().close()

    async def on_ready(self):
        log.info("GFK-Bot online als %s auf %d Server(n) - bereit.", self.user, len(self.guilds))

    @tasks.loop(seconds=30)
    async def heartbeat(self):
        """Lebenszeichen, solange der Bot verbunden ist; Watchdog bei dauerhaftem Verbindungsverlust."""
        if self.is_ready() and not self.is_closed() and math.isfinite(self.latency):
            self._last_connected = time.monotonic()
            try:
                with open(HEARTBEAT_FILE, "w") as fh:
                    fh.write(str(int(time.time())))
            except OSError as exc:
                log.warning("Heartbeat-Datei nicht schreibbar: %s", type(exc).__name__)
        elif time.monotonic() - self._last_connected > WATCHDOG_SECONDS:
            log.error("Seit %d s keine Verbindung zu Discord - Neustart über Docker.", WATCHDOG_SECONDS)
            os._exit(1)


async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        return                                  # Ablehnung wurde schon beantwortet (interaction_check)
    log.exception("Fehler in /%s", interaction.command.qualified_name if interaction.command else "?",
                  exc_info=error)
    try:
        if interaction.response.is_done():
            await interaction.followup.send(t("error"), ephemeral=True)
        else:
            await interaction.response.send_message(t("error"), ephemeral=True)
    except discord.HTTPException:
        pass


def main():
    token = os.environ.get("DISCORD_TOKEN", "").strip()
    if not token:
        raise SystemExit("DISCORD_TOKEN fehlt (.env.gfk bzw. .env.gfk-test)")
    GfkBot().run(token, log_handler=None)


if __name__ == "__main__":
    main()

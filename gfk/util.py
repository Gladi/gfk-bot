"""GFK-Bot - gemeinsame Hilfen für Buttons und Formulare: Fehler freundlich melden statt "Interaktion fehlgeschlagen"."""
import functools
import logging

import discord

from gfk.texts import t

log = logging.getLogger("gfk")


async def send_error(interaction: discord.Interaction):
    try:
        if interaction.response.is_done():
            await interaction.followup.send(t("error"), ephemeral=True)
        else:
            await interaction.response.send_message(t("error"), ephemeral=True)
    except discord.HTTPException:
        pass


def guarded(fn):
    """Für callback(self, interaction, ...) von Buttons (auch DynamicItem): Fehler loggen und dem Nutzer melden."""
    @functools.wraps(fn)
    async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
        try:
            return await fn(self, interaction, *args, **kwargs)
        except Exception:
            log.exception("Fehler bei %s", getattr(interaction, "data", {}).get("custom_id", fn.__qualname__))
            await send_error(interaction)
    return wrapper


class SafeView(discord.ui.View):
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        log.exception("Fehler bei %s", getattr(item, "custom_id", item), exc_info=error)
        await send_error(interaction)

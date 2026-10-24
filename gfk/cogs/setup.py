"""
GFK-Bot - /setup (nur Server-Admins): Rollen, Kanäle, Erinnerung, Anzeige mit Prüfung, feste Nachrichten.

Die Prüfung (status_lines) wird auch vom Test-Werkzeug gfk.devtools genutzt.
"""
import logging
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from gfk import db, settings as st
from gfk.texts import t
from gfk.views.panels import PANELS, panel_message

log = logging.getLogger("gfk.setup")

# Benötigte Rechte je Kanal (Schlüssel aus settings.CHANNEL_KEYS) und auf dem Server
CHANNEL_PERMS = {
    "eingang": ["view_channel", "send_messages", "embed_links"],
    "meldungen": ["view_channel", "send_messages", "embed_links"],
    "vorfallforum": ["view_channel", "send_messages", "embed_links", "attach_files", "manage_threads"],
    "events": ["view_channel", "send_messages", "embed_links", "create_public_threads", "create_private_threads",
               "send_messages_in_threads", "manage_threads"],
    "event_kategorie": ["view_channel", "manage_channels"],
    "log": ["view_channel", "send_messages", "embed_links"],
}
GUILD_PERMS = ["manage_roles", "manage_nicknames", "manage_events", "create_events"]


def _role(guild: discord.Guild, config: Dict[str, str], key: str) -> Optional[discord.Role]:
    value = config.get(st.role_key(key))
    return guild.get_role(int(value)) if value else None


def _channel(guild: discord.Guild, config: Dict[str, str], key: str):
    value = config.get(st.channel_key(key))
    return guild.get_channel(int(value)) if value else None


def status_lines(guild: discord.Guild, config: Dict[str, str]) -> List[str]:
    """Probleme der aktuellen Einrichtung als Textzeilen (leer = alles in Ordnung)."""
    lines = []
    miss = st.missing(config)
    if miss:
        lines.append(t("setup_missing", items=", ".join(miss)))
    me = guild.me
    roles = {k: _role(guild, config, k) for k in st.ROLE_KEYS}
    bad = st.unmanageable(me.top_role.position,
                          [st.RoleInfo(k, r.name, r.position) for k, r in roles.items() if r and k in st.MANAGED_ROLES])
    if bad:
        lines.append(t("setup_hierarchy", items=", ".join(bad)))
    order = st.order_problems({k: (r.position if r else None) for k, r in roles.items()})
    if order:
        lines.append(t("setup_order", items="; ".join(order)))
    perms = []
    gp = me.guild_permissions
    perms += [f"Server: {p}" for p in GUILD_PERMS if not getattr(gp, p, False)]
    for key, needed in CHANNEL_PERMS.items():
        ch = _channel(guild, config, key)
        if ch is None:
            continue
        cp = ch.permissions_for(me)
        perms += [f"{st.CHANNEL_KEYS[key]}: {p}" for p in needed if not getattr(cp, p, False)]
    if perms:
        lines.append(t("setup_perm", items=", ".join(perms)))
    return lines


async def send_log(guild: discord.Guild, text: str):
    """Nachricht in den Log-Kanal (falls eingerichtet); nie mit Pings."""
    config = await db.get_config(guild.id)
    ch = _channel(guild, config, "log")
    if ch is None:
        return
    try:
        await ch.send(text, allowed_mentions=discord.AllowedMentions.none())
    except discord.HTTPException as exc:
        log.warning("Log-Kanal nicht beschreibbar (%s): %s", guild.id, exc)


@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
class SetupCog(commands.GroupCog, group_name="setup", group_description="GFK-Bot einrichten (nur Admins)"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None or not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(t("admin_only"), ephemeral=True)
            return False
        return True

    async def _save(self, interaction: discord.Interaction, values: Dict[str, Optional[str]], labels: List[str]):
        if not values:
            await interaction.response.send_message(t("setup_nothing"), ephemeral=True)
            return
        await db.set_config(interaction.guild_id, values)
        items = ", ".join(labels)
        await interaction.response.send_message(t("setup_saved", items=items), ephemeral=True)
        await send_log(interaction.guild, t("log_setup", user=interaction.user.mention, items=items))

    @app_commands.command(name="rollen", description="Status-Rollen festlegen")
    @app_commands.rename(fuehrung="führung")
    async def roles(self, interaction: discord.Interaction, admiral: Optional[discord.Role] = None,
                    fuehrung: Optional[discord.Role] = None, mitglied: Optional[discord.Role] = None,
                    freund: Optional[discord.Role] = None, gast: Optional[discord.Role] = None):
        given = {"admiral": admiral, "fuehrung": fuehrung, "mitglied": mitglied, "freund": freund, "gast": gast}
        values = {st.role_key(k): str(r.id) for k, r in given.items() if r is not None}
        labels = [f"{st.ROLE_KEYS[k]} = {r.name}" for k, r in given.items() if r is not None]
        await self._save(interaction, values, labels)

    @app_commands.command(name="kanäle", description="Kanäle des Bots festlegen")
    async def channels(self, interaction: discord.Interaction, eingang: Optional[discord.TextChannel] = None,
                       meldungen: Optional[discord.TextChannel] = None,
                       vorfallforum: Optional[discord.ForumChannel] = None,
                       events: Optional[discord.TextChannel] = None,
                       event_kategorie: Optional[discord.CategoryChannel] = None,
                       log: Optional[discord.TextChannel] = None):
        given = {"eingang": eingang, "meldungen": meldungen, "vorfallforum": vorfallforum, "events": events,
                 "event_kategorie": event_kategorie, "log": log}
        values = {st.channel_key(k): str(c.id) for k, c in given.items() if c is not None}
        labels = [f"{st.CHANNEL_KEYS[k]} = #{c.name}" for k, c in given.items() if c is not None]
        await self._save(interaction, values, labels)

    @app_commands.command(name="erinnerung", description="Wie viele Minuten vor einem Event erinnert wird")
    async def reminder(self, interaction: discord.Interaction,
                       minuten: app_commands.Range[int, st.REMINDER_MIN, st.REMINDER_MAX]):
        await db.set_config(interaction.guild_id, {st.REMINDER_KEY: str(minuten)})
        await interaction.response.send_message(t("setup_reminder", minutes=minuten), ephemeral=True)

    @app_commands.command(name="anzeigen", description="Aktuelle Einstellungen und Prüfung der Rechte")
    async def show(self, interaction: discord.Interaction):
        guild = interaction.guild
        config = await db.get_config(guild.id)
        embed = discord.Embed(title=t("setup_title"), color=discord.Color.blurple())
        embed.add_field(name=t("setup_roles"), inline=False, value="\n".join(
            f"{label}: {r.mention if (r := _role(guild, config, key)) else t('setup_unset')}"
            for key, label in st.ROLE_KEYS.items()))
        embed.add_field(name=t("setup_channels"), inline=False, value="\n".join(
            f"{label}: {c.mention if (c := _channel(guild, config, key)) else t('setup_unset')}"
            for key, label in st.CHANNEL_KEYS.items()))
        embed.add_field(name=t("setup_reminder_field"), inline=False,
                        value=t("setup_reminder_value", minutes=st.reminder_minutes(config)))
        problems = status_lines(guild, config)
        embed.add_field(name=t("setup_checks"), inline=False, value="\n".join(problems) or t("setup_ok"))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="panels", description="Feste Nachrichten (Buttons) posten oder aktualisieren")
    async def panels(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        posted, missing = await post_panels(interaction.guild)
        if missing:
            await interaction.followup.send(t("panels_missing", items=", ".join(missing)), ephemeral=True)
        if posted:
            await interaction.followup.send(t("panels_posted", items=", ".join(posted)), ephemeral=True)


async def post_panels(guild: discord.Guild):
    """Postet die festen Nachrichten oder bearbeitet die vorhandenen (damit sie oben im Kanal bleiben)."""
    config = await db.get_config(guild.id)
    posted, missing, updates = [], [], {}
    for kind, (channel_key, *_rest) in PANELS.items():
        ch = _channel(guild, config, channel_key)
        if ch is None:
            missing.append(st.CHANNEL_KEYS[channel_key])
            continue
        embed, view = panel_message(kind)
        msg_id = config.get(f"panel_{kind}")
        message = None
        if msg_id:
            try:
                message = await ch.fetch_message(int(msg_id))
                await message.edit(embed=embed, view=view)
            except discord.NotFound:
                message = None
        if message is None:
            message = await ch.send(embed=embed, view=view)
            updates[f"panel_{kind}"] = str(message.id)
        posted.append(f"#{ch.name}")
    if updates:
        await db.set_config(guild.id, updates)
    return posted, missing


async def setup(bot: commands.Bot):
    await bot.add_cog(SetupCog(bot))

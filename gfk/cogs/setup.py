"""
GFK-Bot - /setup (nur Server-Admins). Gemeinsames (erinnerung, anzeigen, panels, uninstall, Prüfung) kommt aus
botcore.cogs.setup; hier stehen die GFK-Optionen von rollen und kanäle, die Server-Logs, der stfc.pro-Abgleich und die
angepinnte Erklärung in Verwaltung.

Die Prüfung (status_lines) wird auch vom Test-Werkzeug gfk.devtools genutzt.
"""
import logging
from typing import Dict, Optional

import discord
from discord import app_commands
from discord.ext import commands

from botcore.cogs import setup as core
from botcore.cogs.setup import (_channel, _role, notify_verwaltung, post_panels, status_lines,  # noqa: F401
                                uninstall_guild)
from gfk import db, settings as st
from gfk.texts import t
from gfk.views import panels as panels_mod

log = logging.getLogger("gfk.setup")

LOG_PERMS = ["view_channel", "send_messages", "embed_links"]


def log_checks(guild: discord.Guild, config: Dict[str, str], bot: Optional[commands.Bot]):
    """Server-Logs: Rechte in den Log-Kanälen, Audit-Log, Message Content Intent für den msg-log."""
    perms, lines = [], []
    active = [k for k in st.LOG_KEYS if _channel(guild, config, k) is not None]
    for key in active:
        cp = _channel(guild, config, key).permissions_for(guild.me)
        perms += [f"{st.LOG_KEYS[key]}: {p}" for p in LOG_PERMS if not getattr(cp, p, False)]
    if active and not guild.me.guild_permissions.view_audit_log:
        perms.append("Server: view_audit_log (wer etwas geändert hat)")
    if bot is not None and not bot.intents.message_content and _channel(guild, config, "log_msg") is not None:
        lines.append(t("setup_msg_intent"))
    return lines, perms


def log_field(guild: discord.Guild, config: Dict[str, str]):
    return t("setup_logs"), "\n".join(
        f"{label}: {c.mention if (c := _channel(guild, config, key)) else t('setup_off')}"
        for key, label in st.LOG_KEYS.items()) + "\n" + t("setup_msg_days", days=st.msg_days(config))


core.EXTRA_CHECKS.append(log_checks)
core.EXTRA_FIELDS.append(log_field)


@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
class SetupCog(core.SetupBase, group_name="setup", group_description="GFK-Bot einrichten (nur Admins)"):
    async def cog_load(self):
        panels_mod.AFTER_POST["info"] = lambda guild, _fresh: post_info(guild)

    async def cog_unload(self):
        panels_mod.AFTER_POST.pop("info", None)

    @app_commands.command(name="rollen", description="Status-Rollen festlegen")
    @app_commands.rename(fuehrung="führung")
    async def roles(self, interaction: discord.Interaction, admiral: Optional[discord.Role] = None,
                    fuehrung: Optional[discord.Role] = None, mitglied: Optional[discord.Role] = None,
                    freund: Optional[discord.Role] = None, gast: Optional[discord.Role] = None):
        await self.save_given(interaction, roles={"admiral": admiral, "fuehrung": fuehrung, "mitglied": mitglied,
                                                  "freund": freund, "gast": gast})

    @app_commands.command(name="kanäle", description="Kanäle des Bots festlegen")
    @app_commands.describe(namen_zusatz="Optional: weiterer Kanal mit der Nachricht „Namen ändern“",
                           namensaenderungen="Optional: Thread/Forenbeitrag für geänderte Spielnamen (sonst Verwaltung)",
                           logbuch="Optional: Forum, in dem der Bot den Beitrag „Vorfall Statistik“ führt")
    @app_commands.rename(namensaenderungen="namensänderungen")
    async def channels(self, interaction: discord.Interaction, eingang: Optional[discord.TextChannel] = None,
                       meldungen: Optional[discord.TextChannel] = None,
                       vorfallforum: Optional[discord.ForumChannel] = None,
                       events: Optional[discord.TextChannel] = None,
                       event_kategorie: Optional[discord.CategoryChannel] = None,
                       verwaltung: Optional[discord.TextChannel] = None,
                       namen_zusatz: Optional[discord.TextChannel] = None,
                       namensaenderungen: Optional[discord.Thread] = None,
                       logbuch: Optional[discord.ForumChannel] = None):
        await self.save_given(interaction, channels={
            "eingang": eingang, "meldungen": meldungen, "vorfallforum": vorfallforum, "events": events,
            "event_kategorie": event_kategorie, "verwaltung": verwaltung, "eingang_info": namen_zusatz,
            "namen_log": namensaenderungen, "logbuch": logbuch})

    @app_commands.command(name="logs", description="Kanäle der Server-Logs festlegen (ersetzt SCNX)")
    @app_commands.describe(user="Beitritt, Austritt, Nickname, Rollen, Kick/Bann/Timeout", rollen="Rollen geändert",
                           kanal="Kanäle geändert", msg="Bearbeitete und gelöschte Nachrichten",
                           msg_tage="Wie lange der Bot Nachrichten für den msg-log im Arbeitsspeicher behält")
    async def logs(self, interaction: discord.Interaction, user: Optional[discord.TextChannel] = None,
                   rollen: Optional[discord.TextChannel] = None, kanal: Optional[discord.TextChannel] = None,
                   msg: Optional[discord.TextChannel] = None,
                   msg_tage: Optional[app_commands.Range[int, st.MSG_DAYS_MIN, st.MSG_DAYS_MAX]] = None):
        given = {"log_user": user, "log_rollen": rollen, "log_kanal": kanal, "log_msg": msg}
        values = {st.channel_key(k): str(c.id) for k, c in given.items() if c is not None}
        labels = [f"{st.LOG_KEYS[k]} = #{c.name}" for k, c in given.items() if c is not None]
        if msg_tage is not None:
            values[st.MSG_DAYS_KEY] = str(msg_tage)
            labels.append(t("setup_msg_days", days=msg_tage))
        await self._save(interaction, values, labels)

    @app_commands.command(name="log_aus", description="Ein Server-Log abschalten")
    @app_commands.choices(art=[app_commands.Choice(name=v, value=k) for k, v in st.LOG_KEYS.items()])
    async def log_off(self, interaction: discord.Interaction, art: app_commands.Choice[str]):
        await self._save(interaction, {st.channel_key(art.value): None}, [t("setup_log_off", log=art.name)])

    @app_commands.command(name="abgleich", description="Bestehende [GFK]-Mitglieder einmalig mit stfc.pro verknüpfen")
    async def link(self, interaction: discord.Interaction):
        from gfk.cogs.onboarding import link_existing, link_report, update_unlinked_list
        await interaction.response.defer(ephemeral=True, thinking=True)
        roster = await self.bot.roster.get(self.bot.web, max_age=0)
        if roster is None:
            await interaction.followup.send(t("name_stfc_down"), ephemeral=True)
            return
        linked, already, missing, untagged = await link_existing(interaction.guild, roster)
        await interaction.followup.send(embed=link_report(linked, already, missing, untagged), ephemeral=True)
        await update_unlinked_list(interaction.guild)

    async def uninstall_cleanup(self, guild: discord.Guild):
        """Deinstallation: Erklärung, Liste "Noch nicht verknüpft" und offene Karten in Verwaltung entfernen."""
        config = await db.get_config(guild.id)
        channel = _channel(guild, config, "verwaltung")
        if channel is None:
            return
        ids = [config.get(k) for k in ("info_verwaltung", "verw_unlinked_msg")] + await db.all_notices(guild.id)
        for message_id in ids:
            if message_id:
                try:
                    await channel.get_partial_message(int(message_id)).delete()
                except discord.HTTPException:
                    pass


async def post_info(guild: discord.Guild):
    """Erklärung für die Führung in Verwaltung (Rollenvergabe, Vorfälle): einmal posten und anpinnen, danach nur noch
    bearbeiten."""
    config = await db.get_config(guild.id)
    channel = _channel(guild, config, "verwaltung")
    if channel is None:
        return
    lobby, forum = _channel(guild, config, "eingang"), _channel(guild, config, "vorfallforum")
    stats = f"<#{config['stats_thread']}>" if config.get("stats_thread") else t("verw_reports_no_stats")
    embeds = [discord.Embed(title=t("verw_info_title"), color=discord.Color.blurple(),
                            description=t("verw_info_text", eingang=lobby.mention if lobby else "#eingang")),
              discord.Embed(title=t("verw_reports_title"), color=discord.Color.red(), description=t(
                  "verw_reports_text", forum=forum.mention if forum else "#vorfälle", stats=stats,
                  done_days=st.REPORT_DONE_DAYS, null_days=st.REPORT_NULLNODE_DAYS))]
    msg_id = config.get("info_verwaltung")
    if msg_id:
        try:
            await channel.get_partial_message(int(msg_id)).edit(embeds=embeds)
            return
        except discord.NotFound:
            pass
    message = await channel.send(embeds=embeds, allowed_mentions=discord.AllowedMentions.none())
    try:
        await message.pin(reason="GFK-Bot: Erklärung für die Führung")
        async for notice in channel.history(limit=5):          # Systemhinweis "hat angepinnt" wieder entfernen
            if notice.type == discord.MessageType.pins_add:
                await notice.delete()
    except discord.HTTPException:
        pass
    await db.set_config(guild.id, {"info_verwaltung": str(message.id)})


async def setup(bot: commands.Bot):
    await bot.add_cog(SetupCog(bot))

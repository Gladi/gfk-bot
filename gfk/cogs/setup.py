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
from gfk.views import panels as panels_mod
from gfk.views.panels import PANELS, panel_message

log = logging.getLogger("gfk.setup")

# Benötigte Rechte je Kanal (Schlüssel aus settings.CHANNEL_KEYS) und auf dem Server
CHANNEL_PERMS = {
    "eingang": ["view_channel", "send_messages", "embed_links"],
    "meldungen": ["view_channel", "send_messages", "embed_links"],
    "vorfallforum": ["view_channel", "send_messages", "embed_links", "attach_files", "manage_threads"],
    "events": ["view_channel", "send_messages", "embed_links", "create_public_threads", "create_private_threads",
               "send_messages_in_threads", "manage_threads"],
    "event_kategorie": ["view_channel", "manage_channels", "connect", "speak"],
    "verwaltung": ["view_channel", "send_messages", "embed_links"],
    "eingang_info": ["view_channel", "send_messages", "embed_links"],
    "namen_log": ["view_channel", "send_messages_in_threads"],
}
CHANNEL_LABELS = {**st.CHANNEL_KEYS, **st.OPTIONAL_CHANNEL_KEYS}
GUILD_PERMS = ["manage_roles", "manage_nicknames", "manage_events", "create_events"]
LOG_PERMS = ["view_channel", "send_messages", "embed_links"]


def _role(guild: discord.Guild, config: Dict[str, str], key: str) -> Optional[discord.Role]:
    value = config.get(st.role_key(key))
    return guild.get_role(int(value)) if value else None


def _channel(guild: discord.Guild, config: Dict[str, str], key: str):
    value = config.get(st.channel_key(key))
    return guild.get_channel_or_thread(int(value)) if value else None   # auch Threads/Forenbeiträge


def status_lines(guild: discord.Guild, config: Dict[str, str], message_content: Optional[bool] = None) -> List[str]:
    """Probleme der aktuellen Einrichtung als Textzeilen (leer = alles in Ordnung). message_content: ob der Bot den
    Message Content Intent hat (None = nicht prüfen, z. B. im Test-Werkzeug)."""
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
        perms += [f"{CHANNEL_LABELS[key]}: {p}" for p in needed if not getattr(cp, p, False)]
    active_logs = [k for k in st.LOG_KEYS if _channel(guild, config, k) is not None]
    for key in active_logs:
        cp = _channel(guild, config, key).permissions_for(me)
        perms += [f"{st.LOG_KEYS[key]}: {p}" for p in LOG_PERMS if not getattr(cp, p, False)]
    if active_logs and not gp.view_audit_log:
        perms.append("Server: view_audit_log (wer etwas geändert hat)")
    if perms:
        lines.append(t("setup_perm", items=", ".join(perms)))
    forum = _channel(guild, config, "vorfallforum")
    if isinstance(forum, discord.ForumChannel):
        have = [tag.name for tag in forum.available_tags]
        tags = [n for n in st.REPORT_TAGS if not st.has_tag(have, n)]
        if tags:
            lines.append(t("setup_forum_tags", items=", ".join(tags)))
    elif forum is not None:
        lines.append(t("setup_not_forum"))
    lead = _role(guild, config, "fuehrung")
    if lead is not None and not lead.mentionable and not gp.mention_everyone:
        lines.append(t("setup_lead_mention", role=lead.name))
    if message_content is False and _channel(guild, config, "log_msg") is not None:
        lines.append(t("setup_msg_intent"))
    return lines


async def notify_verwaltung(guild: discord.Guild, text: str = None, **kwargs):
    """Nachricht an die Führung im Kanal Verwaltung (falls eingerichtet); nie mit Pings. Liefert die Nachricht."""
    config = await db.get_config(guild.id)
    ch = _channel(guild, config, "verwaltung")
    if ch is None:
        return None
    try:
        return await ch.send(text, allowed_mentions=discord.AllowedMentions.none(), **kwargs)
    except discord.HTTPException as exc:
        log.warning("Kanal Verwaltung nicht beschreibbar (%s): %s", guild.id, exc)
        return None


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
        await notify_verwaltung(interaction.guild, t("log_setup", user=interaction.user.mention, items=items))

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
    @app_commands.describe(namen_zusatz="Optional: weiterer Kanal mit der Nachricht „Namen ändern“",
                           namensaenderungen="Optional: Thread/Forenbeitrag für geänderte Spielnamen (sonst Verwaltung)")
    @app_commands.rename(namensaenderungen="namensänderungen")
    async def channels(self, interaction: discord.Interaction, eingang: Optional[discord.TextChannel] = None,
                       meldungen: Optional[discord.TextChannel] = None,
                       vorfallforum: Optional[discord.ForumChannel] = None,
                       events: Optional[discord.TextChannel] = None,
                       event_kategorie: Optional[discord.CategoryChannel] = None,
                       verwaltung: Optional[discord.TextChannel] = None,
                       namen_zusatz: Optional[discord.TextChannel] = None,
                       namensaenderungen: Optional[discord.Thread] = None):
        given = {"eingang": eingang, "meldungen": meldungen, "vorfallforum": vorfallforum, "events": events,
                 "event_kategorie": event_kategorie, "verwaltung": verwaltung, "eingang_info": namen_zusatz,
                 "namen_log": namensaenderungen}
        values = {st.channel_key(k): str(c.id) for k, c in given.items() if c is not None}
        labels = [f"{CHANNEL_LABELS[k]} = #{c.name}" for k, c in given.items() if c is not None]
        await self._save(interaction, values, labels)

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
            for key, label in st.CHANNEL_KEYS.items()) + "\n" + "\n".join(
            f"{label}: {c.mention if (c := _channel(guild, config, key)) else t('setup_off')}"
            for key, label in st.OPTIONAL_CHANNEL_KEYS.items()))
        embed.add_field(name=t("setup_logs"), inline=False, value="\n".join(
            f"{label}: {c.mention if (c := _channel(guild, config, key)) else t('setup_off')}"
            for key, label in st.LOG_KEYS.items()) + "\n" + t("setup_msg_days", days=st.msg_days(config)))
        embed.add_field(name=t("setup_reminder_field"), inline=False,
                        value=t("setup_reminder_value", minutes=st.reminder_minutes(config)))
        problems = status_lines(guild, config, self.bot.intents.message_content)
        embed.add_field(name=t("setup_checks"), inline=False, value="\n".join(problems) or t("setup_ok"))
        await interaction.response.send_message(embed=embed, ephemeral=True)

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

    @app_commands.command(name="panels", description="Feste Nachrichten (Buttons) posten oder aktualisieren")
    async def panels(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        posted, missing = await post_panels(interaction.guild)
        if missing:
            await interaction.followup.send(t("panels_missing", items=", ".join(missing)), ephemeral=True)
        if posted:
            await interaction.followup.send(t("panels_posted", items=", ".join(posted)), ephemeral=True)


async def post_info(guild: discord.Guild):
    """Erklärung der Rollenvergabe in Verwaltung: einmal posten und anpinnen, danach nur noch bearbeiten."""
    config = await db.get_config(guild.id)
    channel = _channel(guild, config, "verwaltung")
    if channel is None:
        return
    lobby = _channel(guild, config, "eingang")
    embed = discord.Embed(title=t("verw_info_title"), color=discord.Color.blurple(),
                          description=t("verw_info_text", eingang=lobby.mention if lobby else "#eingang"))
    msg_id = config.get("info_verwaltung")
    if msg_id:
        try:
            await channel.get_partial_message(int(msg_id)).edit(embed=embed)
            return
        except discord.NotFound:
            pass
    message = await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
    try:
        await message.pin(reason="GFK-Bot: Erklärung der Rollenvergabe")
        async for notice in channel.history(limit=5):          # Systemhinweis "hat angepinnt" wieder entfernen
            if notice.type == discord.MessageType.pins_add:
                await notice.delete()
    except discord.HTTPException:
        pass
    await db.set_config(guild.id, {"info_verwaltung": str(message.id)})


async def post_panels(guild: discord.Guild):
    """Postet die festen Nachrichten oder bearbeitet die vorhandenen (damit sie oben im Kanal bleiben)."""
    config = await db.get_config(guild.id)
    posted, missing, updates, fresh = [], [], {}, set()
    targets = []                                   # (Art, Kanal-Schlüssel, Config-Schlüssel der Nachricht, Pflicht)
    for kind, (channel_key, *_rest) in PANELS.items():
        targets.append((kind, channel_key, f"panel_{kind}", True))
        targets += [(kind, k, f"panel_{kind}_{k}", False) for k in st.PANEL_EXTRA_CHANNELS.get(kind, [])]
    for kind, channel_key, msg_key, required in targets:
        ch = _channel(guild, config, channel_key)
        if ch is None:
            if required:
                missing.append(st.CHANNEL_KEYS[channel_key])
            continue
        embed, view = panel_message(kind)
        msg_id = config.get(msg_key)
        message = None
        if msg_id:
            try:
                message = await ch.fetch_message(int(msg_id))
                await message.edit(embed=embed, view=view)
            except discord.NotFound:
                message = None
        if message is None:
            message = await ch.send(embed=embed, view=view)
            updates[msg_key] = str(message.id)
            if required:
                fresh.add(kind)
        posted.append(f"#{ch.name}")
    if updates:
        await db.set_config(guild.id, updates)
    await post_info(guild)
    for kind, hook in list(panels_mod.AFTER_POST.items()):
        try:
            await hook(guild, kind in fresh)
        except Exception:
            log.exception("Nach dem Posten von %s fehlgeschlagen", kind)
    return posted, missing


async def setup(bot: commands.Bot):
    await bot.add_cog(SetupCog(bot))

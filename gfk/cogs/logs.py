"""
GFK-Bot - Server-Logs (ersetzen den SCNX-Bot): user-log, rollen-log, kanal-log, msg-log.

Jedes Log hat einen eigenen Kanal (/setup logs), leer = aus. Wer eine Änderung gemacht hat, steht im Audit-Log von
Discord (Recht "Audit-Log anzeigen"); Änderungen des Bots selbst zeigen "im Auftrag von …" aus dem Grund.
msg-log: Discord schickt bei Löschungen nur die ID und bei Bearbeitungen nur den neuen Text - der alte Text kommt aus
einem Zwischenspeicher NUR im Arbeitsspeicher (Dauer einstellbar, nach einem Neustart leer, nie auf der Platte).
"""
import datetime
import logging
from typing import Dict, Optional

import discord
from discord.ext import commands, tasks

from gfk import db, logfmt, settings as st
from gfk.texts import t

log = logging.getLogger("gfk.logs")

A = discord.AuditLogAction
COLORS = {"join": discord.Color.green(), "leave": discord.Color.light_grey(), "bad": discord.Color.red(),
          "change": discord.Color.blurple(), "msg": discord.Color.orange()}


def _ts(dt: Optional[datetime.datetime]) -> str:
    return f"<t:{int(dt.timestamp())}:R>" if dt else "–"


class LogsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cache = logfmt.MessageCache(max_age=st.MSG_DAYS_DEFAULT * 86400)

    async def cog_load(self):
        self.prune.start()

    async def cog_unload(self):
        self.prune.cancel()

    # ----------------- Hilfen -----------------
    async def _channel(self, guild: discord.Guild, key: str):
        config = await db.get_config(guild.id)
        value = config.get(st.channel_key(key))
        return guild.get_channel(int(value)) if value else None

    async def _send(self, guild: discord.Guild, key: str, embed: discord.Embed):
        ch = await self._channel(guild, key)
        if ch is None:
            return
        embed.timestamp = discord.utils.utcnow()
        try:
            await ch.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException as exc:
            log.warning("Log %s nicht beschreibbar (%s): %s", key, guild.id, exc)

    async def _actor(self, guild: discord.Guild, actions, target_id: int, within: float = 20) -> str:
        """"durch @X (Grund)" aus dem Audit-Log, falls in den letzten Sekunden passend; sonst "" (auch wenn die
        Person es selbst war)."""
        if not guild.me.guild_permissions.view_audit_log:
            return ""
        actions = actions if isinstance(actions, (list, tuple)) else [actions]
        now = discord.utils.utcnow()
        try:
            for action in actions:
                async for entry in guild.audit_logs(limit=5, action=action):
                    target = getattr(entry.target, "id", None)
                    if target == target_id and (now - entry.created_at).total_seconds() < within:
                        if entry.user and entry.user.id == target_id:
                            return ""
                        if entry.user and entry.user.id == self.bot.user.id and entry.reason:
                            return t("log_by_bot", reason=entry.reason)
                        reason = f" - {entry.reason}" if entry.reason else ""
                        return t("log_by", user=entry.user.mention if entry.user else "?", reason=reason)
        except discord.HTTPException:
            return ""
        return ""

    @staticmethod
    def _is_log_channel(channel_id: int, config: Dict[str, str]) -> bool:
        return any(config.get(st.channel_key(k)) == str(channel_id) for k in st.LOG_KEYS)

    # ----------------- user-log -----------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        age, new = logfmt.account_age(member.created_at.timestamp())
        e = discord.Embed(title=t("log_join"), color=COLORS["join"],
                          description=f"{member.mention} ({member})")
        e.add_field(name=t("log_account"), value=(t("log_new_account") + " " if new else "") + age)
        e.add_field(name=t("log_members"), value=str(member.guild.member_count))
        e.set_footer(text=f"ID {member.id}")
        await self._send(member.guild, "log_user", e)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if await self._actor(member.guild, A.ban, member.id):
            return                                    # Bann: eigener Eintrag über on_member_ban
        by = await self._actor(member.guild, A.kick, member.id)
        e = discord.Embed(title=t("log_kick") if by else t("log_leave"), color=COLORS["bad"] if by else COLORS["leave"],
                          description=f"{member.mention} ({member}) {by}".strip())
        roles = [r.mention for r in member.roles if not r.is_default()]
        e.add_field(name=t("log_roles"), value=logfmt.clip(" ".join(roles)))
        e.add_field(name=t("log_joined"), value=_ts(member.joined_at))
        e.set_footer(text=f"ID {member.id}")
        await self._send(member.guild, "log_user", e)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        by = await self._actor(guild, A.ban, user.id)
        await self._send(guild, "log_user", discord.Embed(title=t("log_ban"), color=COLORS["bad"],
                                                          description=f"{user.mention} ({user}) {by}".strip()))

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        by = await self._actor(guild, A.unban, user.id)
        await self._send(guild, "log_user", discord.Embed(title=t("log_unban"), color=COLORS["change"],
                                                          description=f"{user.mention} ({user}) {by}".strip()))

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        guild = after.guild
        if before.nick != after.nick:
            by = await self._actor(guild, A.member_update, after.id)
            e = discord.Embed(title=t("log_nick"), color=COLORS["change"], description=f"{after.mention} {by}".strip())
            e.add_field(name=t("log_before"), value=logfmt.clip(before.nick or before.name))
            e.add_field(name=t("log_after"), value=logfmt.clip(after.nick or after.name))
            await self._send(guild, "log_user", e)
        added = [r for r in after.roles if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]
        if added or removed:
            by = await self._actor(guild, A.member_role_update, after.id)
            e = discord.Embed(title=t("log_member_roles"), color=COLORS["change"],
                              description=f"{after.mention} {by}".strip())
            if added:
                e.add_field(name=t("log_added"), value=logfmt.clip(" ".join(r.mention for r in added)))
            if removed:
                e.add_field(name=t("log_removed"), value=logfmt.clip(" ".join(r.mention for r in removed)))
            await self._send(guild, "log_user", e)
        if before.timed_out_until != after.timed_out_until:
            by = await self._actor(guild, A.member_update, after.id)
            if after.timed_out_until and after.timed_out_until > discord.utils.utcnow():
                title, value = t("log_timeout"), t("log_timeout_until", until=_ts(after.timed_out_until))
            else:
                title, value = t("log_timeout_end"), "–"
            e = discord.Embed(title=title, color=COLORS["bad"], description=f"{after.mention} {by}".strip())
            e.add_field(name=t("log_until"), value=value)
            await self._send(guild, "log_user", e)

    # ----------------- rollen-log -----------------
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        by = await self._actor(role.guild, A.role_create, role.id)
        await self._send(role.guild, "log_rollen", discord.Embed(title=t("log_role_create"), color=COLORS["join"],
                                                                 description=f"{role.mention} {by}".strip()))

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        by = await self._actor(role.guild, A.role_delete, role.id)
        await self._send(role.guild, "log_rollen", discord.Embed(title=t("log_role_delete"), color=COLORS["bad"],
                                                                 description=f"**{role.name}** {by}".strip()))

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        lines = []
        if before.name != after.name:
            lines.append(t("log_name_change", before=before.name, after=after.name))
        if before.color != after.color:
            lines.append(t("log_color_change", before=before.color, after=after.color))
        if before.hoist != after.hoist:
            lines.append(t("log_hoist", value=t("yes") if after.hoist else t("no")))
        if before.mentionable != after.mentionable:
            lines.append(t("log_mentionable", value=t("yes") if after.mentionable else t("no")))
        added, removed = logfmt.perm_diff(before.permissions, after.permissions)
        if added:
            lines.append("✅ " + ", ".join(added))
        if removed:
            lines.append("❌ " + ", ".join(removed))
        if not lines:
            return                                   # z. B. nur Position verschoben
        by = await self._actor(after.guild, A.role_update, after.id)
        e = discord.Embed(title=t("log_role_update"), color=COLORS["change"], description=f"{after.mention} {by}".strip())
        e.add_field(name=t("log_changes"), value=logfmt.clip("\n".join(lines)), inline=False)
        await self._send(after.guild, "log_rollen", e)

    # ----------------- kanal-log -----------------
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        by = await self._actor(channel.guild, A.channel_create, channel.id)
        await self._send(channel.guild, "log_kanal", discord.Embed(title=t("log_channel_create"), color=COLORS["join"],
                                                                   description=f"{channel.mention} {by}".strip()))

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        by = await self._actor(channel.guild, A.channel_delete, channel.id)
        await self._send(channel.guild, "log_kanal", discord.Embed(title=t("log_channel_delete"), color=COLORS["bad"],
                                                                   description=f"**#{channel.name}** {by}".strip()))

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        lines = []
        if before.name != after.name:
            lines.append(t("log_name_change", before=before.name, after=after.name))
        if getattr(before, "category_id", None) != getattr(after, "category_id", None):
            lines.append(t("log_category", before=getattr(before.category, "name", "–"),
                           after=getattr(after.category, "name", "–")))
        if getattr(before, "topic", None) != getattr(after, "topic", None):
            lines.append(t("log_topic", after=logfmt.clip(getattr(after, "topic", None), 200)))

        def ow(ch):
            return {getattr(k, "name", str(k)): {p: v for p, v in o} for k, o in ch.overwrites.items()}
        lines += logfmt.overwrite_diff(ow(before), ow(after))
        if not lines:
            return
        by = await self._actor(after.guild, [A.channel_update, A.overwrite_update, A.overwrite_create,
                                             A.overwrite_delete], after.id)
        e = discord.Embed(title=t("log_channel_update"), color=COLORS["change"], description=f"{after.mention} {by}".strip())
        e.add_field(name=t("log_changes"), value=logfmt.clip("\n".join(lines)), inline=False)
        await self._send(after.guild, "log_kanal", e)

    # ----------------- msg-log -----------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None or message.author.bot or message.webhook_id or not self.bot.intents.message_content:
            return
        config = await db.get_config(message.guild.id)
        if not config.get(st.channel_key("log_msg")) or self._is_log_channel(message.channel.id, config):
            return                                    # msg-log aus: nichts zwischenspeichern
        self.cache.max_age = st.msg_days(config) * 86400
        self.cache.put(message.id, logfmt.Cached(message.channel.id, message.author.id, message.content,
                                                 [a.filename for a in message.attachments]))

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        if payload.guild_id is None or "content" not in payload.data:
            return
        item = self.cache.get(payload.message_id)
        new = payload.data.get("content") or ""
        if item is None or item.content == new:
            return                                    # unbekannt (zu alt / nicht gespeichert) oder nur Vorschau geändert
        guild = self.bot.get_guild(payload.guild_id)
        e = discord.Embed(title=t("log_msg_edit"), color=COLORS["msg"],
                          description=t("log_msg_where", user=f"<@{item.author_id}>", channel=f"<#{item.channel_id}>",
                                        link=f"https://discord.com/channels/{payload.guild_id}/{item.channel_id}/"
                                             f"{payload.message_id}"))
        e.add_field(name=t("log_before"), value=logfmt.clip(item.content), inline=False)
        e.add_field(name=t("log_after"), value=logfmt.clip(new), inline=False)
        item.content = new
        await self._send(guild, "log_msg", e)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if payload.guild_id is None:
            return
        item = self.cache.pop(payload.message_id)
        if item is None:
            return                                    # nicht im Speicher (Bot-Nachricht, zu alt, vor dem Neustart)
        guild = self.bot.get_guild(payload.guild_id)
        by = await self._actor(guild, A.message_delete, item.author_id, within=15)
        e = discord.Embed(title=t("log_msg_delete"), color=COLORS["bad"],
                          description=t("log_msg_where_short", user=f"<@{item.author_id}>",
                                        channel=f"<#{item.channel_id}>") + (f" {by}" if by else ""))
        e.add_field(name=t("log_content"), value=logfmt.clip(item.content), inline=False)
        if item.attachments:
            e.add_field(name=t("log_files"), value=logfmt.clip(", ".join(item.attachments)), inline=False)
        await self._send(guild, "log_msg", e)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        if payload.guild_id is None:
            return
        known = [self.cache.pop(i) for i in payload.message_ids]
        guild = self.bot.get_guild(payload.guild_id)
        e = discord.Embed(title=t("log_msg_bulk", count=len(payload.message_ids)), color=COLORS["bad"],
                          description=f"<#{payload.channel_id}>")
        text = "\n".join(f"<@{k.author_id}>: {k.content}" for k in known if k)
        if text:
            e.add_field(name=t("log_content"), value=logfmt.clip(text), inline=False)
        await self._send(guild, "log_msg", e)

    @tasks.loop(hours=1)
    async def prune(self):
        self.cache.prune()


async def setup(bot: commands.Bot):
    await bot.add_cog(LogsCog(bot))

"""
GFK-Bot - Eingangskontrolle (Paket 2).

Neue Nutzer haben keine Rolle und sehen nur den Eingangskanal. Button "Namen ändern" -> Formular (Allianzkürzel
optional, Spielname) -> Nickname `[ALLY] Name` bzw. `Name`. Bei GFK wird der Name mit der Mitgliederliste auf
stfc.pro abgeglichen (Vorschläge bei Tippfehlern) und die Spieler-ID gemerkt; ein täglicher Abgleich zieht spätere
Namensänderungen nach. Wer noch keinen Status hat, wird Gast; die Führung bekommt in "Verwaltung" eine Nachricht mit
Buttons Freund / Mitglied / Führung.
"""
import asyncio
import logging
from typing import Dict, Optional, Set

import aiohttp
import discord
from discord.ext import commands, tasks

from gfk import db, names, settings as st, stfc
from gfk.cogs.setup import notify_verwaltung
from gfk.texts import t
from gfk.views import panels

log = logging.getLogger("gfk.onboarding")

SYNC_HOURS = 24


def status_of(member: discord.Member, config: Dict[str, str]) -> Set[str]:
    """Status-Schlüssel ("admiral", "fuehrung" …) der Rollen, die das Mitglied hat."""
    ids = {r.id for r in member.roles}
    return {k for k in st.STATUS_ROLES if (v := config.get(st.role_key(k))) and int(v) in ids}


async def _reply(interaction: discord.Interaction, text: str, view: Optional[discord.ui.View] = None):
    kwargs = {"ephemeral": True}
    if view is not None:
        kwargs["view"] = view
    if interaction.response.is_done():
        await interaction.followup.send(text, **kwargs)
    else:
        await interaction.response.send_message(text, **kwargs)


# ----------------- Formular und Auswahl -----------------
class NameModal(discord.ui.Modal, title=t("name_modal_title")):
    tag = discord.ui.TextInput(label=t("name_tag_label"), placeholder=t("name_tag_placeholder"), required=False,
                               max_length=8)
    name = discord.ui.TextInput(label=t("name_name_label"), required=True, max_length=32)

    def __init__(self, cog: "OnboardingCog"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        try:
            tag = names.clean_tag(self.tag.value)
            name = names.clean_name(self.name.value)
        except ValueError:
            await interaction.response.send_message(t("name_bad_input"), ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        if tag != stfc.ALLIANCE_TAG:
            await self.cog.apply_name(interaction, tag, name, None)
            return
        roster = await self.cog.bot.roster.get(self.cog.bot.web)
        if roster is None:
            await self.cog.apply_name(interaction, tag, name, None, note=t("name_stfc_down"))
            return
        player = stfc.find(roster, name)
        if player is not None:
            await self.cog.apply_name(interaction, tag, player.name, player)
            return
        hints = stfc.suggestions(roster, name)
        text = t("name_not_found", name=name) if hints else t("name_not_found_none", name=name)
        await _reply(interaction, text, view=MatchView(self.cog, interaction.user.id, tag, name, hints))


class MatchView(discord.ui.View):
    """Vorschläge aus der stfc.pro-Liste oder den eingegebenen Namen trotzdem übernehmen."""

    def __init__(self, cog, user_id: int, tag: str, name: str, hints):
        super().__init__(timeout=300)
        self.cog, self.user_id, self.tag, self.name = cog, user_id, tag, name
        self.hints = {str(p.player_id): p for p in hints}
        if hints:
            select = discord.ui.Select(placeholder=t("name_select_placeholder"), options=[
                discord.SelectOption(label=p.name, value=str(p.player_id), description=p.rank or None) for p in hints])
            select.callback = self.on_select
            self.add_item(select)
        keep = discord.ui.Button(label=t("name_keep"), style=discord.ButtonStyle.secondary)
        keep.callback = self.on_keep
        self.add_item(keep)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    async def on_select(self, interaction: discord.Interaction):
        player = self.hints[interaction.data["values"][0]]
        await interaction.response.edit_message(view=None)
        await self.cog.apply_name(interaction, self.tag, player.name, player)
        self.stop()

    async def on_keep(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=None)
        await self.cog.apply_name(interaction, self.tag, self.name, None)
        self.stop()


# ----------------- Status-Buttons in "Verwaltung" -----------------
class StatusButton(discord.ui.DynamicItem[discord.ui.Button],
                   template=r"gfk:status:(?P<user>\d+):(?P<role>freund|mitglied|fuehrung)"):
    STYLES = {"freund": discord.ButtonStyle.secondary, "mitglied": discord.ButtonStyle.success,
              "fuehrung": discord.ButtonStyle.primary}

    def __init__(self, user_id: int, role: str):
        super().__init__(discord.ui.Button(label=st.ROLE_KEYS[role], style=self.STYLES[role],
                                           custom_id=f"gfk:status:{user_id}:{role}"))
        self.user_id, self.role = user_id, role

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match):
        return cls(int(match["user"]), match["role"])

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        config = await db.get_config(guild.id)
        target = guild.get_member(self.user_id)
        if target is None:
            await interaction.response.send_message(t("status_gone"), ephemeral=True)
            return
        current = status_of(target, config)
        if not names.may_grant(status_of(interaction.user, config), self.role, current):
            await interaction.response.send_message(t("status_denied"), ephemeral=True)
            return
        row = await db.get_member(guild.id, target.id)
        alliance = row[0] if row else ""
        if not names.allowed_for_alliance(self.role, alliance, stfc.ALLIANCE_TAG):
            await interaction.response.send_message(
                t("status_gfk_only", target=target.mention, role=st.ROLE_KEYS[self.role],
                  tag=f"[{alliance}]" if alliance else t("verw_no_ally")), ephemeral=True)
            return
        label = st.ROLE_KEYS[self.role]
        if self.role in current and len(current) == 1:
            await interaction.response.send_message(t("status_already", target=target.mention, role=label),
                                                    ephemeral=True)
            return
        await set_status(guild, config, target, self.role, interaction.user)
        await interaction.response.send_message(t("status_done", target=target.mention, role=label), ephemeral=True)
        if interaction.message and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            embed.description = (embed.description or "") + "\n" + t(
                "verw_status_set", target=target.mention, role=label, actor=interaction.user.mention)
            await interaction.message.edit(embed=embed)


def status_view(user_id: int, alliance: Optional[str]) -> discord.ui.View:
    """Buttons für die Führung; ohne GFK-Kürzel nur "Freund" (Mitglied/Führung nur für GFK)."""
    view = discord.ui.View(timeout=None)
    for role in ("freund", "mitglied", "fuehrung"):
        if names.allowed_for_alliance(role, alliance, stfc.ALLIANCE_TAG):
            view.add_item(StatusButton(user_id, role))
    return view


async def set_status(guild: discord.Guild, config: Dict[str, str], member: discord.Member, target: str,
                     actor: discord.abc.User):
    """Genau eine Status-Rolle setzen (der Admiral bleibt unberührt) und protokollieren."""
    current = status_of(member, config)
    remove, add = names.status_change(current, target, st.STATUS_ROLES)
    reason = f"GFK-Bot im Auftrag von {actor} ({actor.id})"
    to_role = lambda keys: [r for k in keys if (v := config.get(st.role_key(k))) and (r := guild.get_role(int(v)))]  # noqa: E731
    if remove:
        await member.remove_roles(*to_role(remove), reason=reason)
    if add:
        await member.add_roles(*to_role(add), reason=reason)
    await db.log_role_change(guild.id, actor.id, member.id, ",".join(sorted(current)) or "-", target)


# ----------------- Modul -----------------
class OnboardingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        panels.HANDLERS["lobby"] = self.open_form
        self.bot.add_dynamic_items(StatusButton)
        self.sync_names.start()

    async def cog_unload(self):
        panels.HANDLERS.pop("lobby", None)
        self.sync_names.cancel()

    async def open_form(self, interaction: discord.Interaction):
        await interaction.response.send_modal(NameModal(self))

    async def apply_name(self, interaction: discord.Interaction, tag: Optional[str], name: str,
                         player: Optional[stfc.Player], note: str = ""):
        guild, member = interaction.guild, interaction.user
        config = await db.get_config(guild.id)
        nick = names.nickname(tag, name)
        lines = [t("name_done", nick=nick)]
        try:
            if member.display_name != nick:
                await member.edit(nick=nick, reason="GFK-Bot: Eingangskontrolle")
        except discord.Forbidden:
            lines = [t("name_no_nick_perm", nick=nick)]
        first_time = not status_of(member, config)
        if first_time and config.get(st.role_key("gast")):
            await set_status(guild, config, member, "gast", self.bot.user)
            lines.append(t("name_done_guest"))
        await db.save_member(guild.id, member.id, tag or "", name, player.player_id if player else None)
        if note:
            lines.append(note)
        await _reply(interaction, "\n".join(lines))
        if first_time:
            embed = discord.Embed(title=t("verw_new_guest_title"), color=discord.Color.blurple(),
                                  description=t("verw_new_guest", user=member.mention, nick=nick))
            if tag == stfc.ALLIANCE_TAG:
                embed.add_field(name="stfc.pro", value=t("verw_stfc_ok", rank=player.rank or "?") if player
                                else t("verw_stfc_missing"))
            elif not tag:
                embed.add_field(name=t("verw_alliance"), value=t("verw_no_ally"))
            await notify_verwaltung(guild, embed=embed, view=status_view(member.id, tag))

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await db.delete_member(member.guild.id, member.id)   # Spieler-ID nur, solange jemand auf dem Server ist

    # ----------------- täglicher Abgleich mit stfc.pro -----------------
    @tasks.loop(hours=SYNC_HOURS)
    async def sync_names(self):
        for guild in self.bot.guilds:
            try:
                await self.sync_guild(guild)
            except Exception:
                log.exception("Namensabgleich fehlgeschlagen (%s)", guild.id)

    @sync_names.before_loop
    async def _before_sync(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(300)                          # nicht direkt beim Start

    async def sync_guild(self, guild: discord.Guild):
        rows = await db.linked_members(guild.id)
        if not rows:
            return
        roster = await self.bot.roster.get(self.bot.web, max_age=3600)
        if roster is None:
            return
        for user_id, alliance, game_name, player_id in rows:
            member = guild.get_member(user_id)
            if member is None:
                await db.delete_member(guild.id, user_id)
                continue
            player = roster.get(player_id)
            if player is None:
                await db.save_member(guild.id, user_id, alliance, game_name, None)
                await notify_verwaltung(guild, t("sync_left", user=member.mention, name=game_name))
                continue
            if player.name == game_name:
                continue
            nick = names.nickname(alliance or stfc.ALLIANCE_TAG, player.name)
            try:
                await member.edit(nick=nick, reason="GFK-Bot: Name auf stfc.pro geändert")
            except discord.Forbidden:
                log.info("Nickname von %s nicht änderbar", user_id)
            await db.save_member(guild.id, user_id, alliance, player.name, player_id)
            await notify_verwaltung(guild, t("sync_renamed", user=member.mention, nick=nick, old=game_name))


async def setup(bot: commands.Bot):
    if not hasattr(bot, "web"):
        bot.web = aiohttp.ClientSession()
    if not hasattr(bot, "roster"):
        bot.roster = stfc.Roster()
    await bot.add_cog(OnboardingCog(bot))

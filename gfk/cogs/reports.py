"""
GFK-Bot - Meldungen (Paket 4): ROE-Verstöße, Null-Node-Meldungen, Sonstiges.

Button "Meldung erstellen" im Meldungskanal (nur Mitglied, Führung, Admiral) -> Formular mit Kategorie, Allianz
(optional), Spieler, Beschreibung und bis zu 5 Screenshots -> Beitrag im Vorfallforum mit Erwähnung der Führung,
Forum-Tags (Kategorie + Offen/Erledigt) und Button "Erledigt" (nur Führung). Gäste und Freunde melden ohne Bot.
"""
import datetime as dt
import logging
from typing import List, Optional

import discord
from discord.ext import commands

from gfk import db, names, settings as st
from gfk.cogs.onboarding import status_of
from gfk.cogs.setup import _channel, _role
from gfk.texts import t
from gfk.util import guarded
from gfk.views import panels

log = logging.getLogger("gfk.reports")

CATEGORIES, STATUS_TAGS, ALL_TAGS = st.REPORT_CATEGORIES, st.REPORT_STATUS_TAGS, st.REPORT_TAGS
MAX_FILES = 5


def report_title(category: str, alliance: Optional[str], player: str, when: dt.datetime) -> str:
    """`[Kategorie] Allianz – Spieler – TT.MM.JJJJ` (ohne Allianz: `[Kategorie] Spieler – Datum`), höchstens 100."""
    parts = [p for p in (alliance, player) if p] + [f"{when:%d.%m.%Y}"]
    title = f"[{CATEGORIES.get(category, category)}] " + " – ".join(parts)
    return title if len(title) <= 100 else title[:99] + "…"


def find_tags(forum: discord.ForumChannel, wanted: List[str]) -> List[discord.ForumTag]:
    by_name = {tag.name.casefold(): tag for tag in forum.available_tags}
    return [by_name[w.casefold()] for w in wanted if w.casefold() in by_name]


def missing_tags(forum: discord.ForumChannel) -> List[str]:
    have = {tag.name.casefold() for tag in forum.available_tags}
    return [name for name in ALL_TAGS if name.casefold() not in have]


async def ensure_tags(guild: discord.Guild, newly_posted: bool = False):
    """Fehlende Forum-Tags anlegen (braucht "Kanäle verwalten" am Forum; ohne das zeigt /setup anzeigen den Hinweis)."""
    forum = _channel(guild, await db.get_config(guild.id), "vorfallforum")
    if not isinstance(forum, discord.ForumChannel) or not missing_tags(forum):
        return
    tags = list(forum.available_tags) + [discord.ForumTag(name=n) for n in missing_tags(forum)]
    try:
        await forum.edit(available_tags=tags[:20], reason="GFK-Bot: Tags für Meldungen")
    except discord.HTTPException as exc:
        log.info("Forum-Tags nicht anlegbar (%s): %s", guild.id, exc)


def report_embed(report: dict, reporter_id: int) -> discord.Embed:
    e = discord.Embed(title=f"🚨 {CATEGORIES.get(report['category'], report['category'])}",
                      description=report["description"], color=discord.Color.red())
    e.add_field(name=t("rep_f_reporter"), value=f"<@{reporter_id}>")
    e.add_field(name=t("rep_f_alliance"), value=report["alliance"] or t("rep_no_alliance"))
    e.add_field(name=t("rep_f_player"), value=report["player"])
    e.add_field(name=t("rep_f_status"), value=t("rep_open"), inline=False)
    e.set_footer(text=t("rep_footer", id=report["id"]))
    e.timestamp = discord.utils.utcnow()
    return e


class DoneButton(discord.ui.DynamicItem[discord.ui.Button], template=r"gfk:report:done:(?P<id>\d+)"):
    def __init__(self, report_id: int, done: bool = False):
        super().__init__(discord.ui.Button(label=t("rep_done_button_done") if done else t("rep_done_button"),
                                           emoji="✅", style=discord.ButtonStyle.success, disabled=done,
                                           custom_id=f"gfk:report:done:{report_id}"))
        self.report_id = report_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match):
        return cls(int(match["id"]))

    @guarded
    async def callback(self, interaction: discord.Interaction):
        config = await db.get_config(interaction.guild_id)
        if not names.is_lead(status_of(interaction.user, config)):
            await interaction.response.send_message(t("rep_done_denied"), ephemeral=True)
            return
        if not await db.close_report(self.report_id, interaction.user.id):
            await interaction.response.send_message(t("rep_already_done"), ephemeral=True)
            return
        await interaction.response.defer()
        await finish_report(interaction.message, self.report_id, interaction.user)


async def finish_report(message: discord.Message, report_id: int, actor: discord.abc.User):
    """Startnachricht als erledigt markieren, Tag Offen -> Erledigt, Beitrag archivieren."""
    embed = message.embeds[0] if message.embeds else discord.Embed()
    now = discord.utils.utcnow()
    value = t("rep_done_by", user=actor.mention, when=f"<t:{int(now.timestamp())}:f>")
    for i, field in enumerate(embed.fields):
        if field.name == t("rep_f_status"):
            embed.set_field_at(i, name=field.name, value=value, inline=False)
    embed.color = discord.Color.green()
    view = discord.ui.View(timeout=None)
    view.add_item(DoneButton(report_id, done=True))
    await message.edit(embed=embed, view=view)
    thread = message.channel
    if isinstance(thread, discord.Thread):
        await thread.send(t("rep_done_note", user=actor.mention), allowed_mentions=discord.AllowedMentions.none())
        forum = thread.parent
        tags = [tag for tag in thread.applied_tags if tag.name.casefold() != STATUS_TAGS["open"].casefold()]
        if isinstance(forum, discord.ForumChannel):
            tags += [tag for tag in find_tags(forum, [STATUS_TAGS["done"]]) if tag not in tags]
        try:
            await thread.edit(applied_tags=tags[:5], archived=True, reason=f"GFK-Bot: erledigt ({actor})")
        except discord.HTTPException as exc:
            log.warning("Beitrag %s nicht archivierbar: %s", thread.id, exc)


def report_view(report_id: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(DoneButton(report_id))
    return view


async def create_report(guild: discord.Guild, reporter: discord.Member, category: str, alliance: str, player: str,
                        description: str, attachments: List[discord.Attachment] = ()) -> (discord.Thread, List[str]):
    """Legt den Forenbeitrag an. Liefert (Thread, übersprungene Dateien). ValueError("no_forum"), wenn nicht eingerichtet."""
    config = await db.get_config(guild.id)
    forum = _channel(guild, config, "vorfallforum")
    if not isinstance(forum, discord.ForumChannel):
        raise ValueError("no_forum")
    report_id = await db.create_report(guild.id, reporter.id, category, alliance, player, description)
    report = {"id": report_id, "category": category, "alliance": alliance, "player": player,
              "description": description}
    files, skipped = [], []
    for a in list(attachments)[:MAX_FILES]:
        if a.size > guild.filesize_limit:
            skipped.append(a.filename)
            continue
        try:
            files.append(await a.to_file())
        except discord.HTTPException:
            skipped.append(a.filename)
    lead = _role(guild, config, "fuehrung")
    tags = find_tags(forum, [CATEGORIES[category], STATUS_TAGS["open"]])
    kwargs = dict(name=report_title(category, alliance, player, dt.datetime.now(dt.timezone.utc).astimezone()),
                  content=(lead.mention + " " if lead else "") + t("rep_new_content", user=reporter.mention),
                  embed=report_embed(report, reporter.id), view=report_view(report_id), applied_tags=tags,
                  allowed_mentions=discord.AllowedMentions(roles=[lead] if lead else False, users=False,
                                                           everyone=False),
                  reason=f"GFK-Bot: Meldung von {reporter}")
    try:
        try:
            created = await forum.create_thread(files=files, **kwargs)
        except discord.HTTPException as exc:
            if not files or exc.status != 413:
                raise
            skipped += [f.filename for f in files]               # zu groß zusammen -> ohne Dateien
            created = await forum.create_thread(**kwargs)
    except Exception:
        await db.delete_report(report_id)
        raise
    await db.set_report_thread(report_id, created.thread.id)
    return created.thread, skipped


class ReportModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title=t("rep_modal_title"), timeout=1200)
        self.category = discord.ui.Select(placeholder=t("rep_cat_placeholder"), options=[
            discord.SelectOption(label=v, value=k) for k, v in CATEGORIES.items()])
        self.alliance = discord.ui.TextInput(required=False, max_length=30, placeholder=t("rep_alliance_placeholder"))
        self.player = discord.ui.TextInput(required=True, max_length=60)
        self.description = discord.ui.TextInput(style=discord.TextStyle.paragraph, required=True, max_length=1500,
                                                placeholder=t("rep_desc_placeholder"))
        self.files = discord.ui.FileUpload(required=False, min_values=0, max_values=MAX_FILES)
        self.add_item(discord.ui.Label(text=t("rep_f_category"), component=self.category))
        self.add_item(discord.ui.Label(text=t("rep_f_alliance"), description=t("rep_alliance_hint"),
                                       component=self.alliance))
        self.add_item(discord.ui.Label(text=t("rep_f_player"), component=self.player))
        self.add_item(discord.ui.Label(text=t("rep_f_description"), component=self.description))
        self.add_item(discord.ui.Label(text=t("rep_f_files"), description=t("rep_files_hint"), component=self.files))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        category = self.category.values[0] if self.category.values else "sonstiges"
        alliance = " ".join(self.alliance.value.split())
        player = " ".join(self.player.value.split())
        description = self.description.value.strip()
        if not player or not description:
            await interaction.followup.send(t("rep_bad_input"), ephemeral=True)
            return
        try:
            thread, skipped = await create_report(interaction.guild, interaction.user, category, alliance, player,
                                                  description, list(self.files.values or []))
        except ValueError:
            await interaction.followup.send(t("rep_no_forum"), ephemeral=True)
            return
        lines = [t("rep_created", thread=thread.mention)]
        if skipped:
            lines.append(t("rep_files_skipped", files=", ".join(skipped)))
        await interaction.followup.send("\n".join(lines), ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        log.exception("Meldung fehlgeschlagen", exc_info=error)
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send(t("error"), ephemeral=True)


class ReportsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        panels.HANDLERS["report"] = self.open_form
        panels.AFTER_POST["report"] = ensure_tags
        self.bot.add_dynamic_items(DoneButton)

    async def cog_unload(self):
        panels.HANDLERS.pop("report", None)
        panels.AFTER_POST.pop("report", None)

    async def open_form(self, interaction: discord.Interaction):
        config = await db.get_config(interaction.guild_id)
        if not names.is_internal(status_of(interaction.user, config)):
            await interaction.response.send_message(t("internal_only_report"), ephemeral=True)
            return
        await interaction.response.send_modal(ReportModal())


async def setup(bot: commands.Bot):
    await bot.add_cog(ReportsCog(bot))

"""
GFK-Bot - Meldungen (Paket 4): ROE-Verstöße, Null-Node-Meldungen, Sonstiges.

Button "Meldung erstellen" im Meldungskanal (nur Mitglied, Führung, Admiral) -> Formular mit Kategorie, Allianz
(optional), Spieler, Beschreibung und bis zu 5 Screenshots -> Beitrag im Vorfallforum mit Erwähnung der Führung,
Forum-Tags (Kategorie + Offen/In Bearbeitung/Erledigt) und Buttons "In Bearbeitung" und "Erledigt" (nur Führung).
0-Node-Meldungen sind nur Nachweise: keine Buttons, nach 14 Tagen gelöscht. Gäste und Freunde melden ohne Bot.

Alle 6 Stunden räumt der Bot das Vorfallforum auf (erledigt + 30 Tage ohne Aktivität, 0-Node nach 14 Tagen; angepinnte
Beiträge nie) und aktualisiert im Logbuch den Beitrag "Vorfall Statistik" (dort dürfen nur seine Nachrichten stehen).
"""
import asyncio
import datetime as dt
import logging
from typing import Dict, List, Optional

import discord
from discord.ext import commands, tasks

from gfk import db, names, reportstats, settings as st
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
    found = []
    for w in wanted:
        tag = next((by_name[n.casefold()] for n in st.tag_names(w) if n.casefold() in by_name), None)
        if tag is not None:
            found.append(tag)
    return found


def missing_tags(forum: discord.ForumChannel) -> List[str]:
    have = [tag.name for tag in forum.available_tags]
    return [name for name in ALL_TAGS if not st.has_tag(have, name)]


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
    e.add_field(name=t("rep_f_status"), inline=False, value=t("rep_proof", days=st.REPORT_NULLNODE_DAYS)
                if report["category"] == "nullnode" else t("rep_open"))
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


class ProgressButton(discord.ui.DynamicItem[discord.ui.Button], template=r"gfk:report:progress:(?P<id>\d+)"):
    def __init__(self, report_id: int, taken: bool = False):
        super().__init__(discord.ui.Button(
            label=t("rep_progress_button_done") if taken else t("rep_progress_button"), emoji="🔵",
            style=discord.ButtonStyle.primary, disabled=taken, custom_id=f"gfk:report:progress:{report_id}"))
        self.report_id = report_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match):
        return cls(int(match["id"]))

    @guarded
    async def callback(self, interaction: discord.Interaction):
        config = await db.get_config(interaction.guild_id)
        if not names.is_lead(status_of(interaction.user, config)):
            await interaction.response.send_message(t("rep_progress_denied"), ephemeral=True)
            return
        if not await db.progress_report(self.report_id, interaction.user.id):
            await interaction.response.send_message(t("rep_progress_already"), ephemeral=True)
            return
        await interaction.response.defer()
        await start_progress(interaction.message, self.report_id, interaction.user)


def _status_names(*keys: str) -> set:
    return {n.casefold() for key in keys for n in st.tag_names(STATUS_TAGS[key])}


async def _set_status_tag(thread: discord.Thread, key: str, **edit):
    """Status-Tag tauschen (Kategorie-Tags bleiben) und den Beitrag ggf. zusätzlich ändern (z. B. archivieren)."""
    tags = [tag for tag in thread.applied_tags if tag.name.casefold() not in _status_names(*STATUS_TAGS)]
    if isinstance(thread.parent, discord.ForumChannel):
        tags += [tag for tag in find_tags(thread.parent, [STATUS_TAGS[key]]) if tag not in tags]
    try:
        await thread.edit(applied_tags=tags[:5], **edit)
    except discord.HTTPException as exc:
        log.warning("Beitrag %s nicht änderbar: %s", thread.id, exc)


def _set_status_field(embed: discord.Embed, value: str):
    for i, field in enumerate(embed.fields):
        if field.name == t("rep_f_status"):
            embed.set_field_at(i, name=field.name, value=value, inline=False)


async def start_progress(message: discord.Message, report_id: int, actor: discord.abc.User):
    """Führung übernimmt: Status im Embed, Button deaktiviert, Tag "In Bearbeitung"."""
    embed = message.embeds[0] if message.embeds else discord.Embed()
    _set_status_field(embed, t("rep_progress_by", user=actor.mention,
                               when=f"<t:{int(discord.utils.utcnow().timestamp())}:f>"))
    embed.color = discord.Color.blue()
    await message.edit(embed=embed, view=report_view(report_id, "roe", taken=True))
    thread = message.channel
    if isinstance(thread, discord.Thread):
        await thread.send(t("rep_progress_note", user=actor.mention), allowed_mentions=discord.AllowedMentions.none())
        await _set_status_tag(thread, "progress", reason=f"GFK-Bot: in Bearbeitung ({actor})")


async def finish_report(message: discord.Message, report_id: int, actor: discord.abc.User):
    """Startnachricht als erledigt markieren, Tag Offen -> Erledigt, Beitrag archivieren."""
    embed = message.embeds[0] if message.embeds else discord.Embed()
    _set_status_field(embed, t("rep_done_by", user=actor.mention,
                               when=f"<t:{int(discord.utils.utcnow().timestamp())}:f>"))
    embed.color = discord.Color.green()
    view = discord.ui.View(timeout=None)
    view.add_item(DoneButton(report_id, done=True))
    await message.edit(embed=embed, view=view)
    thread = message.channel
    if isinstance(thread, discord.Thread):
        await thread.send(t("rep_done_note", user=actor.mention), allowed_mentions=discord.AllowedMentions.none())
        await _set_status_tag(thread, "done", archived=True, reason=f"GFK-Bot: erledigt ({actor})")


def report_view(report_id: int, category: str, taken: bool = False) -> Optional[discord.ui.View]:
    """0-Node: keine Buttons (nur Nachweis). Sonst "In Bearbeitung" (danach deaktiviert) und "Erledigt"."""
    if category == "nullnode":
        return None
    view = discord.ui.View(timeout=None)
    view.add_item(ProgressButton(report_id, taken=taken))
    view.add_item(DoneButton(report_id))
    return view


def cleanup_reason(tag_names, created: dt.datetime, last_activity: dt.datetime, pinned: bool,
                   now: dt.datetime) -> Optional[str]:
    """Muss ein Beitrag im Vorfallforum weg? "nullnode" (Nachweis älter als 14 Tage), "done" (erledigt und 30 Tage ohne
    Aktivität) oder None. Angepinnte Beiträge (z. B. Erklärungen) nie."""
    if pinned:
        return None
    have = {n.casefold() for n in tag_names}
    if have & {n.casefold() for n in st.tag_names(CATEGORIES["nullnode"])} and \
            now - created > dt.timedelta(days=st.REPORT_NULLNODE_DAYS):
        return "nullnode"
    if have & _status_names("done") and now - last_activity > dt.timedelta(days=st.REPORT_DONE_DAYS):
        return "done"
    return None


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
    tags = find_tags(forum, [CATEGORIES[category]] + ([] if category == "nullnode" else [STATUS_TAGS["open"]]))
    kwargs = dict(name=report_title(category, alliance, player, dt.datetime.now(dt.timezone.utc).astimezone()),
                  content=(lead.mention + " " if lead else "") + t("rep_new_content", user=reporter.mention),
                  embed=report_embed(report, reporter.id), applied_tags=tags,
                  allowed_mentions=discord.AllowedMentions(roles=[lead] if lead else False, users=False,
                                                           everyone=False),
                  reason=f"GFK-Bot: Meldung von {reporter}")
    view = report_view(report_id, category)
    if view is not None:
        kwargs["view"] = view
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
    try:
        await update_stats(guild)
    except Exception:
        log.exception("Vorfall-Statistik nicht aktualisierbar")
    return created.thread, skipped


# ----------------- Vorfall-Statistik im Logbuch -----------------
_stats_lock = asyncio.Lock()
STATS_THREADS: Dict[int, int] = {}          # Server -> Beitrag "Vorfall Statistik" (für on_message)


async def _thread_by_id(guild: discord.Guild, thread_id: int) -> Optional[discord.Thread]:
    thread = guild.get_thread(thread_id)
    if thread is None:
        try:
            thread = await guild.fetch_channel(thread_id)
        except discord.HTTPException:
            return None
    return thread if isinstance(thread, discord.Thread) else None


async def update_stats(guild: discord.Guild):
    """Beitrag "Vorfall Statistik" im Logbuch anlegen (angepinnt) bzw. seine Nachrichten bearbeiten. Nachrichten anderer
    werden entfernt, damit dort nur die Statistik steht."""
    async with _stats_lock:
        config = await db.get_config(guild.id)
        forum = _channel(guild, config, "logbuch")
        if not isinstance(forum, discord.ForumChannel):
            return
        now = discord.utils.utcnow()
        texts = reportstats.render(await db.report_rows(guild.id),
                                   t("stats_header", when=f"<t:{int(now.timestamp())}:f>"), now.timestamp())
        thread = await _thread_by_id(guild, int(config["stats_thread"])) if config.get("stats_thread") else None
        ids = [int(x) for x in config.get("stats_msgs", "").split(",") if x]
        if thread is None or not ids:
            created = await forum.create_thread(name=t("stats_title"), content=texts[0],
                                                allowed_mentions=discord.AllowedMentions.none(),
                                                reason="GFK-Bot: Vorfall-Statistik")
            thread, ids = created.thread, [created.message.id]
            try:
                await thread.edit(pinned=True)
            except discord.HTTPException:
                pass
        elif thread.archived:
            await thread.edit(archived=False)
        kept = []
        for i, text in enumerate(texts):
            if i < len(ids):
                try:
                    await thread.get_partial_message(ids[i]).edit(content=text,
                                                                  allowed_mentions=discord.AllowedMentions.none())
                    kept.append(ids[i])
                    continue
                except discord.NotFound:
                    if i == 0:                       # Startnachricht weg -> beim nächsten Mal neu anlegen
                        await db.set_config(guild.id, {"stats_thread": None, "stats_msgs": None})
                        return
            message = await thread.send(text, allowed_mentions=discord.AllowedMentions.none())
            kept.append(message.id)
        for extra in ids[len(texts):]:
            try:
                await thread.get_partial_message(extra).delete()
            except discord.HTTPException:
                pass
        async for message in thread.history(limit=100):
            if message.id not in kept and message.id != thread.id:
                try:
                    await message.delete()
                except discord.HTTPException:
                    pass
        STATS_THREADS[guild.id] = thread.id
        await db.set_config(guild.id, {"stats_thread": str(thread.id), "stats_msgs": ",".join(map(str, kept))})


async def cleanup_forum(guild: discord.Guild, now: Optional[dt.datetime] = None, dry_run: bool = False) -> List[str]:
    """Vorfallforum aufräumen; liefert die Titel der gelöschten (bzw. bei dry_run: zu löschenden) Beiträge."""
    config = await db.get_config(guild.id)
    forum = _channel(guild, config, "vorfallforum")
    if not isinstance(forum, discord.ForumChannel):
        return []
    now = now or discord.utils.utcnow()
    threads = list(forum.threads) + [th async for th in forum.archived_threads(limit=None)]
    removed = []
    for thread in threads:
        created = thread.created_at or discord.utils.snowflake_time(thread.id)
        last = discord.utils.snowflake_time(thread.last_message_id) if thread.last_message_id else created
        reason = cleanup_reason([tag.name for tag in thread.applied_tags], created, max(created, last),
                                thread.flags.pinned, now)
        if reason is None:
            continue
        if not dry_run:
            try:
                await thread.delete(reason=f"GFK-Bot: Aufräumen ({reason})")
            except discord.HTTPException as exc:
                log.warning("Beitrag %s nicht löschbar: %s", thread.id, exc)
                continue
        removed.append(f"{thread.name} ({reason})")
    if removed and not dry_run:
        log.info("Vorfallforum aufgeräumt (%s): %s", guild.id, ", ".join(removed))
    return removed


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
        self.bot.add_dynamic_items(DoneButton, ProgressButton)
        self.housekeeping.start()

    async def cog_unload(self):
        panels.HANDLERS.pop("report", None)
        panels.AFTER_POST.pop("report", None)
        self.housekeeping.cancel()

    @tasks.loop(hours=6)
    async def housekeeping(self):
        for guild in self.bot.guilds:
            for job in (cleanup_forum, update_stats):
                try:
                    await job(guild)
                except Exception:
                    log.exception("%s fehlgeschlagen (%s)", job.__name__, guild.id)

    @housekeeping.before_loop
    async def _before_housekeeping(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:                       # Statistik-Beitrag für on_message kennen
            value = (await db.get_config(guild.id)).get("stats_thread")
            if value:
                STATS_THREADS[guild.id] = int(value)
        await asyncio.sleep(120)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Im Beitrag "Vorfall Statistik" stehen nur die Nachrichten des Bots."""
        if message.guild is None or STATS_THREADS.get(message.guild.id) != message.channel.id:
            return
        if message.author.id != self.bot.user.id:
            try:
                await message.delete()
            except discord.HTTPException:
                pass

    async def open_form(self, interaction: discord.Interaction):
        config = await db.get_config(interaction.guild_id)
        if not names.is_internal(status_of(interaction.user, config)):
            await interaction.response.send_message(t("internal_only_report"), ephemeral=True)
            return
        await interaction.response.send_modal(ReportModal())


async def setup(bot: commands.Bot):
    await bot.add_cog(ReportsCog(bot))

"""
GFK-Bot - Eventplanung (Pakete 5-7): allianzweite und private Events, Sprachkanal 1 Stunde vorher, Erinnerungen,
Aufräumen nach dem Ende.

Button "Neues Event planen" im Eventkanal (nur Mitglied, Führung, Admiral) -> Wahl allianzweit/privat -> Formular.
Jedes Event hat eine Karte im Eventkanal und einen Thread (privat: privater Thread nur mit den Eingeladenen).
Allianzweit: Discord-Event (Ort zuerst "extern", 1 h vorher der Sprachkanal), Buttons Teilnehmen/Vielleicht/Abmelden;
bearbeiten und absagen dürfen Ersteller und Führung. Privat: kein Discord-Event bis zum Sprachkanal (der ist nur für
die Teilnehmer sichtbar), Button "Ich möchte mitmachen" für alle anderen; bearbeiten und absagen nur der Ersteller.
Ein Minuten-Task erledigt alles Zeitgesteuerte (eventlogic.due); der Stand liegt in SQLite, nach einem Neustart geht
nichts doppelt oder verloren.
"""
import datetime as dt
import logging
from typing import Dict, List, Optional, Tuple

import discord
from discord.ext import commands, tasks

from gfk import db, eventlogic as el, logfmt, names, settings as st
from gfk.cogs.onboarding import status_of
from gfk.cogs.setup import _channel, _role
from gfk.texts import t
from gfk.util import SafeView, guarded
from gfk.views import panels

log = logging.getLogger("gfk.events")

GOING, MAYBE, OUT, ASKED, DECLINED = "dabei", "vielleicht", "abgemeldet", "angefragt", "abgelehnt"
PINGS = discord.AllowedMentions(users=True, roles=False, everyone=False)
EVERYONE = discord.AllowedMentions(users=False, roles=False, everyone=True)   # nur die Karte allianzweiter Events
VOICE_ALLOW = dict(view_channel=True, connect=True, speak=True)   # nur Rechte, die der Bot selbst hat


def _ts(value: dt.datetime, style: str = "F") -> str:
    return f"<t:{int(value.timestamp())}:{style}>"


def jump(guild_id: int, ev: dict, config: Dict[str, str]) -> str:
    return f"https://discord.com/channels/{guild_id}/{config.get(st.channel_key('events'))}/{ev['message_id']}"


# ----------------- Event-Karte -----------------
BUTTONS = {
    # Aktion: (Text-Schlüssel, Emoji, Stil)
    "join": ("ev_b_join", "✅", discord.ButtonStyle.success),
    "maybe": ("ev_b_maybe", "❔", discord.ButtonStyle.secondary),
    "leave": ("ev_b_leave", "🚪", discord.ButtonStyle.secondary),
    "ask": ("ev_b_ask", "🙋", discord.ButtonStyle.primary),
    "edit": ("ev_b_edit", "✏️", discord.ButtonStyle.secondary),
    "cancel": ("ev_b_cancel", "🗑️", discord.ButtonStyle.danger),
}


class EventButton(discord.ui.DynamicItem[discord.ui.Button],
                  template=r"gfk:ev:(?P<action>join|maybe|leave|ask|edit|cancel):(?P<id>\d+)"):
    def __init__(self, action: str, event_id: int):
        text, emoji, style = BUTTONS[action]
        super().__init__(discord.ui.Button(label=t(text), emoji=emoji, style=style,
                                           custom_id=f"gfk:ev:{action}:{event_id}"))
        self.action, self.event_id = action, event_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match):
        return cls(match["action"], int(match["id"]))

    @guarded
    async def callback(self, interaction: discord.Interaction):
        await interaction.client.get_cog("EventsCog").on_button(interaction, self.action, self.event_id)


class RequestButton(discord.ui.DynamicItem[discord.ui.Button],
                    template=r"gfk:evreq:(?P<act>yes|no):(?P<id>\d+):(?P<user>\d+)"):
    def __init__(self, act: str, event_id: int, user_id: int):
        yes = act == "yes"
        super().__init__(discord.ui.Button(label=t("ev_b_accept") if yes else t("ev_b_decline"),
                                           style=discord.ButtonStyle.success if yes else discord.ButtonStyle.danger,
                                           custom_id=f"gfk:evreq:{act}:{event_id}:{user_id}"))
        self.act, self.event_id, self.user_id = act, event_id, user_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match):
        return cls(match["act"], int(match["id"]), int(match["user"]))

    @guarded
    async def callback(self, interaction: discord.Interaction):
        await interaction.client.get_cog("EventsCog").on_request(interaction, self.act == "yes", self.event_id,
                                                                 self.user_id)


def card(ev: dict, parts: Dict[int, str]) -> Tuple[discord.Embed, Optional[discord.ui.View]]:
    start, end = el.from_iso(ev["start_at"]), el.from_iso(ev["end_at"])
    private, status = ev["type"] == "private", ev["status"]
    title = f"{el.emoji(ev['category'])} {el.title_of(ev)}" + (f" · 🔒 {t('ev_private')}" if private else "")
    color = discord.Color.dark_purple() if private else discord.Color.green()
    if status == "cancelled":
        title, color = f"❌ {t('ev_cancelled')}: {title}", discord.Color.dark_grey()
    elif status in ("ended", "done"):
        title, color = f"✔️ {t('ev_ended')}: {title}", discord.Color.light_grey()
    e = discord.Embed(title=title, color=color)
    e.add_field(name=t("ev_f_kind"), value=f"{el.emoji(ev['category'])} {el.label(ev['category'])}")
    e.add_field(name=t("ev_f_when"), value=f"{_ts(start)}\n{_ts(start, 'R')}")
    e.add_field(name=t("ev_f_duration"), value=el.duration_text(int((end - start).total_seconds() // 60)))
    e.add_field(name=t("ev_f_creator"), value=f"<@{ev['creator_id']}>")
    going = [u for u, s in parts.items() if s == GOING]
    e.add_field(name=t("ev_f_going", n=len(going)), inline=False,
                value=logfmt.clip(" ".join(f"<@{u}>" for u in going)))
    maybe = [u for u, s in parts.items() if s == MAYBE]
    if maybe and not private:
        e.add_field(name=t("ev_f_maybe", n=len(maybe)), inline=False,
                    value=logfmt.clip(" ".join(f"<@{u}>" for u in maybe)))
    if status == "planned":
        e.add_field(name=t("ev_f_voice"),
                    value=f"<#{ev['voice_channel_id']}>" if ev["voice_channel_id"] else t("ev_voice_later"))
    if ev["thread_id"]:
        e.add_field(name=t("ev_f_thread"), value=f"<#{ev['thread_id']}>")
    e.set_footer(text=t("ev_footer", id=ev["id"]))
    if status != "planned":
        return e, None
    view = discord.ui.View(timeout=None)
    for action in (("ask", "edit", "cancel") if private else ("join", "maybe", "leave", "edit", "cancel")):
        view.add_item(EventButton(action, ev["id"]))
    return e, view


# ----------------- Formular -----------------
class EventModal(discord.ui.Modal):
    def __init__(self, cog: "EventsCog", guild: discord.Guild, kind: str, draft: Optional[dict] = None,
                 event_id: Optional[int] = None):
        super().__init__(title=t("ev_modal_edit") if event_id else t(f"ev_modal_{kind}"), timeout=1200)
        self.cog, self.kind, self.event_id = cog, kind, event_id
        draft = draft or {}
        self.category = discord.ui.Select(placeholder=t("ev_cat_placeholder"), options=[
            discord.SelectOption(label=lbl, value=key, emoji=emo, default=draft.get("category") == key)
            for key, (lbl, emo) in el.CATEGORIES.items()])
        self.title_input = discord.ui.TextInput(placeholder=t("ev_title_placeholder"), default=draft.get("title"),
                                                max_length=80)
        self.when = discord.ui.TextInput(placeholder=t("ev_when_placeholder"), default=draft.get("when"), max_length=30)
        self.duration = discord.ui.TextInput(required=False, placeholder=t("ev_duration_placeholder"),
                                             default=draft.get("duration"), max_length=10)
        self.add_item(discord.ui.Label(text=t("ev_f_title"), description=t("ev_title_hint"),
                                       component=self.title_input))
        self.add_item(discord.ui.Label(text=t("ev_f_category"), component=self.category))
        self.add_item(discord.ui.Label(text=t("ev_f_when_input"), description=t("ev_when_hint"), component=self.when))
        self.add_item(discord.ui.Label(text=t("ev_f_duration_input"), description=t("ev_duration_hint"),
                                       component=self.duration))
        self.people = None
        if kind == "private":
            defaults = [m for uid in draft.get("people", []) if (m := guild.get_member(uid))][:25]
            self.people = discord.ui.UserSelect(min_values=1, max_values=25, default_values=defaults,
                                                placeholder=t("ev_people_placeholder"))
            self.add_item(discord.ui.Label(text=t("ev_f_people"), description=t("ev_people_hint"),
                                           component=self.people))

    def draft(self) -> dict:
        return {"title": self.title_input.value, "category": self.category.values[0] if self.category.values else None,
                "when": self.when.value, "duration": self.duration.value,
                "people": [u.id for u in self.people.values] if self.people else []}

    async def on_submit(self, interaction: discord.Interaction):
        draft = self.draft()
        try:
            start = el.parse_when(draft["when"], discord.utils.utcnow())
            minutes = el.parse_duration(draft["duration"])
            if not el.clean_title(draft["title"]):
                raise ValueError("title")
        except ValueError as exc:
            await interaction.response.send_message(
                t(f"ev_bad_{exc}"), ephemeral=True,
                view=RetryView(self.cog, self.kind, draft, self.event_id, interaction.user.id))
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        title = el.clean_title(draft["title"])
        category = draft["category"] or "sonstiges"
        invitees = list(self.people.values) if self.people else []
        if self.event_id:
            ev = await db.get_event(self.event_id)
            if ev is None or ev["status"] != "planned":
                await interaction.followup.send(t("ev_closed"), ephemeral=True)
                return
            if not await self.cog.may_manage(interaction.user, ev):
                await interaction.followup.send(t("ev_manage_denied_" + ev["type"]), ephemeral=True)
                return
            notes = await self.cog.edit_event(interaction.guild, ev, interaction.user, title, category, start,
                                              minutes, invitees if self.people else None)
            text = t("ev_saved")
        else:
            ev, notes = await self.cog.create_event(interaction.guild, interaction.user, self.kind, title, category,
                                                    start, minutes, invitees)
            config = await db.get_config(interaction.guild_id)
            text = t("ev_created", link=jump(interaction.guild_id, ev, config))
        await interaction.followup.send("\n".join([text] + notes), ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        log.exception("Event-Formular fehlgeschlagen", exc_info=error)
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send(t("error"), ephemeral=True)


class RetryView(SafeView):
    """Nach einer ungültigen Eingabe: Formular mit den bisherigen Eingaben erneut öffnen."""

    def __init__(self, cog, kind: str, draft: dict, event_id: Optional[int], user_id: int):
        super().__init__(timeout=900)
        self.cog, self.kind, self.draft, self.event_id, self.user_id = cog, kind, draft, event_id, user_id

    @discord.ui.button(label=t("ev_b_retry"), emoji="✏️", style=discord.ButtonStyle.primary)
    async def again(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EventModal(self.cog, interaction.guild, self.kind, self.draft,
                                                         self.event_id))


class KindView(SafeView):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label=t("ev_b_alliance"), emoji="🌐", style=discord.ButtonStyle.primary)
    async def alliance(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EventModal(self.cog, interaction.guild, "alliance"))

    @discord.ui.button(label=t("ev_b_private"), emoji="🔒", style=discord.ButtonStyle.secondary)
    async def private(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EventModal(self.cog, interaction.guild, "private",
                                                         {"people": [interaction.user.id]}))


class CancelView(SafeView):
    def __init__(self, cog, event_id: int):
        super().__init__(timeout=120)
        self.cog, self.event_id = cog, event_id

    @discord.ui.button(label=t("ev_b_cancel_confirm"), emoji="🗑️", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        ev = await db.get_event(self.event_id)
        if ev is None or ev["status"] != "planned" or not await self.cog.may_manage(interaction.user, ev):
            await interaction.response.edit_message(content=t("ev_closed"), view=None)
            return
        await interaction.response.edit_message(content=t("ev_cancel_done"), view=None)
        await self.cog.cancel_event(interaction.guild, ev, interaction.user)
        self.stop()


# ----------------- Modul -----------------
class EventsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._warned = set()

    async def cog_load(self):
        panels.HANDLERS["event"] = self.open_planner
        panels.AFTER_POST["event"] = self.repost_cards
        self.bot.add_dynamic_items(EventButton, RequestButton)
        self.tick.start()

    async def cog_unload(self):
        panels.HANDLERS.pop("event", None)
        panels.AFTER_POST.pop("event", None)
        self.tick.cancel()

    # ---------- Hilfen ----------
    async def _thread(self, guild: discord.Guild, thread_id: Optional[int]) -> Optional[discord.Thread]:
        if not thread_id:
            return None
        thread = guild.get_thread(thread_id)
        if thread is None:
            try:
                thread = await guild.fetch_channel(thread_id)
            except discord.HTTPException:
                return None
        return thread if isinstance(thread, discord.Thread) else None

    async def _scheduled(self, guild: discord.Guild, ev: dict) -> Optional[discord.ScheduledEvent]:
        if not ev["discord_event_id"]:
            return None
        try:
            return guild.get_scheduled_event(ev["discord_event_id"]) or \
                await guild.fetch_scheduled_event(ev["discord_event_id"])
        except discord.HTTPException:
            return None

    async def _describe(self, guild: discord.Guild, ev: dict, thread: Optional[discord.Thread]):
        """Discord-Event: Link zum Thread in die Beschreibung (das Event selbst kann nicht auf einen Thread zeigen)."""
        sev = await self._scheduled(guild, ev)
        if sev is None or thread is None:
            return
        try:
            await sev.edit(description=t("ev_discord_desc", thread=thread.mention, url=thread.jump_url))
        except discord.HTTPException as exc:
            log.info("Beschreibung von Discord-Event %s nicht setzbar: %s", sev.id, exc)

    async def update_card(self, guild: discord.Guild, ev: dict):
        config = await db.get_config(guild.id)
        channel = _channel(guild, config, "events")
        if channel is None or not ev["message_id"]:
            return
        embed, view = card(ev, await db.participants(ev["id"]))
        try:
            await channel.get_partial_message(ev["message_id"]).edit(embed=embed, view=view)
        except discord.NotFound:
            log.info("Karte von Event %s fehlt", ev["id"])

    async def _post(self, guild: discord.Guild, ev: dict, text: str, ping: List[int] = ()):
        """Nachricht in den Thread des Events, Erwähnungen auf mehrere Nachrichten verteilt."""
        thread = await self._thread(guild, ev["thread_id"])
        if thread is None:
            return
        try:
            if not ping:
                await thread.send(text, allowed_mentions=discord.AllowedMentions.none())
                return
            for chunk in el.mention_chunks(ping, prefix=text + "\n"):
                await thread.send(chunk, allowed_mentions=PINGS)
        except discord.HTTPException as exc:
            log.warning("Thread von Event %s nicht beschreibbar: %s", ev["id"], exc)

    async def may_manage(self, member: discord.Member, ev: dict) -> bool:
        """Allianzweit: Ersteller und Führung (inkl. Admiral). Privat: nur der Ersteller."""
        if member.id == ev["creator_id"]:
            return True
        if ev["type"] == "private":
            return False
        return names.is_lead(status_of(member, await db.get_config(member.guild.id)))

    async def _internal(self, interaction: discord.Interaction) -> bool:
        if names.is_internal(status_of(interaction.user, await db.get_config(interaction.guild_id))):
            return True
        await interaction.response.send_message(t("internal_only_event"), ephemeral=True)
        return False

    @staticmethod
    def _going(parts: Dict[int, str], private: bool) -> List[int]:
        return [u for u, s in parts.items() if s == GOING or (s == MAYBE and not private)]

    def _filter_invitees(self, guild: discord.Guild, config: Dict[str, str], creator: discord.abc.User,
                         invitees) -> Tuple[List[discord.Member], List[str]]:
        ok, skipped = [], []
        for user in invitees:
            member = guild.get_member(user.id)
            if member is None or member.bot or member.id == creator.id:
                continue
            if names.is_internal(status_of(member, config)):
                ok.append(member)
            else:
                skipped.append(member.mention)
        return ok, skipped

    # ---------- Planen ----------
    async def open_planner(self, interaction: discord.Interaction):
        if not await self._internal(interaction):
            return
        await interaction.response.send_message(t("ev_choose_kind"), view=KindView(self), ephemeral=True)

    async def create_event(self, guild: discord.Guild, creator: discord.Member, kind: str, title: str,
                           category: str, start: dt.datetime, minutes: int,
                           invitees=()) -> Tuple[dict, List[str]]:
        config = await db.get_config(guild.id)
        channel = _channel(guild, config, "events")
        if not isinstance(channel, discord.TextChannel):
            raise ValueError("no_events_channel")
        now = discord.utils.utcnow()
        end = start + dt.timedelta(minutes=minutes)
        notes = []
        event_id = await db.create_event(guild.id, kind, title, category, el.iso(start), el.iso(end), "",
                                         creator.id, el.initial_reminded(start, now, st.reminder_minutes(config)))
        await db.set_participant(event_id, creator.id, GOING)
        members, skipped = self._filter_invitees(guild, config, creator, invitees)
        for m in members:
            await db.set_participant(event_id, m.id, GOING)
        if skipped:
            notes.append(t("ev_skipped", users=", ".join(skipped)))
        fields = {}
        if kind == "alliance":
            try:
                sev = await guild.create_scheduled_event(
                    name=el.event_name(title), start_time=start, end_time=end,
                    entity_type=discord.EntityType.external, location=t("ev_location_pending"),
                    privacy_level=discord.PrivacyLevel.guild_only, reason=f"GFK-Bot: Event von {creator}")
                fields["discord_event_id"] = sev.id
            except discord.HTTPException as exc:
                log.warning("Discord-Event nicht anlegbar: %s", exc)
                notes.append(t("ev_no_discord_event"))
        ev = await db.get_event(event_id)
        embed, view = card(ev, await db.participants(event_id))
        if kind == "alliance":
            # #events sehen nur Mitglieder, Führung und Admiral - @everyone erreicht also nur die Allianz
            message = await channel.send(t("ev_everyone", title=title, when=_ts(start)), embed=embed, view=view,
                                         allowed_mentions=EVERYONE)
        else:
            message = await channel.send(embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none())
        fields["message_id"] = message.id
        name = el.thread_name(category, title)
        try:
            if kind == "alliance":
                thread = await message.create_thread(name=name, auto_archive_duration=10080)
            else:
                thread = await channel.create_thread(name=name, type=discord.ChannelType.private_thread,
                                                     invitable=False, auto_archive_duration=10080)
                for uid in [creator.id] + [m.id for m in members]:
                    await thread.add_user(discord.Object(uid))
            fields["thread_id"] = thread.id
        except discord.HTTPException as exc:
            log.warning("Thread für Event %s nicht anlegbar: %s", event_id, exc)
            thread = None
            notes.append(t("ev_no_thread"))
        await db.update_event(event_id, **fields)
        ev = await db.get_event(event_id)
        await self.update_card(guild, ev)
        await self._describe(guild, ev, thread)
        if thread is not None:
            intro = t("ev_intro_" + kind, creator=creator.mention, when=_ts(start), card=message.jump_url)
            if kind == "private":
                await self._post(guild, ev, intro, [m.id for m in members])
            else:
                await self._post(guild, ev, intro)
        return ev, notes

    async def edit_event(self, guild: discord.Guild, ev: dict, actor: discord.Member, title: str, category: str,
                         start: dt.datetime, minutes: int, invitees=None) -> List[str]:
        config = await db.get_config(guild.id)
        now = discord.utils.utcnow()
        end = start + dt.timedelta(minutes=minutes)
        old_start, old_end = el.from_iso(ev["start_at"]), el.from_iso(ev["end_at"])
        time_changed = start != old_start or end != old_end
        fields = {"title": title, "category": category, "start_at": el.iso(start), "end_at": el.iso(end)}
        notes = []
        vc = guild.get_channel(ev["voice_channel_id"]) if ev["voice_channel_id"] else None
        if time_changed:
            fields["reminded"] = el.initial_reminded(start, now, st.reminder_minutes(config))
            if vc is not None and now < start - el.VOICE_LEAD and not vc.members:
                await self._delete_channel(vc)                    # weit verschoben: Sprachkanal kommt neu
                vc, fields["voice_channel_id"] = None, None
        await db.update_event(ev["id"], **fields)
        parts = await db.participants(ev["id"])
        thread = await self._thread(guild, ev["thread_id"])
        added: List[int] = []
        if invitees is not None and ev["type"] == "private":
            members, skipped = self._filter_invitees(guild, config, actor, invitees)
            wanted = {m.id for m in members} | {ev["creator_id"]}
            for m in members:
                if parts.get(m.id) != GOING:
                    await db.set_participant(ev["id"], m.id, GOING)
                    added.append(m.id)
                    await self._grant(thread, vc, m)
            for uid, state in parts.items():
                if state == GOING and uid not in wanted:
                    await db.set_participant(ev["id"], uid, None)
                    await self._revoke(guild, thread, vc, uid)
            if skipped:
                notes.append(t("ev_skipped", users=", ".join(skipped)))
        ev = await db.get_event(ev["id"])
        sev = await self._scheduled(guild, ev)
        if sev is not None and sev.status == discord.EventStatus.scheduled:
            kwargs = dict(name=el.event_name(title), start_time=start, end_time=end)
            if sev.entity_type == discord.EntityType.voice and vc is None:
                kwargs.update(entity_type=discord.EntityType.external, location=t("ev_location_pending"), channel=None)
            try:
                await sev.edit(**kwargs)
            except discord.HTTPException as exc:
                log.warning("Discord-Event %s nicht änderbar: %s", sev.id, exc)
        if thread is not None:
            try:
                await thread.edit(name=el.thread_name(category, title))
            except discord.HTTPException:
                pass
        if vc is not None:
            try:
                await vc.edit(name=el.voice_name(title))
            except discord.HTTPException:
                pass
        await self.update_card(guild, ev)
        text = t("ev_changed", user=actor.mention, when=_ts(start))
        parts = await db.participants(ev["id"])
        ping = self._going(parts, ev["type"] == "private") if time_changed else added
        await self._post(guild, ev, text, [u for u in ping if u != actor.id])
        return notes

    async def cancel_event(self, guild: discord.Guild, ev: dict, actor: discord.Member):
        await db.update_event(ev["id"], status="cancelled", voice_channel_id=None)
        if ev["voice_channel_id"]:
            await self._delete_channel(guild.get_channel(ev["voice_channel_id"]))
        sev = await self._scheduled(guild, ev)
        if sev is not None:
            try:
                await sev.delete()
            except discord.HTTPException:
                pass
        ev = await db.get_event(ev["id"])
        await self.update_card(guild, ev)
        parts = await db.participants(ev["id"])
        await self._post(guild, ev, t("ev_cancelled_note", user=actor.mention),
                         [u for u in self._going(parts, ev["type"] == "private") if u != actor.id])

    # ---------- Buttons ----------
    async def on_button(self, interaction: discord.Interaction, action: str, event_id: int):
        if not await self._internal(interaction):
            return
        ev = await db.get_event(event_id)
        if ev is None or ev["status"] != "planned":
            await interaction.response.send_message(t("ev_closed"), ephemeral=True)
            return
        user = interaction.user
        if action in ("join", "maybe", "leave"):
            state = {"join": GOING, "maybe": MAYBE, "leave": OUT}[action]
            await db.set_participant(event_id, user.id, state)
            await interaction.response.send_message(t(f"ev_{action}_done"), ephemeral=True)
            await self.update_card(interaction.guild, ev)
        elif action == "ask":
            await self.ask(interaction, ev)
        elif action == "edit":
            if not await self.may_manage(user, ev):
                await interaction.response.send_message(t("ev_manage_denied_" + ev["type"]), ephemeral=True)
                return
            parts = await db.participants(event_id)
            start, end = el.from_iso(ev["start_at"]), el.from_iso(ev["end_at"])
            draft = {"title": el.title_of(ev), "category": ev["category"],
                     "when": el.input_value(start),
                     "duration": el.duration_input(int((end - start).total_seconds() // 60)),
                     "people": [u for u, s in parts.items() if s == GOING]}
            await interaction.response.send_modal(EventModal(self, interaction.guild, ev["type"], draft, event_id))
        elif action == "cancel":
            if not await self.may_manage(user, ev):
                await interaction.response.send_message(t("ev_manage_denied_" + ev["type"]), ephemeral=True)
                return
            await interaction.response.send_message(t("ev_cancel_confirm"), view=CancelView(self, event_id),
                                                    ephemeral=True)

    async def ask(self, interaction: discord.Interaction, ev: dict):
        """Privates Event: Anfrage eines nicht eingeladenen Mitglieds an den Ersteller (im privaten Thread)."""
        if interaction.user.id == ev["creator_id"]:
            await interaction.response.send_message(t("ev_ask_creator"), ephemeral=True)
            return
        state = (await db.participants(ev["id"])).get(interaction.user.id)
        if state == GOING:
            await interaction.response.send_message(t("ev_ask_already_in"), ephemeral=True)
            return
        if state == ASKED:
            await interaction.response.send_message(t("ev_ask_pending"), ephemeral=True)
            return
        thread = await self._thread(interaction.guild, ev["thread_id"])
        if thread is None:
            await interaction.response.send_message(t("error"), ephemeral=True)
            return
        await db.set_participant(ev["id"], interaction.user.id, ASKED)
        view = discord.ui.View(timeout=None)
        view.add_item(RequestButton("yes", ev["id"], interaction.user.id))
        view.add_item(RequestButton("no", ev["id"], interaction.user.id))
        await thread.send(t("ev_ask_msg", creator=f"<@{ev['creator_id']}>", user=interaction.user.mention),
                          view=view, allowed_mentions=discord.AllowedMentions(users=[discord.Object(ev["creator_id"])]))
        await interaction.response.send_message(t("ev_ask_sent"), ephemeral=True)

    async def on_request(self, interaction: discord.Interaction, accept: bool, event_id: int, user_id: int):
        ev = await db.get_event(event_id)
        if ev is None or ev["status"] != "planned":
            await interaction.response.edit_message(view=None)
            return
        if interaction.user.id != ev["creator_id"]:
            await interaction.response.send_message(t("ev_request_denied"), ephemeral=True)
            return
        guild = interaction.guild
        member = guild.get_member(user_id)
        if member is None:
            await interaction.response.edit_message(content=t("status_gone"), view=None)
            return
        if accept:
            await db.set_participant(event_id, user_id, GOING)
            vc = guild.get_channel(ev["voice_channel_id"]) if ev["voice_channel_id"] else None
            await self._grant(interaction.channel if isinstance(interaction.channel, discord.Thread) else None, vc,
                              member)
            text = t("ev_request_accepted", user=member.mention, creator=interaction.user.mention)
        else:
            await db.set_participant(event_id, user_id, DECLINED)
            text = t("ev_request_declined", user=member.mention)
            try:
                await member.send(t("ev_request_declined_dm", creator=interaction.user.display_name,
                                    card=jump(guild.id, ev, await db.get_config(guild.id))))
            except discord.HTTPException:
                pass
        await interaction.response.edit_message(content=text, view=None,
                                                allowed_mentions=discord.AllowedMentions.none())
        await self.update_card(guild, ev)

    async def _grant(self, thread: Optional[discord.Thread], vc, member: discord.Member):
        if thread is not None:
            try:
                await thread.add_user(member)
            except discord.HTTPException as exc:
                log.warning("Thread %s: %s nicht hinzufügbar: %s", thread.id, member.id, exc)
        if vc is not None:
            try:
                await vc.set_permissions(member, **VOICE_ALLOW, reason="GFK-Bot: Teilnehmer")
            except discord.HTTPException as exc:
                log.warning("Sprachkanal %s: Recht für %s nicht setzbar: %s", vc.id, member.id, exc)

    async def _revoke(self, guild: discord.Guild, thread: Optional[discord.Thread], vc, user_id: int):
        if thread is not None:
            try:
                await thread.remove_user(discord.Object(user_id))
            except discord.HTTPException:
                pass
        member = guild.get_member(user_id)
        if vc is not None and member is not None:
            try:
                await vc.set_permissions(member, overwrite=None, reason="GFK-Bot: kein Teilnehmer mehr")
            except discord.HTTPException:
                pass

    # ---------- Zeitgesteuert ----------
    @tasks.loop(minutes=1)
    async def tick(self):
        now = discord.utils.utcnow()
        for guild in self.bot.guilds:
            config = await db.get_config(guild.id)
            for ev in await db.active_events(guild.id):
                try:
                    await self.process(guild, config, ev, now)
                except Exception:
                    log.exception("Event %s: Verarbeitung fehlgeschlagen", ev["id"])

    @tick.before_loop
    async def _before_tick(self):
        await self.bot.wait_until_ready()

    def _due(self, ev: dict, now: dt.datetime, config: Dict[str, str]):
        return el.due(el.from_iso(ev["start_at"]), el.from_iso(ev["end_at"]), ev["status"],
                      bool(ev["voice_channel_id"]), ev["reminded"], now, st.reminder_minutes(config))

    async def process(self, guild: discord.Guild, config: Dict[str, str], ev: dict, now: dt.datetime):
        actions = self._due(ev, now, config)
        if "end" in actions:
            await self.finish(guild, ev)
            ev = await db.get_event(ev["id"])
            actions = self._due(ev, now, config)
        if "voice" in actions:
            await self.open_voice(guild, config, ev)
            ev = await db.get_event(ev["id"])
        if "start" in actions or "remind" in actions:
            await self.announce(guild, config, ev, "start" if "start" in actions else "remind")
        if "cleanup" in actions:
            await self.cleanup(guild, ev)

    async def open_voice(self, guild: discord.Guild, config: Dict[str, str], ev: dict):
        category = _channel(guild, config, "event_kategorie")
        if not isinstance(category, discord.CategoryChannel):
            if guild.id not in self._warned:
                self._warned.add(guild.id)
                log.warning("Keine Event-Kategorie eingerichtet (%s) - kein Sprachkanal", guild.id)
            return
        start, end = el.from_iso(ev["start_at"]), el.from_iso(ev["end_at"])
        overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False),
                      guild.me: discord.PermissionOverwrite(manage_channels=True, **VOICE_ALLOW)}
        if ev["type"] == "private":
            for uid, state in (await db.participants(ev["id"])).items():
                if state == GOING and (m := guild.get_member(uid)):
                    overwrites[m] = discord.PermissionOverwrite(**VOICE_ALLOW)
        else:
            for key in names.INTERNAL:
                if role := _role(guild, config, key):
                    overwrites[role] = discord.PermissionOverwrite(**VOICE_ALLOW)
        vc = await category.create_voice_channel(el.voice_name(el.title_of(ev)), overwrites=overwrites,
                                                 reason=f"GFK-Bot: Event {ev['id']}")
        await db.update_event(ev["id"], voice_channel_id=vc.id)
        sev = await self._scheduled(guild, ev)
        try:
            if sev is not None and sev.status == discord.EventStatus.scheduled:
                await sev.edit(channel=vc, entity_type=discord.EntityType.voice)
            elif ev["type"] == "private" and sev is None and start > discord.utils.utcnow() + dt.timedelta(minutes=2):
                # Event im privaten Sprachkanal: nur für die Teilnehmer sichtbar (Kanalrechte)
                sev = await guild.create_scheduled_event(
                    name=el.event_name(el.title_of(ev)), start_time=start, end_time=end,
                    entity_type=discord.EntityType.voice, channel=vc, privacy_level=discord.PrivacyLevel.guild_only,
                    reason=f"GFK-Bot: Event {ev['id']}")
                await db.update_event(ev["id"], discord_event_id=sev.id)
                await self._describe(guild, await db.get_event(ev["id"]), await self._thread(guild, ev["thread_id"]))
        except discord.HTTPException as exc:
            log.warning("Discord-Event zu Event %s nicht umstellbar: %s", ev["id"], exc)
        ev = await db.get_event(ev["id"])
        await self.update_card(guild, ev)
        await self._post(guild, ev, t("ev_voice_ready", voice=vc.mention))

    async def announce(self, guild: discord.Guild, config: Dict[str, str], ev: dict, kind: str):
        start = el.from_iso(ev["start_at"])
        bits = ev["reminded"] | el.REMIND_BIT | (el.START_BIT if kind == "start" else 0)
        await db.update_event(ev["id"], reminded=bits)            # zuerst merken: nie doppelt
        voice = f"<#{ev['voice_channel_id']}>" if ev["voice_channel_id"] else t("ev_no_voice")
        text = t("ev_start_msg", voice=voice) if kind == "start" else \
            t("ev_remind_msg", when=_ts(start, "R"), voice=voice)
        parts = await db.participants(ev["id"])
        await self._post(guild, ev, text, self._going(parts, ev["type"] == "private"))
        if kind == "start":
            sev = await self._scheduled(guild, ev)
            if sev is not None and sev.status == discord.EventStatus.scheduled:
                try:
                    await sev.start()
                except discord.HTTPException as exc:
                    log.info("Discord-Event %s nicht startbar: %s", sev.id, exc)

    async def finish(self, guild: discord.Guild, ev: dict):
        await db.update_event(ev["id"], status="ended")
        sev = await self._scheduled(guild, ev)
        if sev is not None:
            try:
                if sev.status == discord.EventStatus.active:
                    await sev.end()
                elif sev.status == discord.EventStatus.scheduled:
                    await sev.delete()
            except discord.HTTPException:
                pass
        await self.update_card(guild, await db.get_event(ev["id"]))

    async def cleanup(self, guild: discord.Guild, ev: dict):
        """Vorbei: Sprachkanal (erst wenn leer), Karte und Thread entfernen."""
        vc = guild.get_channel(ev["voice_channel_id"]) if ev["voice_channel_id"] else None
        if vc is not None and getattr(vc, "members", None):
            return                                        # es wird noch gesprochen - beim Verlassen erneut
        await self._delete_channel(vc)
        config = await db.get_config(guild.id)
        channel = _channel(guild, config, "events")
        if channel is not None and ev["message_id"]:
            try:
                await channel.get_partial_message(ev["message_id"]).delete()
            except discord.HTTPException:
                pass
        thread = await self._thread(guild, ev["thread_id"])
        if thread is not None:
            try:
                await thread.delete()
            except discord.HTTPException:
                pass
        await db.update_event(ev["id"], status="done", voice_channel_id=None)

    async def _delete_channel(self, channel):
        if channel is None:
            return
        try:
            await channel.delete(reason="GFK-Bot: Event vorbei")
        except discord.HTTPException as exc:
            log.warning("Kanal %s nicht löschbar: %s", channel.id, exc)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        channel = before.channel
        if channel is None or channel == after.channel or channel.members:
            return
        ev = await db.event_by_voice(channel.id)
        if ev and ev["status"] in ("ended", "cancelled") and discord.utils.utcnow() >= el.from_iso(ev["end_at"]):
            await self.cleanup(member.guild, ev)

    # ---------- /setup panels ----------
    async def repost_cards(self, guild: discord.Guild, newly_posted: bool):
        """Neue Planungs-Nachricht: die aktuellen Karten darunter neu posten (früheste zuerst)."""
        if not newly_posted:
            return
        config = await db.get_config(guild.id)
        channel = _channel(guild, config, "events")
        if channel is None:
            return
        for ev in await db.active_events(guild.id):
            if ev["message_id"]:
                try:
                    await channel.get_partial_message(ev["message_id"]).delete()
                except discord.HTTPException:
                    pass
            embed, view = card(ev, await db.participants(ev["id"]))
            message = await channel.send(embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none())
            await db.update_event(ev["id"], message_id=message.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(EventsCog(bot))

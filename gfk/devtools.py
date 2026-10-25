"""
GFK-Bot - Werkzeug für den Test-Server (nur mit GFK_DEV_GUILD, nie auf dem echten Server).

    python -m gfk.devtools seed     # Kanäle der Kategorie "gfk-bot" zuordnen, fehlende Rollen/Verwaltung/Logs anlegen
    python -m gfk.devtools status   # Prüfung wie /setup anzeigen
    python -m gfk.devtools panels   # feste Nachrichten posten bzw. aktualisieren
    python -m gfk.devtools selftest # Meldung + Events gegen den Test-Server durchspielen (Test-Bot vorher stoppen!)

Kanalnamen auf dem Test-Server: lobby = Eingang, event = Events, report = Meldungen, reports (Forum) = Vorfallforum;
Sprachkanäle der Events in derselben Kategorie.
"""
import asyncio
import datetime as dt
import os
import re
import sys

import discord

from gfk import db, eventlogic as el, settings as st
from gfk.cogs.setup import post_panels, status_lines

CATEGORY = "gfk-bot"
CHANNEL_NAMES = {"lobby": "eingang", "event": "events", "report": "meldungen", "reports": "vorfallforum",
                 "reportsforum": "vorfallforum"}
VERWALTUNG_NAMES = ["verwaltung", "gfk-verwaltung", "gfk-log"]   # gfk-log = alter Name auf dem Test-Server
ROLE_ORDER = ["Admiral", "Führung", "Mitglied", "Freund", "Gast"]
ROLE_TO_KEY = {"Admiral": "admiral", "Führung": "fuehrung", "Mitglied": "mitglied", "Freund": "freund", "Gast": "gast"}


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


async def seed(guild: discord.Guild):
    cat = next((c for c in guild.categories if _norm(c.name) == _norm(CATEGORY)), None)
    if cat is None:
        raise SystemExit(f"Kategorie {CATEGORY!r} nicht gefunden")
    values = {st.channel_key("event_kategorie"): str(cat.id)}
    for ch in cat.channels:
        key = CHANNEL_NAMES.get(_norm(ch.name))
        if key:
            values[st.channel_key(key)] = str(ch.id)
            print(f"  Kanal #{ch.name} -> {st.CHANNEL_KEYS[key]}")
    verw = next((c for c in cat.text_channels if c.name in VERWALTUNG_NAMES), None)
    if verw is None:
        verw = await cat.create_text_channel("verwaltung", reason="GFK-Test: Verwaltung")
    elif verw.name != "verwaltung":
        await verw.edit(name="verwaltung", reason="GFK-Test: Verwaltung statt Log-Kanal")
    values[st.channel_key("verwaltung")] = str(verw.id)
    values[st.channel_key("log")] = None
    print(f"  Kanal #verwaltung -> Verwaltung")
    hidden = {guild.default_role: discord.PermissionOverwrite(view_channel=False),
              guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True)}
    for key, name in st.LOG_KEYS.items():
        ch = next((c for c in cat.text_channels if c.name == name), None)
        if ch is None:
            ch = await cat.create_text_channel(name, overwrites=hidden, reason="GFK-Test: Server-Log")
        values[st.channel_key(key)] = str(ch.id)
        print(f"  Kanal #{name} -> {name}")
    existing = {r.name: r for r in guild.roles}
    for name in ROLE_ORDER:
        role = existing.get(name) or await guild.create_role(name=name, reason="GFK-Test: Status-Rolle")
        values[st.role_key(ROLE_TO_KEY[name])] = str(role.id)
    # Reihenfolge direkt unter der höchsten Rolle des Bots: Admiral oben, Gast unten
    top = guild.me.top_role.position
    positions = {guild.get_role(int(values[st.role_key(ROLE_TO_KEY[n])])): top - 1 - i for i, n in enumerate(ROLE_ORDER)}
    await guild.edit_role_positions(positions={r: max(1, p) for r, p in positions.items()}, reason="GFK-Test")
    print("  Rollen:", ", ".join(ROLE_ORDER))
    await db.set_config(guild.id, values)
    from gfk.cogs.reports import ensure_tags, missing_tags
    await ensure_tags(guild)
    forum = guild.get_channel(int(values.get(st.channel_key("vorfallforum"), 0) or 0))
    if isinstance(forum, discord.ForumChannel):
        forum = await guild.fetch_channel(forum.id)
        print("  Forum-Tags fehlen:", missing_tags(forum) or "keine")


class Check:
    def __init__(self):
        self.ok = self.bad = 0

    def __call__(self, cond, text):
        print(("  ✅ " if cond else "  ❌ ") + text)
        self.ok += bool(cond)
        self.bad += not cond


async def selftest(client: discord.Client, guild: discord.Guild):
    """Ablauf ohne Klicks: Meldung anlegen und erledigen; allianzweites und privates Event mit vorgespulter Uhr."""
    from gfk.cogs import reports
    from gfk.cogs.events import EventsCog
    check = Check()
    me = guild.me
    config = await db.get_config(guild.id)
    print("Meldung:")
    thread, skipped = await reports.create_report(guild, me, "roe", "TST", "Selbsttest-Spieler",
                                                  "Automatischer Selbsttest - wird gleich wieder gelöscht.")
    check(thread is not None and not skipped, f"Beitrag angelegt: {thread.name}")
    check({t.name for t in thread.applied_tags} == {"ROE-Verstoß", "Offen"}, "Tags ROE-Verstoß + Offen")
    starter = await thread.fetch_message(thread.id)
    lead = guild.get_role(int(config[st.role_key("fuehrung")]))
    check(lead in starter.role_mentions, "Führung erwähnt")
    check(bool(starter.components), "Button Erledigt vorhanden")
    rid = int(starter.embeds[0].footer.text.split("#")[1])
    check(await db.close_report(rid, me.id), "in der DB erledigt")
    check(not await db.close_report(rid, me.id), "zweites Erledigt wird abgelehnt")
    await reports.finish_report(starter, rid, me)
    thread = await guild.fetch_channel(thread.id)
    check({t.name for t in thread.applied_tags} == {"ROE-Verstoß", "Erledigt"}, "Tag jetzt Erledigt")
    check(thread.archived, "Beitrag archiviert")
    await thread.delete()
    await db.delete_report(rid)

    cog = EventsCog(client)
    now = discord.utils.utcnow().replace(second=0, microsecond=0)
    start = now + dt.timedelta(minutes=90)
    print("Allianzweites Event:")
    ev, notes = await cog.create_event(guild, me, "alliance", "Selbsttest Armada", "armada", start, 60)
    check(not notes, f"angelegt (#{ev['id']}) {notes or ''}")
    check(ev["message_id"] and ev["thread_id"] and ev["discord_event_id"], "Karte, Thread, Discord-Event")
    sev = await guild.fetch_scheduled_event(ev["discord_event_id"])
    check(sev.entity_type == discord.EntityType.external, "Discord-Event zuerst extern")
    edited = start + dt.timedelta(minutes=10)
    await cog.edit_event(guild, ev, me, "Selbsttest Welle", "welle", edited, 45)
    ev = await db.get_event(ev["id"])
    sev = await guild.fetch_scheduled_event(ev["discord_event_id"])
    check(el.from_iso(ev["start_at"]) == edited and sev.start_time == edited, "Zeit geändert (DB + Discord-Event)")
    check(sev.name == "Selbsttest Welle", f"Discord-Event heißt wie der Titel: {sev.name}")
    thread = await guild.fetch_channel(ev["thread_id"])
    check(thread.name == "🌊 Selbsttest Welle", f"Thread heißt wie der Titel: {thread.name}")
    start, end = edited, edited + dt.timedelta(minutes=45)
    await cog.process(guild, config, ev, now)
    ev = await db.get_event(ev["id"])
    check(not ev["voice_channel_id"], "jetzt noch kein Sprachkanal")
    await cog.process(guild, config, ev, start - dt.timedelta(minutes=59))
    ev = await db.get_event(ev["id"])
    vc = guild.get_channel(ev["voice_channel_id"] or 0)
    check(vc is not None and vc.category_id == int(config[st.channel_key("event_kategorie")]),
          f"Sprachkanal 1 h vorher: {vc.name if vc else '-'}")
    check(vc is not None and vc.name == "🔊 Selbsttest Welle", "Sprachkanal heißt wie der Titel")
    sev = await guild.fetch_scheduled_event(ev["discord_event_id"])
    check(sev.entity_type == discord.EntityType.voice and sev.channel_id == ev["voice_channel_id"],
          "Discord-Event auf den Sprachkanal umgestellt")
    check(vc is not None and not vc.permissions_for(guild.default_role).view_channel, "@everyone sieht ihn nicht")
    await cog.process(guild, config, ev, start - dt.timedelta(minutes=st.reminder_minutes(config) - 1))
    ev = await db.get_event(ev["id"])
    check(ev["reminded"] & el.REMIND_BIT, "Erinnerung gesendet")
    await cog.process(guild, config, ev, start - dt.timedelta(minutes=st.reminder_minutes(config) - 2))
    check((await db.get_event(ev["id"]))["reminded"] == el.REMIND_BIT, "keine doppelte Erinnerung")
    await cog.process(guild, config, ev, start + dt.timedelta(minutes=1))
    ev = await db.get_event(ev["id"])
    check(ev["reminded"] & el.START_BIT, "Start-Hinweis gesendet")
    sev = await guild.fetch_scheduled_event(ev["discord_event_id"])
    check(sev.status == discord.EventStatus.active, "Discord-Event gestartet")
    thread = await guild.fetch_channel(ev["thread_id"])
    texts = [m.content async for m in thread.history(limit=20)]
    check(any("Erinnerung" in x for x in texts) and any("Es geht los" in x for x in texts),
          "Erinnerung + Start im Thread")
    await cog.process(guild, config, ev, end + dt.timedelta(minutes=1))
    ev = await db.get_event(ev["id"])
    check(ev["status"] == "done", f"nach dem Ende aufgeräumt (Status {ev['status']})")
    check(guild.get_channel(vc.id) is None, "Sprachkanal gelöscht")
    try:
        await guild.fetch_channel(ev["thread_id"])
        check(False, "Thread gelöscht")
    except discord.NotFound:
        check(True, "Thread gelöscht")

    print("Privates Event:")
    start = now + dt.timedelta(minutes=45)
    ev, notes = await cog.create_event(guild, me, "private", "Selbsttest privat", "sonstiges", start, 30)
    check(ev["thread_id"] and not ev["discord_event_id"], "Karte + privater Thread, noch kein Discord-Event")
    thread = await guild.fetch_channel(ev["thread_id"])
    check(thread.type == discord.ChannelType.private_thread, "Thread ist privat")
    await cog.process(guild, config, ev, now)
    ev = await db.get_event(ev["id"])
    vc = guild.get_channel(ev["voice_channel_id"] or 0)
    check(vc is not None, "Sprachkanal sofort (weniger als 1 h vor Beginn)")
    check(vc is not None and not vc.permissions_for(guild.default_role).view_channel, "privater Sprachkanal versteckt")
    check(bool(ev["discord_event_id"]), "Discord-Event im privaten Sprachkanal")
    await cog.cancel_event(guild, ev, me)
    ev = await db.get_event(ev["id"])
    check(ev["status"] == "cancelled" and guild.get_channel(vc.id) is None, "abgesagt: Sprachkanal sofort weg")
    try:
        await guild.fetch_scheduled_event(ev["discord_event_id"])
        check(False, "Discord-Event gelöscht")
    except discord.NotFound:
        check(True, "Discord-Event gelöscht")
    await cog.process(guild, config, ev, start + dt.timedelta(minutes=31))
    check((await db.get_event(ev["id"]))["status"] == "done", "abgesagtes Event nach dem Ende aufgeräumt")
    print(f"Selbsttest: {check.ok} ok, {check.bad} Fehler")


async def run(command: str):
    guild_id = int(os.environ["GFK_DEV_GUILD"])
    client = discord.Client(intents=discord.Intents(guilds=True, members=True, voice_states=True))
    done = asyncio.Event()

    @client.event
    async def on_ready():
        try:
            guild = client.get_guild(guild_id)
            if command == "seed":
                await seed(guild)
            elif command == "selftest":
                await selftest(client, guild)
            elif command == "panels":
                posted, missing = await post_panels(guild)
                print("  gepostet:", posted, "| fehlt:", missing)
            lines = status_lines(guild, await db.get_config(guild.id))
            print("Prüfung:", "alles eingerichtet" if not lines else "")
            for line in lines:
                print("  -", line)
        finally:
            done.set()

    async with client:
        task = asyncio.create_task(client.start(os.environ["DISCORD_TOKEN"]))
        await done.wait()
        await client.close()
        task.cancel()


if __name__ == "__main__":
    if not os.environ.get("GFK_DEV_GUILD"):
        raise SystemExit("Nur für den Test-Server: GFK_DEV_GUILD fehlt")
    db.init()
    asyncio.run(run(sys.argv[1] if len(sys.argv) > 1 else "status"))

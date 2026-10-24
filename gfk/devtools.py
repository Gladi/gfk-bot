"""
GFK-Bot - Werkzeug für den Test-Server (nur mit GFK_DEV_GUILD, nie auf dem echten Server).

    python -m gfk.devtools seed     # Kanäle der Kategorie "gfk-bot" zuordnen, fehlende Rollen/Log-Kanal anlegen
    python -m gfk.devtools status   # Prüfung wie /setup anzeigen
    python -m gfk.devtools panels   # feste Nachrichten posten bzw. aktualisieren

Kanalnamen auf dem Test-Server: lobby = Eingang, event = Events, report = Meldungen, reports (Forum) = Vorfallforum;
Sprachkanäle der Events in derselben Kategorie.
"""
import asyncio
import os
import re
import sys

import discord

from gfk import db, settings as st
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


async def run(command: str):
    guild_id = int(os.environ["GFK_DEV_GUILD"])
    client = discord.Client(intents=discord.Intents(guilds=True, members=True))
    done = asyncio.Event()

    @client.event
    async def on_ready():
        try:
            guild = client.get_guild(guild_id)
            if command == "seed":
                await seed(guild)
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

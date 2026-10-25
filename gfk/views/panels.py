"""
GFK-Bot - feste Nachrichten (Panels) mit Buttons, die Neustarts überleben.

Jeder Button hat eine feste custom_id "gfk:panel:<art>". Als DynamicItem registriert, findet discord.py nach einem
Neustart den passenden Code allein über die custom_id - ohne gespeicherte View. Die Module tragen ihre Funktion in
HANDLERS ein (Namen ändern, Meldung, Event planen).
"""
import discord

from gfk.texts import t
from gfk.util import guarded

# Art -> Funktion(interaction), eingetragen von den Modulen (z. B. Eingangskontrolle: "lobby"); sonst Platzhalter
HANDLERS = {}
# Art -> async Funktion(guild, newly_posted) nach /setup panels (z. B. Event-Karten unter die neue Planungs-Nachricht)
AFTER_POST = {}

PANELS = {
    # art: (Kanal-Schlüssel, Titel, Text, Button, Emoji, Farbe)
    "lobby": ("eingang", "panel_lobby_title", "panel_lobby_text", "panel_lobby_button", "✏️", discord.Color.blurple()),
    "report": ("meldungen", "panel_report_title", "panel_report_text", "panel_report_button", "🚨", discord.Color.red()),
    "event": ("events", "panel_event_title", "panel_event_text", "panel_event_button", "📅", discord.Color.green()),
}


class PanelButton(discord.ui.DynamicItem[discord.ui.Button], template=r"gfk:panel:(?P<kind>[a-z]+)"):
    def __init__(self, kind: str):
        _, _, _, label, emoji, _ = PANELS[kind]
        super().__init__(discord.ui.Button(label=t(label), emoji=emoji, style=discord.ButtonStyle.primary,
                                           custom_id=f"gfk:panel:{kind}"))
        self.kind = kind

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match):
        kind = match["kind"]
        if kind not in PANELS:
            raise ValueError(kind)
        return cls(kind)

    @guarded
    async def callback(self, interaction: discord.Interaction):
        handler = HANDLERS.get(self.kind)
        if handler is None:
            await interaction.response.send_message(t("follows"), ephemeral=True)
        else:
            await handler(interaction)


def panel_message(kind: str):
    """(Embed, View) für eine feste Nachricht."""
    _, title, text, _, _, color = PANELS[kind]
    view = discord.ui.View(timeout=None)
    view.add_item(PanelButton(kind))
    return discord.Embed(title=t(title), description=t(text), color=color), view

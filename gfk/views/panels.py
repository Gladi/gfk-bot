"""
GFK-Bot - feste Nachrichten (Panels) mit Buttons, die Neustarts überleben (Grundlage: botcore.panels).

Zusätzlich zu Meldung und Event gibt es beim GFK-Bot die Eingangskontrolle ("Namen ändern", Art "lobby").
"""
import discord

from botcore.panels import AFTER_POST, HANDLERS, PANELS, PanelButton, panel_message  # noqa: F401

PANELS["lobby"] = ("eingang", "panel_lobby_title", "panel_lobby_text", "panel_lobby_button", "✏️",
                   discord.Color.blurple())

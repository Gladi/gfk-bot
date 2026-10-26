"""
GFK-Bot - Rollenverwaltung (Paket 3): Kontextmenü "Status ändern" und /status.

Rechtsklick (Handy: lange tippen) auf eine Person -> Apps -> "Status ändern" -> nur für den Aufrufer sichtbare
Buttons mit genau den Status, die er vergeben darf (Führung: Gast/Freund/Mitglied, Admiral zusätzlich Führung;
Mitglied/Führung nur mit GFK-Kürzel). Niemand ändert sich selbst, den Admiral ändert der Bot nie.
"""
import discord
from discord import app_commands
from discord.ext import commands

from gfk import db, names, settings as st, stfc
from gfk.cogs.onboarding import alliance_for_status, set_status, status_of
from gfk.texts import t
from gfk.util import SafeView


class ChoiceView(SafeView):
    def __init__(self, actor: discord.Member, target: discord.Member, options):
        super().__init__(timeout=120)
        self.actor, self.target = actor, target
        for role in options:
            button = discord.ui.Button(label=st.ROLE_KEYS[role], style=discord.ButtonStyle.primary)
            button.callback = self._make(role)
            self.add_item(button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.actor.id

    def _make(self, role: str):
        async def callback(interaction: discord.Interaction):
            guild = interaction.guild
            config = await db.get_config(guild.id)
            target = guild.get_member(self.target.id)
            if target is None or role not in names.choices(status_of(interaction.user, config), status_of(target, config),
                                                         await alliance_for_status(guild.id, target), stfc.ALLIANCE_TAG):
                await interaction.response.edit_message(content=t("status_stale"), view=None)
                return
            await set_status(guild, config, target, role, interaction.user)
            label = st.ROLE_KEYS[role]
            await interaction.response.edit_message(content=t("status_done", target=target.mention, role=label),
                                                    view=None)
            self.stop()
        return callback


async def open_status_menu(interaction: discord.Interaction, target: discord.Member):
    guild = interaction.guild
    config = await db.get_config(guild.id)
    actor_status = status_of(interaction.user, config)
    if not actor_status & {"admiral", "fuehrung"}:
        await interaction.response.send_message(t("status_denied"), ephemeral=True)
        return
    if target.bot or target.id == interaction.user.id:
        await interaction.response.send_message(t("status_not_self"), ephemeral=True)
        return
    target_status = status_of(target, config)
    alliance = await alliance_for_status(guild.id, target)
    options = names.choices(actor_status, target_status, alliance, stfc.ALLIANCE_TAG)
    current = ", ".join(st.ROLE_KEYS[s] for s in st.STATUS_ROLES if s in target_status) or t("status_none")
    if not options:
        await interaction.response.send_message(t("status_no_options", target=target.mention, current=current),
                                                ephemeral=True)
        return
    await interaction.response.send_message(t("status_menu", target=target.mention, current=current), ephemeral=True,
                                            view=ChoiceView(interaction.user, target, options))


class RolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.menu = app_commands.ContextMenu(name="Status ändern", callback=self._menu)
        self.menu.guild_only = True

    async def cog_load(self):
        self.bot.tree.add_command(self.menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.menu.name, type=self.menu.type)

    async def _menu(self, interaction: discord.Interaction, member: discord.Member):
        await open_status_menu(interaction, member)

    @app_commands.command(name="status", description="Status einer Person ändern (Führung und Admiral)")
    @app_commands.guild_only()
    @app_commands.describe(person="Wessen Status du ändern willst")
    async def status(self, interaction: discord.Interaction, person: discord.Member):
        await open_status_menu(interaction, person)


async def setup(bot: commands.Bot):
    await bot.add_cog(RolesCog(bot))

"""Server-Logs: Vergleiche, Kürzen, Kontoalter, Nachrichten-Zwischenspeicher, Einstellungen (offline)."""
import time
import unittest

import _testenv  # noqa: F401

from gfk import logfmt, settings as st  # noqa: E402
from gfk.texts import T  # noqa: E402


class LogfmtTests(unittest.TestCase):
    def test_clip(self):
        self.assertEqual(logfmt.clip(None), "–")
        self.assertEqual(logfmt.clip("  "), "–")
        self.assertEqual(logfmt.clip("abc"), "abc")
        long = logfmt.clip("x" * 2000)
        self.assertEqual(len(long), logfmt.FIELD_MAX)
        self.assertTrue(long.endswith("…"))

    def test_perm_diff(self):
        before = [("kick_members", False), ("ban_members", True), ("speak", True)]
        after = [("kick_members", True), ("ban_members", False), ("speak", True)]
        added, removed = logfmt.perm_diff(before, after)
        self.assertEqual(added, ["Mitglieder kicken"])
        self.assertEqual(removed, ["Mitglieder bannen"])

    def test_overwrite_diff(self):
        before = {"Gast": {"view_channel": False}, "Alt": {"view_channel": True}}
        after = {"Gast": {"view_channel": True}, "Neu": {"send_messages": False}}
        lines = logfmt.overwrite_diff(before, after)
        self.assertIn("➖ Alt", lines)
        self.assertIn("Gast: ✅ Kanal sehen", lines)
        self.assertIn("➕ Neu", lines)
        self.assertIn("Neu: ❌ Nachrichten senden", lines)
        self.assertEqual(logfmt.overwrite_diff(before, before), [])

    def test_account_age(self):
        now = 1_000_000_000.0
        self.assertEqual(logfmt.account_age(now - 3600, now), ("heute", True))
        self.assertEqual(logfmt.account_age(now - 3 * 86400, now), ("vor 3 Tagen", True))
        self.assertEqual(logfmt.account_age(now - 10 * 86400, now), ("vor 10 Tagen", False))
        self.assertEqual(logfmt.account_age(now - 400 * 86400, now)[0], "vor 13 Monaten")
        self.assertEqual(logfmt.account_age(now - 3 * 365 * 86400, now)[0], "vor 3 Jahren")


class CacheTests(unittest.TestCase):
    def test_put_get_pop(self):
        c = logfmt.MessageCache(max_age=60)
        c.put(1, logfmt.Cached(10, 20, "hallo"))
        self.assertEqual(c.get(1).content, "hallo")
        self.assertEqual(c.pop(1).content, "hallo")
        self.assertIsNone(c.pop(1))

    def test_expiry(self):
        c = logfmt.MessageCache(max_age=60)
        c.put(1, logfmt.Cached(10, 20, "alt", at=time.time() - 120))
        c.put(2, logfmt.Cached(10, 20, "neu"))
        self.assertIsNone(c.get(1))
        c.put(3, logfmt.Cached(10, 20, "alt", at=time.time() - 120))
        self.assertEqual(c.prune(), 1)
        self.assertEqual(len(c), 1)

    def test_max_items_drops_oldest(self):
        c = logfmt.MessageCache(max_age=60, max_items=2)
        for i in range(3):
            c.put(i, logfmt.Cached(10, 20, str(i)))
        self.assertIsNone(c.get(0))
        self.assertEqual(len(c), 2)


class LogSettingsTests(unittest.TestCase):
    def test_msg_days_bounds(self):
        self.assertEqual(st.msg_days({}), st.MSG_DAYS_DEFAULT)
        self.assertEqual(st.msg_days({st.MSG_DAYS_KEY: "0"}), st.MSG_DAYS_MIN)
        self.assertEqual(st.msg_days({st.MSG_DAYS_KEY: "99"}), st.MSG_DAYS_MAX)
        self.assertEqual(st.msg_days({st.MSG_DAYS_KEY: "x"}), st.MSG_DAYS_DEFAULT)

    def test_logs_are_optional(self):
        self.assertFalse(set(st.LOG_KEYS.values()) & set(st.missing({})))

    def test_all_texts_exist(self):
        import glob
        import re
        for path in glob.glob(_testenv.ROOT + "/gfk/**/*.py", recursive=True):
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            for key in set(re.findall(r'\bt\("([a-z_]+)"\s*[,)]', src)):
                self.assertIn(key, T, f"{path}: {key}")


class MemberUpdateTests(unittest.TestCase):
    """after ist das live aktualisierte Mitglied: Änderungen während der Audit-Log-Abfrage gehören zum nächsten Ereignis."""

    def run_update(self, before, after, during):
        import asyncio
        from types import SimpleNamespace
        from gfk.cogs.logs import LogsCog
        sent = []
        cog = LogsCog.__new__(LogsCog)

        async def actor(guild, actions, target_id, within=20):
            during()
            return ""

        async def send(guild, key, embed):
            sent.append(embed)
        cog._actor, cog._send = actor, send
        after.guild = SimpleNamespace(id=1)
        asyncio.run(LogsCog.on_member_update(cog, before, after))
        return sent

    @staticmethod
    def member(nick, roles):
        from types import SimpleNamespace
        return SimpleNamespace(id=7, name="n", nick=nick, roles=list(roles), timed_out_until=None, mention="<@7>")

    def test_roles_changed_during_nick_lookup_are_not_logged_again(self):
        from types import SimpleNamespace
        mitglied = SimpleNamespace(mention="<@&1>")
        before, after = self.member("[GFK] A", [mitglied]), self.member("A", [mitglied])
        sent = self.run_update(before, after, lambda: after.roles.remove(mitglied))
        self.assertEqual([e.title for e in sent], [T["log_nick"]])
        self.assertEqual(sent[0].fields[1].value, "A")

    def test_nick_and_roles_in_one_event(self):
        from types import SimpleNamespace
        mitglied, gast = SimpleNamespace(mention="<@&1>"), SimpleNamespace(mention="<@&2>")
        before, after = self.member("[GFK] A", [mitglied]), self.member("A", [gast])
        sent = self.run_update(before, after, lambda: None)
        self.assertEqual([e.title for e in sent], [T["log_nick"], T["log_member_roles"]])
        self.assertEqual([f.value for f in sent[1].fields], ["<@&2>", "<@&1>"])


class ActorLookupTests(unittest.TestCase):
    """Regression: eine einzelne AuditLogAction darf nicht als Liste mehrerer Aktionen behandelt werden."""

    def test_single_and_multiple_actions(self):
        import asyncio
        import datetime
        import discord
        from gfk.cogs.logs import LogsCog

        asked = []
        now = discord.utils.utcnow()

        class Entry:
            def __init__(self, target_id, user):
                self.target = type("T", (), {"id": target_id})()
                self.user, self.reason, self.created_at = user, None, now - datetime.timedelta(seconds=2)

        class Guild:
            me = type("Me", (), {"guild_permissions": discord.Permissions(view_audit_log=True)})()

            def audit_logs(self, limit, action):
                assert isinstance(action, discord.AuditLogAction), action
                asked.append(action)

                async def gen():
                    if action == discord.AuditLogAction.member_update:
                        yield Entry(5, type("U", (), {"id": 9, "mention": "<@9>"})())
                return gen()

        cog = LogsCog.__new__(LogsCog)
        cog.bot = type("B", (), {"user": type("U", (), {"id": 1})()})()
        A = discord.AuditLogAction
        self.assertIn("<@9>", asyncio.run(cog._actor(Guild(), A.member_update, 5)))
        self.assertEqual(asyncio.run(cog._actor(Guild(), [A.channel_update, A.overwrite_update], 5)), "")
        self.assertEqual(asked, [A.member_update, A.channel_update, A.overwrite_update])


if __name__ == "__main__":
    unittest.main()

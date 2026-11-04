"""Grundgerüst: Datenbank, Einstellungen, Prüfungen, feste Nachrichten, Texte (offline)."""
import asyncio
import re
import unittest

import _testenv  # noqa: F401

from gfk import db, settings as st  # noqa: E402
from gfk.texts import T, t  # noqa: E402
from gfk.views import panels  # noqa: E402

G = 424242424242424242


def run(coro):
    return asyncio.run(coro)


class DbTests(unittest.TestCase):
    def setUp(self):
        db.init()
        db.set_config_sync(G, {k: None for k in db.get_config_sync(G)})

    def test_schema_has_all_tables(self):
        with db._conn() as conn:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"config", "reports", "events", "event_participants", "role_log", "members"} <= tables)

    def test_config_set_update_delete(self):
        run(db.set_config(G, {"role_gast": "1", "channel_log": "2"}))
        run(db.set_config(G, {"role_gast": "3"}))
        self.assertEqual(run(db.get_config(G)), {"role_gast": "3", "channel_log": "2"})
        run(db.set_config(G, {"channel_log": None}))
        self.assertEqual(run(db.get_config(G)), {"role_gast": "3"})
        self.assertEqual(run(db.get_config(G + 1)), {})        # andere Server getrennt

    def test_init_is_repeatable(self):
        db.init()
        db.init()


class SettingsTests(unittest.TestCase):
    def test_missing_lists_everything_until_set(self):
        self.assertEqual(len(st.missing({})), len(st.ROLE_KEYS) + len(st.CHANNEL_KEYS))
        full = {st.role_key(k): "1" for k in st.ROLE_KEYS} | {st.channel_key(k): "1" for k in st.CHANNEL_KEYS}
        self.assertEqual(st.missing(full), [])

    def test_unmanageable_roles(self):
        roles = [st.RoleInfo("gast", "Gast", 3), st.RoleInfo("fuehrung", "Führung", 10)]
        self.assertEqual(st.unmanageable(10, roles), ["Führung"])
        self.assertEqual(st.unmanageable(11, roles), [])

    def test_role_order(self):
        good = {"admiral": 9, "fuehrung": 8, "mitglied": 7, "freund": 6, "gast": 5}
        self.assertEqual(st.order_problems(good), [])
        self.assertEqual(st.order_problems({**good, "gast": 7}), ["Freund sollte über Gast stehen"])
        self.assertEqual(st.order_problems({"admiral": 9, "gast": 5}), [])   # fehlende Rollen stören nicht

    def test_reminder_minutes(self):
        self.assertEqual(st.reminder_minutes({}), st.REMINDER_DEFAULT)
        self.assertEqual(st.reminder_minutes({st.REMINDER_KEY: "1"}), st.REMINDER_MIN)
        self.assertEqual(st.reminder_minutes({st.REMINDER_KEY: "999"}), st.REMINDER_MAX)
        self.assertEqual(st.reminder_minutes({st.REMINDER_KEY: "x"}), st.REMINDER_DEFAULT)


class PanelTests(unittest.TestCase):
    def test_custom_ids_are_fixed_and_match_template(self):
        for kind in panels.PANELS:
            embed, view = panels.panel_message(kind)
            (item,) = view.children
            self.assertEqual(item.custom_id, f"gfk:panel:{kind}")
            self.assertTrue(re.fullmatch(panels.PanelButton.__discord_ui_compiled_template__, item.custom_id))
            self.assertTrue(embed.title and embed.description)
            self.assertIsNone(view.timeout)                      # überlebt Neustarts

    def test_unknown_kind_is_rejected(self):
        match = panels.PanelButton.__discord_ui_compiled_template__.fullmatch("gfk:panel:nope")
        with self.assertRaises(ValueError):
            run(panels.PanelButton.from_custom_id(None, None, match))


class TextTests(unittest.TestCase):
    def test_all_texts_format(self):
        for key, text in T.items():
            fields = set(re.findall(r"\{(\w+)\}", text)) - {"bot", "tag"}
            self.assertTrue(t(key, **{f: "x" for f in fields}))

    def test_gfk_wording_unchanged(self):
        self.assertEqual(t("internal_only_event"), "🔒 Events sind nur für GFK-Mitglieder.")
        self.assertTrue(t("internal_only_report").endswith("Gäste und Freunde melden bitte von Hand in ihrem Forum."))
        self.assertEqual(t("setup_title"), "⚙️ GFK-Bot - Einstellungen")
        self.assertIn("stfc.pro", t("uninstall_confirm"))


class CompatTests(unittest.TestCase):
    """Buttons alter Nachrichten auf dem GFK-Server tragen "gfk:" - die IDs dürfen sich nie ändern."""

    def test_report_and_event_ids(self):
        import datetime as dt
        from botcore import eventlogic as el
        from botcore.cogs import events, reports

        async def go():
            ids = [c.custom_id for c in reports.report_view(1, "roe").children]
            self.assertEqual(ids, ["gfk:report:progress:1", "gfk:report:done:1"])
            now = dt.datetime(2026, 11, 4, 18, 0, tzinfo=dt.timezone.utc)
            ev = {"id": 3, "type": "alliance", "title": "Borg", "category": "armada", "start_at": el.iso(now),
                  "end_at": el.iso(now), "description": "", "creator_id": 1, "status": "planned",
                  "voice_channel_id": None, "thread_id": 9}
            _, view = events.card(ev, {})
            self.assertEqual([c.custom_id for c in view.children],
                             [f"gfk:ev:{a}:3" for a in ("join", "maybe", "leave", "edit", "cancel")])
        run(go())

    def test_core_tables_and_gfk_tables(self):
        db.init()
        with db._conn() as conn:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"config", "reports", "events", "members", "notices", "role_log", "stfc_roster"} <= tables)


class ExtraPanelTests(unittest.TestCase):
    def test_extra_channels_optional(self):
        for kind, keys in st.PANEL_EXTRA_CHANNELS.items():
            self.assertIn(kind, panels.PANELS)
            for key in keys:
                self.assertIn(key, st.OPTIONAL_CHANNEL_KEYS)
        self.assertFalse(set(st.OPTIONAL_CHANNEL_KEYS.values()) & set(st.missing({})))


if __name__ == "__main__":
    unittest.main()

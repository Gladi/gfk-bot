"""Meldungen: In Bearbeitung/Erledigt, Aufräumregeln im Vorfallforum, Vorfall-Statistik (offline)."""
import asyncio
import datetime as dt
import unittest

import _testenv  # noqa: F401

from gfk import db, reportstats as rs  # noqa: E402
from gfk.cogs import reports  # noqa: E402

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
DAY = dt.timedelta(days=1)


class StatusTests(unittest.TestCase):
    def setUp(self):
        db.init()

    def test_progress_then_done(self):
        rid = db.create_report_sync(9, 1, "roe", "ABC", "P", "D")
        self.assertTrue(db.progress_report_sync(rid, 2))
        self.assertFalse(db.progress_report_sync(rid, 3))               # nur einmal übernehmen
        self.assertEqual(db.get_report_sync(rid)["progress_by"], 2)
        self.assertTrue(db.close_report_sync(rid, 2))                   # aus "in Bearbeitung" erledigen
        self.assertFalse(db.progress_report_sync(rid, 2))
        self.assertFalse(db.close_report_sync(rid, 2))

    def test_rows_only_with_thread(self):
        a = db.create_report_sync(10, 1, "roe", "ABC", "P", "D")
        db.create_report_sync(10, 1, "roe", "ABC", "Q", "D")            # Beitrag nie angelegt -> zählt nicht
        db.set_report_thread_sync(a, 555)
        rows = db.report_rows_sync(10)
        self.assertEqual([r[:3] for r in rows], [("roe", "ABC", "P")])
        self.assertGreater(rows[0][3], 1_700_000_000)

    def test_buttons(self):
        async def go():
            self.assertIsNone(reports.report_view(1, "nullnode"))       # Nachweis: keine Buttons
            ids = [c.custom_id for c in reports.report_view(1, "roe").children]
            self.assertEqual(ids, ["gfk:report:progress:1", "gfk:report:done:1"])
            taken = reports.report_view(1, "roe", taken=True).children[0]
            self.assertTrue(taken.item.disabled)
        asyncio.run(go())


class CleanupTests(unittest.TestCase):
    def reason(self, tags, age_days, idle_days=None, pinned=False):
        created = NOW - age_days * DAY
        last = NOW - (idle_days if idle_days is not None else age_days) * DAY
        return reports.cleanup_reason(tags, created, last, pinned, NOW)

    def test_nullnode_after_14_days(self):
        self.assertIsNone(self.reason(["0-Node"], 13))
        self.assertEqual(self.reason(["0-Node"], 15), "nullnode")
        self.assertEqual(self.reason(["Null-Node", "Offen"], 15), "nullnode")    # eigener Tag des Bots

    def test_done_after_30_days_idle(self):
        self.assertIsNone(self.reason(["ROE-Verstoß", "Erledigt"], 60, idle_days=10))   # noch Aktivität
        self.assertEqual(self.reason(["ROE-Verstoß", "Erledigt"], 60, idle_days=31), "done")

    def test_never_open_or_pinned(self):
        self.assertIsNone(self.reason(["Neue Meldung"], 400))
        self.assertIsNone(self.reason(["In Bearbeitung"], 400))
        self.assertIsNone(self.reason(["0-Node"], 400, pinned=True))
        self.assertIsNone(self.reason(["Erledigt"], 400, pinned=True))


class StatsTests(unittest.TestCase):
    def test_render(self):
        now = NOW.timestamp()
        rows = [("roe", "abc", "Testpilot", now), ("nullnode", "[ABC]", "testpilot", now - 40 * 86400),
                ("roe", "ABC", "Kometa", now), ("nullnode", "XYZ", "Nebula", now), ("sonstiges", "", "X", now)]
        msgs = rs.render(rows, "📊", now)
        text = "\n".join(msgs)
        self.assertIn("5 Meldungen · 2 Allianzen", text)
        self.assertLess(text.index("[ABC]"), text.index("[XYZ]"))            # meiste Meldungen zuerst
        self.assertLess(text.index("[XYZ]"), text.index("ohne Allianz"))      # ohne Allianz zuletzt
        line = next(l for l in text.splitlines() if l.startswith("Testpilot"))
        self.assertEqual(line.split("│")[1:], ["   1 ", "   1 ", "   · ", "   2 ", "   1"])   # 1 RoE, 1 0-N; 30T=1
        widths = {len(l) for l in text.splitlines() if "│" in l}
        self.assertEqual(len(widths), 1)                                      # alle Tabellen gleich breit
        self.assertTrue(all(len(m) <= 2000 for m in msgs))

    def test_many_players_split(self):
        now = NOW.timestamp()
        rows = [("roe", "BIG", f"Spieler{i:03d}", now) for i in range(150)]
        msgs = rs.render(rows, "📊", now)
        self.assertGreater(len(msgs), 2)
        self.assertTrue(all(len(m) <= 2000 for m in msgs))
        self.assertEqual(sum(m.count("Spieler") - m.count("Spieler   ") for m in msgs), 150 + 0 * len(msgs))

    def test_empty(self):
        self.assertIn("Noch keine Meldungen", rs.render([], "📊", NOW.timestamp())[0])


if __name__ == "__main__":
    unittest.main()

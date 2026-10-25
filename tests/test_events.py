"""Events und Meldungen: Zeit-/Dauer-Eingaben, Fälligkeiten, Namen, Formulare (Discord-Grenzen), DB (offline)."""
import asyncio
import datetime as dt
import unittest

import _testenv  # noqa: F401

import discord  # noqa: E402

from gfk import db, eventlogic as el  # noqa: E402
from gfk.cogs import events, reports  # noqa: E402

UTC = dt.timezone.utc
# Samstag, 24.10.2026 18:00 Berliner Sommerzeit (= 16:00 UTC); Zeitumstellung in der Nacht auf den 25.10.
NOW = dt.datetime(2026, 10, 24, 16, 0, tzinfo=UTC)


def berlin(*args) -> dt.datetime:
    return dt.datetime(*args, tzinfo=el.TZ).astimezone(UTC)


class WhenTests(unittest.TestCase):
    def test_full_and_short_dates(self):
        self.assertEqual(el.parse_when("25.10.2026 20:00", NOW), berlin(2026, 10, 25, 20, 0))
        self.assertEqual(el.parse_when("25.10. 20:00", NOW), berlin(2026, 10, 25, 20, 0))
        self.assertEqual(el.parse_when("25.10 20.00 Uhr", NOW), berlin(2026, 10, 25, 20, 0))
        self.assertEqual(el.parse_when("25.10.26 20:00", NOW), berlin(2026, 10, 25, 20, 0))
        self.assertEqual(el.parse_when("5.1. 9:30", NOW), berlin(2027, 1, 5, 9, 30))   # nächstes Jahr

    def test_words_and_time_only(self):
        self.assertEqual(el.parse_when("morgen 20:00", NOW), berlin(2026, 10, 25, 20, 0))
        self.assertEqual(el.parse_when("heute um 21:15", NOW), berlin(2026, 10, 24, 21, 15))
        self.assertEqual(el.parse_when("20:00", NOW), berlin(2026, 10, 24, 20, 0))
        self.assertEqual(el.parse_when("17:00", NOW), berlin(2026, 10, 25, 17, 0))     # vorbei -> morgen

    def test_dst_switch(self):
        # 25.10.2026 ab 03:00 Winterzeit: 20:00 Berlin = 19:00 UTC
        self.assertEqual(el.parse_when("25.10. 20:00", NOW), dt.datetime(2026, 10, 25, 19, 0, tzinfo=UTC))

    def test_errors(self):
        for text, code in [("bald", "format"), ("31.02. 20:00", "format"), ("25.10. 25:00", "format"),
                           ("24.10.2026 17:00", "past"), ("heute 17:00", "past"), ("01.01.2028 20:00", "far"),
                           ("", "format")]:
            with self.assertRaises(ValueError) as ctx:
                el.parse_when(text, NOW)
            self.assertEqual(str(ctx.exception), code, text)


class DurationTests(unittest.TestCase):
    def test_values(self):
        for text, minutes in [("", 60), (None, 60), ("1", 60), ("1,5", 90), ("2h", 120), ("2 Std", 120),
                              ("90", 90), ("90min", 90), ("45 min", 45), ("1:30", 90), ("24", 1440)]:
            self.assertEqual(el.parse_duration(text), minutes, text)

    def test_errors(self):
        for text in ("10min", "25h", "abc", "0", "1:75x"):
            with self.assertRaises(ValueError):
                el.parse_duration(text)

    def test_texts(self):
        self.assertEqual(el.duration_text(60), "1 h")
        self.assertEqual(el.duration_text(90), "1:30 h")
        self.assertEqual(el.duration_text(45), "45 min")
        self.assertEqual(el.parse_duration(el.duration_input(90)), 90)


class DueTests(unittest.TestCase):
    start = NOW + dt.timedelta(hours=2)
    end = start + dt.timedelta(hours=1)

    def due(self, now, status="planned", voice=False, reminded=0, minutes=30):
        return el.due(self.start, self.end, status, voice, reminded, now, minutes)

    def test_timeline(self):
        self.assertEqual(self.due(NOW), set())
        self.assertEqual(self.due(self.start - dt.timedelta(minutes=60)), {"voice"})
        self.assertEqual(self.due(self.start - dt.timedelta(minutes=30), voice=True), {"remind"})
        self.assertEqual(self.due(self.start - dt.timedelta(minutes=29), voice=True, reminded=el.REMIND_BIT), set())
        self.assertEqual(self.due(self.start, voice=True, reminded=el.REMIND_BIT), {"start"})
        self.assertEqual(self.due(self.start + dt.timedelta(minutes=5), voice=True, reminded=3), set())
        self.assertEqual(self.due(self.end, voice=True, reminded=3), {"end"})
        self.assertEqual(self.due(self.end, status="ended", voice=True), {"cleanup"})
        self.assertEqual(self.due(self.end, status="done"), set())

    def test_bot_was_offline(self):
        # Neustart mitten im Event: Sprachkanal + Start-Hinweis nachholen, aber keine Vorlauf-Erinnerung mehr
        self.assertEqual(self.due(self.start + dt.timedelta(minutes=10)), {"voice", "start"})
        self.assertEqual(self.due(self.end + dt.timedelta(hours=5)), {"end"})

    def test_cancelled_waits_for_end(self):
        self.assertEqual(self.due(self.start, status="cancelled"), set())
        self.assertEqual(self.due(self.end, status="cancelled"), {"cleanup"})

    def test_initial_reminded(self):
        self.assertEqual(el.initial_reminded(NOW + dt.timedelta(minutes=20), NOW, 30), el.REMIND_BIT)
        self.assertEqual(el.initial_reminded(NOW + dt.timedelta(minutes=40), NOW, 30), 0)


class NameTests(unittest.TestCase):
    def test_names(self):
        start = berlin(2026, 10, 25, 20, 0)
        self.assertEqual(el.voice_name("armada", start), "🔊 Armada 25.10. 20:00")
        self.assertEqual(el.thread_name("welle", start, "  Hostiles  im Süden "), "🌊 Welle 25.10. 20:00 – Hostiles im Süden")
        self.assertLessEqual(len(el.thread_name("welle", start, "x" * 300)), 100)
        self.assertEqual(el.short_time(start), "So 25.10. 20:00")
        self.assertEqual(el.input_value(start), "25.10.2026 20:00")
        self.assertEqual(el.from_iso(el.iso(start)), start)
        self.assertEqual(el.event_name("sonstiges", ""), "Sonstiges")

    def test_mention_chunks(self):
        chunks = list(el.mention_chunks(range(10 ** 17, 10 ** 17 + 200), prefix="Hallo\n"))
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= 2000 for c in chunks))
        self.assertTrue(chunks[0].startswith("Hallo"))
        self.assertEqual(sum(c.count("<@") for c in chunks), 200)

    def test_report_title(self):
        when = dt.datetime(2026, 10, 25)
        self.assertEqual(reports.report_title("roe", "ABC", "Spieler", when), "[ROE-Verstoß] ABC – Spieler – 25.10.2026")
        self.assertEqual(reports.report_title("nullnode", "", "Spieler", when), "[Null-Node] Spieler – 25.10.2026")
        self.assertLessEqual(len(reports.report_title("roe", "A" * 30, "B" * 60, when)), 100)


class _Guild:
    def get_member(self, _):
        return None


def _check_limits(test, payload):
    test.assertLessEqual(len(payload["title"]), 45)
    test.assertLessEqual(len(payload["components"]), 5)
    for comp in payload["components"]:
        test.assertEqual(comp["type"], 18)                       # Label
        test.assertLessEqual(len(comp["label"]), 45)
        test.assertLessEqual(len(comp.get("description") or ""), 100)
        test.assertLessEqual(len(comp["component"].get("placeholder") or ""), 100)


class ModalTests(unittest.TestCase):
    def test_report_modal(self):
        async def go():
            payload = reports.ReportModal().to_dict()
            _check_limits(self, payload)
            types = [c["component"]["type"] for c in payload["components"]]
            self.assertEqual(types, [3, 4, 4, 4, 19])            # Select, 3 Textfelder, Datei-Upload
        asyncio.run(go())

    def test_event_modals(self):
        async def go():
            for kind, count in (("alliance", 4), ("private", 5)):
                payload = events.EventModal(None, _Guild(), kind).to_dict()
                _check_limits(self, payload)
                self.assertEqual(len(payload["components"]), count)
            payload = events.EventModal(None, _Guild(), "alliance", {"category": "welle", "when": "25.10. 20:00"},
                                        event_id=1).to_dict()
            select = payload["components"][0]["component"]
            self.assertEqual([o["value"] for o in select["options"] if o.get("default")], ["welle"])
        asyncio.run(go())

    def test_button_labels(self):
        for key, (text, _e, _s) in events.BUTTONS.items():
            self.assertLessEqual(len(events.t(text)), 80, key)


class EventDbTests(unittest.TestCase):
    def setUp(self):
        db.init()

    def test_event_roundtrip(self):
        eid = db.create_event_sync(7, "alliance", "armada", el.iso(NOW), el.iso(NOW + dt.timedelta(hours=1)), "x", 1, 0)
        db.set_participant_sync(eid, 1, "dabei")
        db.set_participant_sync(eid, 2, "vielleicht")
        db.set_participant_sync(eid, 1, "abgemeldet")
        self.assertEqual(db.participants_sync(eid), {1: "abgemeldet", 2: "vielleicht"})
        db.set_participant_sync(eid, 2, None)
        self.assertEqual(db.participants_sync(eid), {1: "abgemeldet"})
        db.update_event_sync(eid, voice_channel_id=55, status="ended")
        self.assertEqual(db.event_by_voice_sync(55)["id"], eid)
        self.assertIn(eid, [e["id"] for e in db.active_events_sync(7)])
        db.update_event_sync(eid, status="done")
        self.assertNotIn(eid, [e["id"] for e in db.active_events_sync(7)])
        with self.assertRaises(ValueError):
            db.update_event_sync(eid, creator_id=3)

    def test_card_buttons(self):
        ev = {"id": 3, "type": "alliance", "category": "armada", "start_at": el.iso(NOW),
              "end_at": el.iso(NOW + dt.timedelta(minutes=90)), "description": "Test", "creator_id": 1,
              "status": "planned", "voice_channel_id": None, "thread_id": 9}

        async def go():
            embed, view = events.card(ev, {1: "dabei", 2: "vielleicht", 4: "abgemeldet"})
            self.assertEqual([c.custom_id for c in view.children],
                             [f"gfk:ev:{a}:3" for a in ("join", "maybe", "leave", "edit", "cancel")])
            self.assertIn("(1)", embed.fields[3].name)
            embed, view = events.card({**ev, "type": "private"}, {1: "dabei"})
            self.assertEqual([c.custom_id for c in view.children], [f"gfk:ev:{a}:3" for a in ("ask", "edit", "cancel")])
            _, view = events.card({**ev, "status": "cancelled"}, {})
            self.assertIsNone(view)
        asyncio.run(go())

    def test_report_close_once(self):
        rid = db.create_report_sync(7, 1, "roe", "", "P", "D")
        self.assertTrue(db.close_report_sync(rid, 2))
        self.assertFalse(db.close_report_sync(rid, 2))
        self.assertEqual(db.get_report_sync(rid)["closed_by"], 2)


if __name__ == "__main__":
    unittest.main()

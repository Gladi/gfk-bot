"""Eingangskontrolle: Kürzel, Nicknames, Status-Rechte, stfc.pro-Liste (offline)."""
import json
import unittest

import _testenv  # noqa: F401

from gfk import db, names, settings as st, stfc  # noqa: E402


def page(players, duplicate=True) -> str:
    """Nachbau einer stfc.pro-Allianzseite: Next.js-Payload in self.__next_f.push-Stücken."""
    payload = '1:["$","div",null,{"players":' + json.dumps(players) + '}]'
    if duplicate:
        payload += '2:{"players":' + json.dumps(players[:1]) + '}'
    esc = json.dumps(payload)[1:-1]
    half = len(esc) // 2
    while esc[half - 1] == "\\":
        half += 1
    return (f'<script>self.__next_f.push([1,"{esc[:half]}"])</script>'
            f'<script>self.__next_f.push([1,"{esc[half:]}"])</script>')


PLAYERS = [{"playerid": 11, "owner": "McRunner", "tag": "GFK", "rankdesc": "Admiral"},
           {"playerid": 22, "owner": "Ëlla Star", "tag": "GFK", "rankdesc": "Premier"},
           {"playerid": 33, "owner": "Kestrel_77", "tag": "GFK", "rankdesc": "Agent"}]


class TagAndNickTests(unittest.TestCase):
    def test_clean_tag(self):
        self.assertEqual(names.clean_tag(" [gfk] "), "GFK")
        self.assertIsNone(names.clean_tag("   "))
        for bad in ("GF K", "TOOLONG7", "G-F"):
            with self.assertRaises(ValueError):
                names.clean_tag(bad)

    def test_nickname_format_and_length(self):
        self.assertEqual(names.nickname("GFK", "McRunner"), "[GFK] McRunner")
        self.assertEqual(names.nickname(None, "McRunner"), "McRunner")
        long = names.nickname("ABCDEF", "A" * 40)
        self.assertEqual(len(long), names.MAX_NICK)
        self.assertTrue(long.startswith("[ABCDEF] ") and long.endswith("…"))   # gekürzt wird der Name, nie das Kürzel
        self.assertEqual(names.clean_name("  Ella   Star "), "Ella Star")


class StatusRightsTests(unittest.TestCase):
    def test_who_may_grant_what(self):
        self.assertTrue(names.may_grant({"fuehrung"}, "mitglied", {"gast"}))
        self.assertTrue(names.may_grant({"fuehrung"}, "freund", {"gast"}))
        self.assertFalse(names.may_grant({"fuehrung"}, "fuehrung", {"mitglied"}))   # Führung ernennt nur der Admiral
        self.assertTrue(names.may_grant({"admiral"}, "fuehrung", {"mitglied"}))
        self.assertFalse(names.may_grant({"mitglied"}, "freund", {"gast"}))         # Mitglieder vergeben nichts
        self.assertFalse(names.may_grant({"fuehrung"}, "gast", {"fuehrung"}))       # Führung degradiert nur der Admiral
        self.assertTrue(names.may_grant({"admiral"}, "mitglied", {"fuehrung"}))
        self.assertFalse(names.may_grant({"admiral"}, "mitglied", {"admiral"}))     # den Admiral ändert der Bot nie

    def test_member_and_leadership_only_for_gfk(self):
        self.assertTrue(names.allowed_for_alliance("mitglied", "GFK"))
        self.assertTrue(names.allowed_for_alliance("fuehrung", "gfk"))
        self.assertFalse(names.allowed_for_alliance("mitglied", "ABC"))
        self.assertFalse(names.allowed_for_alliance("fuehrung", ""))
        self.assertFalse(names.allowed_for_alliance("mitglied", None))
        self.assertTrue(names.allowed_for_alliance("freund", "ABC"))
        self.assertTrue(names.allowed_for_alliance("gast", None))

    def test_losing_the_gfk_tag(self):
        self.assertEqual(names.tag_of_nick("[GFK] McRunner"), "GFK")
        self.assertEqual(names.tag_of_nick("[gfk]McRunner"), "GFK")
        self.assertIsNone(names.tag_of_nick("McRunner"))
        self.assertIsNone(names.tag_of_nick(None))
        self.assertEqual(names.tag_of_nick("[ABC] Tom"), "ABC")
        self.assertTrue(names.loses_gfk_status({"mitglied"}, None))
        self.assertTrue(names.loses_gfk_status({"fuehrung"}, "ABC"))
        self.assertFalse(names.loses_gfk_status({"mitglied"}, "GFK"))
        self.assertFalse(names.loses_gfk_status({"admiral", "fuehrung"}, None))   # Admiral nie automatisch
        self.assertFalse(names.loses_gfk_status({"freund"}, None))
        self.assertFalse(names.loses_gfk_status({"gast"}, "ABC"))

    def test_status_change_keeps_exactly_one(self):
        self.assertEqual(names.status_change({"gast"}, "mitglied", st.STATUS_ROLES), (["gast"], ["mitglied"]))
        self.assertEqual(names.status_change(set(), "gast", st.STATUS_ROLES), ([], ["gast"]))
        self.assertEqual(names.status_change({"admiral", "fuehrung"}, "fuehrung", st.STATUS_ROLES), ([], []))
        self.assertEqual(names.status_change({"gast", "freund"}, "freund", st.STATUS_ROLES), (["gast"], []))


class StfcTests(unittest.TestCase):
    def test_parse_roster_merges_duplicates(self):
        roster = stfc.parse_roster(page(PLAYERS))
        self.assertEqual(sorted(roster), [11, 22, 33])
        self.assertEqual(roster[22], stfc.Player(22, "Ëlla Star", "GFK", "Premier"))

    def test_parse_roster_empty_or_changed_format(self):
        self.assertEqual(stfc.parse_roster("<html>nothing</html>"), {})

    def test_find_is_tolerant(self):
        roster = stfc.parse_roster(page(PLAYERS))
        self.assertEqual(stfc.find(roster, "mcrunner").player_id, 11)
        self.assertEqual(stfc.find(roster, "Ella Star").player_id, 22)       # ohne Akzent, mit Leerzeichen
        self.assertEqual(stfc.find(roster, "kestrel 77").player_id, 33)
        self.assertIsNone(stfc.find(roster, "Somebody"))

    def test_suggestions_for_typos(self):
        roster = stfc.parse_roster(page(PLAYERS))
        self.assertEqual([p.player_id for p in stfc.suggestions(roster, "McRuner")][:1], [11])
        self.assertEqual(stfc.suggestions(roster, "zzz"), [])


class MemberDbTests(unittest.TestCase):
    def test_save_link_delete(self):
        db.init()
        db.save_member_sync(1, 2, "GFK", "McRunner", 11)
        db.save_member_sync(1, 3, "", "Gastname", None)
        self.assertEqual(db.get_member_sync(1, 2), ("GFK", "McRunner", 11))
        self.assertEqual([r[0] for r in db.linked_members_sync(1)], [2])
        db.save_member_sync(1, 2, "GFK", "McRunner2", 11)                    # Update statt Duplikat
        self.assertEqual(db.get_member_sync(1, 2)[1], "McRunner2")
        db.delete_member_sync(1, 2)
        self.assertIsNone(db.get_member_sync(1, 2))
        self.assertEqual(db.unlinked_gfk_members_sync(1), [])
        db.save_member_sync(1, 4, "gfk", "Neuling2", None)
        self.assertEqual(db.unlinked_gfk_members_sync(1), [(4, "Neuling2")])   # GFK ohne Spieler-ID


if __name__ == "__main__":
    unittest.main()

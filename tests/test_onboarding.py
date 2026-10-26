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


class _Role:
    def __init__(self, rid):
        self.id = rid


class _Member:
    def __init__(self, uid, nick, roles=(), bot=False):
        self.id, self.nick, self.bot = uid, nick, bot
        self.roles = [_Role(r) for r in roles]
        self.mention = f"<@{uid}>"


class _Guild:
    def __init__(self, gid, members):
        self.id, self.members = gid, members


class LinkExistingTests(unittest.TestCase):
    def test_find_prefix(self):
        roster = {p["playerid"]: stfc.Player(p["playerid"], p["owner"], "GFK", "") for p in PLAYERS}
        self.assertEqual(stfc.find_prefix(roster, "Kestr…").player_id, 33)
        self.assertIsNone(stfc.find_prefix(roster, "…"))
        roster[44] = stfc.Player(44, "Kestrel_88", "GFK", "")
        self.assertIsNone(stfc.find_prefix(roster, "Kestr…"))              # nicht eindeutig

    def test_link_existing(self):
        import asyncio
        from gfk.cogs.onboarding import link_existing, link_report
        db.init()
        g = 4242
        db.set_config_sync(g, {st.role_key("mitglied"): "500"})
        db.save_member_sync(g, 4, "GFK", "Kestrel_77", 33)                  # schon verknüpft
        roster = {p["playerid"]: stfc.Player(p["playerid"], p["owner"], "GFK", "") for p in PLAYERS}
        members = [_Member(1, "[GFK] McRunner"), _Member(2, "[GFK] Unbekannt"), _Member(3, "[ABC] Ella Star"),
                   _Member(4, "[GFK] Kestrel_77"), _Member(5, "Ohne Kürzel", roles=[500]), _Member(6, None, bot=True),
                   _Member(7, "[gfk] ëlla star")]
        linked, already, missing, untagged = asyncio.run(link_existing(_Guild(g, members), roster))
        self.assertEqual(sorted(m.id for m in linked), [1, 7])
        self.assertEqual(already, 1)
        self.assertEqual([(m.id, n) for m, n in missing], [(2, "Unbekannt")])
        self.assertEqual([m.id for m in untagged], [5])
        self.assertEqual(db.get_member_sync(g, 1), ("GFK", "McRunner", 11))
        self.assertEqual(db.get_member_sync(g, 2), ("GFK", "Unbekannt", None))   # später automatisch verknüpfbar
        self.assertIsNone(db.get_member_sync(g, 3))
        embed = link_report(linked, already, missing, untagged)
        self.assertEqual(len(embed.fields), 2)


class _Target:
    def __init__(self):
        self.sent = []

    async def send(self, text=None, **kwargs):
        self.sent.append(text)


class _ChanGuild:
    def __init__(self, gid, channels):
        self.id, self.channels = gid, channels

    def get_channel_or_thread(self, cid):
        return self.channels.get(cid)

    async def fetch_channel(self, cid):
        import discord
        raise discord.NotFound(type("R", (), {"status": 404, "reason": "x"})(), "x")


class NameChangeTests(unittest.TestCase):
    def test_goes_to_thread_or_falls_back(self):
        import asyncio
        from gfk.cogs.onboarding import post_name_change
        db.init()
        g, thread, verw = 5151, _Target(), _Target()
        guild = _ChanGuild(g, {11: thread, 22: verw})
        member = _Member(1, "[GFK] Neu")
        db.set_config_sync(g, {st.channel_key("verwaltung"): "22", st.channel_key("namen_log"): "11"})
        asyncio.run(post_name_change(guild, member, "Alt", "Neu", "sync"))
        self.assertEqual(len(thread.sent), 1)
        self.assertIn("**Neu**", thread.sent[0])
        self.assertIn("**Alt**", thread.sent[0])
        self.assertEqual(verw.sent, [])
        db.set_config_sync(g, {st.channel_key("namen_log"): "99"})        # Beitrag gelöscht -> Verwaltung
        asyncio.run(post_name_change(guild, member, "Alt", "Neu", "self"))
        self.assertEqual(len(verw.sent), 1)
        self.assertIn("Namen ändern", verw.sent[0])


if __name__ == "__main__":
    unittest.main()


class _Resp:
    def __init__(self, status, text):
        self.status, self._text = status, text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def text(self):
        return self._text


class _Session:
    """Attrappe für aiohttp.ClientSession: liefert nacheinander die vorgegebenen Antworten (Exception = Ausfall)."""
    def __init__(self, *answers):
        self.answers, self.calls = list(answers), 0

    def get(self, *args, **kwargs):
        self.calls += 1
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return _Resp(*answer)


class StoredRosterTests(unittest.TestCase):
    def setUp(self):
        db.init()
        db.save_roster_sync([], 0)

    def roster(self):
        return stfc.Roster(store=(db.save_roster, db.load_roster))

    def test_successful_fetch_is_stored_and_used_when_site_is_down(self):
        import aiohttp
        r = self.roster()
        players = run(r.get(_Session((200, page(PLAYERS)))))
        self.assertEqual(sorted(players), [11, 22, 33])
        self.assertEqual(len(db.load_roster_sync()[0]), 3)
        down = self.roster()                                   # neuer Start, stfc.pro nicht erreichbar
        got = run(down.get(_Session(aiohttp.ClientError("down"))))
        self.assertEqual(sorted(got), [11, 22, 33])
        self.assertTrue(down.from_store)
        session = _Session()
        self.assertEqual(sorted(run(down.get(session))), [11, 22, 33])   # 2 Minuten kein neuer Versuch
        self.assertEqual(session.calls, 0)

    def test_changed_format_does_not_overwrite_stored_list(self):
        r = self.roster()
        run(r.get(_Session((200, page(PLAYERS)))))
        again = self.roster()
        self.assertEqual(sorted(run(again.get(_Session((200, "<html>neues Format</html>"))))), [11, 22, 33])
        self.assertEqual(len(db.load_roster_sync()[0]), 3)

    def test_too_old_stored_list_is_not_used(self):
        import time
        db.save_roster_sync([(11, "McRunner", "GFK", "Admiral")], time.time() - stfc.STORED_MAX_AGE - 60)
        self.assertIsNone(run(self.roster().get(_Session((503, "")))))


def run(coro):
    import asyncio
    return asyncio.run(coro)


class StatusChoiceTests(unittest.TestCase):
    def test_choices_per_actor(self):
        self.assertEqual(names.choices({"fuehrung"}, {"gast"}, "GFK"), ["freund", "mitglied"])
        self.assertEqual(names.choices({"admiral"}, {"mitglied"}, "GFK"), ["gast", "freund", "fuehrung"])
        self.assertEqual(names.choices({"fuehrung"}, {"gast"}, "ABC"), ["freund"])        # ohne GFK nur Freund
        self.assertEqual(names.choices({"fuehrung"}, {"fuehrung"}, "GFK"), [])           # Führung ändert nur der Admiral
        self.assertEqual(names.choices({"mitglied"}, {"gast"}, "GFK"), [])
        self.assertEqual(names.choices({"admiral"}, {"admiral", "fuehrung"}, "GFK"), [])  # Admiral nie
        self.assertEqual(names.choices({"fuehrung"}, set(), None), ["gast", "freund"])


class AllianceForStatusTests(unittest.TestCase):
    """Mitglied/Führung zählt nur mit aktuellem [GFK] im Nickname UND stfc.pro-Verknüpfung."""
    class M:
        def __init__(self, uid, nick):
            self.id, self.nick = uid, nick

    def test_current_nick_and_link_required(self):
        from gfk.cogs.onboarding import alliance_for_status
        db.init()
        db.save_member_sync(7, 1, "GFK", "McRunner", 11)          # verknüpft
        db.save_member_sync(7, 2, "GFK", "Fake", None)            # GFK eingetragen, aber nicht verknüpft
        self.assertEqual(run(alliance_for_status(7, self.M(1, "[GFK] McRunner"))), "GFK")
        self.assertEqual(run(alliance_for_status(7, self.M(1, "McRunner"))), "")      # Kürzel entfernt
        self.assertEqual(run(alliance_for_status(7, self.M(1, "[ABC] McRunner"))), "ABC")
        self.assertEqual(run(alliance_for_status(7, self.M(2, "[GFK] Fake"))), "")    # ohne Verknüpfung
        self.assertEqual(run(alliance_for_status(7, self.M(3, "[GFK] Hand"))), "")    # von Hand, nie eingetragen

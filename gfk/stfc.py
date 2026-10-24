"""
GFK-Bot - Mitgliederliste der Allianz von stfc.pro (nur lesen, normale Seite, nie /api/ - siehe robots.txt).

Die Seite https://stfc.pro/alliances/<id> enthält die vollständige Mitgliederliste im eingebetteten Next.js-Payload
(self.__next_f.push). Abgerufen wird höchstens alle CACHE_SECONDS einmal (Zwischenspeicher im Arbeitsspeicher), mit
eigenem User-Agent und kurzem Timeout. Gespeichert wird nichts davon außer Spieler-ID und Name von Mitgliedern, die
sich bei der Eingangskontrolle selbst zugeordnet haben (Tabelle members).
"""
import difflib
import json
import logging
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional

import aiohttp

log = logging.getLogger("gfk.stfc")

ALLIANCE_ID = 1913611545            # GFK auf Server 401
ALLIANCE_TAG = "GFK"
URL = "https://stfc.pro/alliances/{id}"
USER_AGENT = "GFK-Bot (Discord bot of the GFK alliance; contact via stfc.pro alliance GFK)"
CACHE_SECONDS = 15 * 60
_PUSH_RE = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', re.S)


@dataclass(frozen=True)
class Player:
    player_id: int
    name: str
    tag: str
    rank: str


def parse_roster(html: str) -> Dict[int, Player]:
    """Spieler aus dem Seiten-Payload (Einträge kommen doppelt vor -> nach playerid zusammengefasst)."""
    payload = "".join(json.loads('"' + chunk + '"') for chunk in _PUSH_RE.findall(html))
    players: Dict[int, Player] = {}
    pos = 0
    while (m := payload.find('"players":[', pos)) != -1:
        start = m + len('"players":')
        depth, end = 0, None
        for i in range(start, len(payload)):
            depth += payload[i] == "["
            depth -= payload[i] == "]"
            if depth == 0:
                end = i + 1
                break
        if end is None:
            break
        try:
            for p in json.loads(payload[start:end]):
                if isinstance(p, dict) and p.get("playerid") and p.get("owner"):
                    players[int(p["playerid"])] = Player(int(p["playerid"]), str(p["owner"]), str(p.get("tag") or ""),
                                                         str(p.get("rankdesc") or ""))
        except (ValueError, TypeError):
            pass
        pos = end
    return players


def normalize(name: str) -> str:
    """Für den Vergleich: klein, ohne Akzente, ohne Leer- und Sonderzeichen."""
    name = unicodedata.normalize("NFKD", name)
    return "".join(c for c in name.lower() if c.isalnum())


def find(players: Dict[int, Player], name: str) -> Optional[Player]:
    """Exakter Treffer (nach normalize) oder None."""
    key = normalize(name)
    return next((p for p in players.values() if normalize(p.name) == key), None) if key else None


def suggestions(players: Dict[int, Player], name: str, limit: int = 5, cutoff: float = 0.6) -> List[Player]:
    """Ähnliche Namen für Tippfehler, beste zuerst."""
    by_norm = {normalize(p.name): p for p in players.values()}
    hits = difflib.get_close_matches(normalize(name), list(by_norm), n=limit, cutoff=cutoff)
    return [by_norm[h] for h in hits]


class Roster:
    """Zwischengespeicherte Mitgliederliste; get() liefert None, wenn stfc.pro nicht erreichbar ist."""

    def __init__(self, alliance_id: int = ALLIANCE_ID):
        self.alliance_id = alliance_id
        self._players: Optional[Dict[int, Player]] = None
        self._at = 0.0

    def age(self) -> float:
        """Sekunden seit dem letzten erfolgreichen Abruf (unendlich, wenn noch keiner)."""
        return time.monotonic() - self._at if self._players is not None else float("inf")

    async def get(self, session: aiohttp.ClientSession, max_age: float = CACHE_SECONDS) -> Optional[Dict[int, Player]]:
        if self._players is not None and time.monotonic() - self._at < max_age:
            return self._players
        try:
            async with session.get(URL.format(id=self.alliance_id), headers={"User-Agent": USER_AGENT},
                                   timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    log.warning("stfc.pro antwortet mit HTTP %s", resp.status)
                    return self._players
                html = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as exc:
            log.warning("stfc.pro nicht erreichbar: %s", type(exc).__name__)
            return self._players
        players = parse_roster(html)
        if not players:
            log.warning("stfc.pro: keine Mitglieder im Seiteninhalt gefunden (Format geändert?)")
            return self._players
        self._players, self._at = players, time.monotonic()
        return players

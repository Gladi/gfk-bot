"""
GFK-Bot - Vorfall-Statistik (ohne Discord-Aufrufe): wie oft wurden welche Allianzen und Spieler gemeldet.

Je Allianz eine Tabelle mit festen Spalten (RoE, 0-Node, Sonstiges, Summe, letzte 30 Tage), die gemeldeten Spieler
als Zeilen und eine Summenzeile. Feste Breite (Namen gekürzt), damit es auch auf dem Handy lesbar bleibt. Alles als
Codeblock (Discord kennt keine Tabellen), aufgeteilt auf Nachrichten unter 2000 Zeichen.
"""
from typing import Dict, Iterable, List, Tuple

ROWS = [("roe", "RoE-Verstoß"), ("nullnode", "0-Nodes"), ("sonstiges", "Sonstiges")]
SHORT = {"roe": "RoE", "nullnode": "0-N", "sonstiges": "Son"}
NO_ALLIANCE = "ohne Allianz"
NAME_W = 14                   # Breite der Namensspalte (längere Namen werden gekürzt)
MESSAGE_MAX = 1900
DAYS = 30


def norm_alliance(raw: str) -> str:
    tag = (raw or "").strip().strip("[]()").strip().upper()
    return tag or NO_ALLIANCE


def _total(counts: Dict[str, int]) -> int:
    return sum(counts.values())


def _clip(name: str) -> str:
    return name if len(name) <= NAME_W else name[:NAME_W - 1] + "…"


def _row(label: str, counts: Dict[str, int], recent: int) -> str:
    cells = [str(counts.get(cat, 0)) if counts.get(cat, 0) else "·" for cat, _ in ROWS]
    return f"{label:<{NAME_W}} │ " + " │ ".join(f"{c:>3}" for c in cells) + \
        f" │ {_total(counts):>3} │ {recent or '·':>3}"


def _rule() -> str:
    return "─" * (NAME_W + 1) + "┼" + "┼".join(["─────"] * 5)[:-1]


def render(reports: Iterable[Tuple[str, str, str, float]], header: str, now: float) -> List[str]:
    """reports: (Kategorie, Allianz, Spieler, Zeitpunkt als Unix-Zeit) -> Nachrichten für den Statistik-Beitrag.
    Allianzen mit den meisten Meldungen zuerst, "ohne Allianz" zuletzt; Spieler ohne Groß/Klein-Unterschied
    zusammengefasst (es gilt die zuerst gemeldete Schreibweise)."""
    reports = list(reports)
    since = now - DAYS * 86400
    data: Dict[str, Dict[str, Dict[str, int]]] = {}
    recent: Dict[Tuple[str, str], int] = {}
    spelling: Dict[Tuple[str, str], str] = {}
    for category, alliance, player, at in reports:
        cat = category if category in SHORT else "sonstiges"
        ally = norm_alliance(alliance)
        name = " ".join((player or "?").split())
        name = spelling.setdefault((ally, name.casefold()), name)
        cell = data.setdefault(ally, {}).setdefault(name, {})
        cell[cat] = cell.get(cat, 0) + 1
        if at >= since:
            recent[(ally, name)] = recent.get((ally, name), 0) + 1
    per_cat = {cat: sum(c.get(cat, 0) for p in data.values() for c in p.values()) for cat, _ in ROWS}
    allies = len([a for a in data if a != NO_ALLIANCE])
    parts = [header + (f"\n{len(reports)} Meldungen · {allies} Allianzen · " +
                       " · ".join(f"{label} {per_cat[cat]}" for cat, label in ROWS) if reports
                       else "\nNoch keine Meldungen.")]
    head = [f"{'Spieler':<{NAME_W}} │ " + " │ ".join(f"{SHORT[c]:>3}" for c, _ in ROWS) + " │   Σ │ 30T", _rule()]
    for ally in sorted(data, key=lambda a: (a == NO_ALLIANCE, -sum(_total(c) for c in data[a].values()), a)):
        players = data[ally]
        order = sorted(players, key=lambda p: (-_total(players[p]), -recent.get((ally, p), 0), p.casefold()))
        sums = {cat: sum(players[p].get(cat, 0) for p in order) for cat, _ in ROWS}
        ally_recent = sum(recent.get((ally, p), 0) for p in order)
        rows = [_row(_clip(p), players[p], recent.get((ally, p), 0)) for p in order]
        foot = [_rule(), _row("Gesamt", sums, ally_recent)] if len(order) > 1 else []
        label = f"[{ally}]" if ally != NO_ALLIANCE else NO_ALLIANCE
        title = f"**{label}** · {_total(sums)} Meldung{'en' if _total(sums) != 1 else ''}" + \
                (f" · {ally_recent} in den letzten {DAYS} Tagen" if ally_recent else "")
        blocks, chunk = [], []                       # sehr große Allianzen auf mehrere Blöcke verteilen
        for row in rows:
            if chunk and len("\n".join(head + chunk + [row])) > MESSAGE_MAX - 250:
                blocks.append(chunk)
                chunk = []
            chunk.append(row)
        blocks.append(chunk)
        for i, block in enumerate(blocks):
            body = head + block + (foot if i == len(blocks) - 1 else [])
            parts.append(title + ("" if i == 0 else " (Fortsetzung)") + "\n```\n" + "\n".join(body) + "\n```")
    parts.append(f"-# RoE = RoE-Verstoß · 0-N = 0-Node · Son = Sonstiges · Σ = gesamt · 30T = letzte {DAYS} Tage "
                 "· · = keine")
    messages, current = [], ""
    for part in parts:
        if current and len(current) + len(part) + 2 > MESSAGE_MAX:
            messages.append(current)
            current = part
        else:
            current = f"{current}\n\n{part}" if current else part
    messages.append(current)
    return messages

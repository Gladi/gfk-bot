"""GFK-Bot - Nicknames und Status-Rollen (reine Logik ohne Discord-Aufrufe, gut testbar)."""
import re
from typing import Iterable, List, Optional, Set, Tuple

MAX_NICK = 32                    # Discord-Grenze für Server-Nicknames
MAX_TAG = 6
TAG_RE = re.compile(r"^[^\W_]{1,6}$")   # Buchstaben/Ziffern, auch Ø, Ä …


def clean_tag(raw: str) -> Optional[str]:
    """Allianzkürzel: Klammern/Leerzeichen weg, Großbuchstaben. Leer -> None (kein Kürzel). Ungültig -> ValueError."""
    tag = raw.strip().strip("[]()").strip().upper()
    if not tag:
        return None
    if not TAG_RE.fullmatch(tag):
        raise ValueError(tag)
    return tag


def clean_name(raw: str) -> str:
    name = " ".join(raw.split())
    if not name:
        raise ValueError("leer")
    return name


def nickname(tag: Optional[str], name: str) -> str:
    """`[TAG] Name` bzw. `Name`; ist es zu lang, wird der Name gekürzt, nie das Kürzel."""
    prefix = f"[{tag}] " if tag else ""
    room = MAX_NICK - len(prefix)
    return prefix + (name if len(name) <= room else name[:room - 1].rstrip() + "…")


# Status-Rollen (Schlüssel aus settings.STATUS_ROLES) - wer darf wen wozu machen
GFK_ONLY = {"mitglied", "fuehrung"}    # nur für Personen mit dem Allianzkürzel GFK


def allowed_for_alliance(target: str, alliance: Optional[str], gfk_tag: str = "GFK") -> bool:
    """Mitglied und Führung nur mit GFK-Kürzel; Freund und Gast für alle."""
    return target not in GFK_ONLY or (alliance or "").upper() == gfk_tag


NICK_TAG_RE = re.compile(r"^\[([^\W_]{1,6})\]\s*")


def tag_of_nick(nick: Optional[str]) -> Optional[str]:
    """Kürzel aus einem Nickname wie "[GFK] Name" (groß geschrieben) oder None."""
    m = NICK_TAG_RE.match(nick or "")
    return m.group(1).upper() if m else None


def loses_gfk_status(status: Set[str], tag: Optional[str], gfk_tag: str = "GFK") -> bool:
    """Mitglied oder Führung ohne GFK-Kürzel -> zurück zu Gast (der Admiral wird nie automatisch geändert)."""
    return bool(status & GFK_ONLY) and "admiral" not in status and (tag or "").upper() != gfk_tag


GRANTABLE_BY_FUEHRUNG = ["gast", "freund", "mitglied"]
GRANTABLE_BY_ADMIRAL = ["gast", "freund", "mitglied", "fuehrung"]


def may_grant(actor_status: Set[str], target: str, current_target_status: Set[str]) -> bool:
    """actor_status = Status-Rollen des Handelnden ("admiral", "fuehrung" …). Führung vergibt Gast/Freund/Mitglied,
    der Admiral zusätzlich Führung; wer schon Führung ist, kann nur der Admiral wieder ändern."""
    if "admiral" in actor_status:
        allowed = GRANTABLE_BY_ADMIRAL
    elif "fuehrung" in actor_status:
        allowed = GRANTABLE_BY_FUEHRUNG
    else:
        return False
    if current_target_status & {"admiral", "fuehrung"} and "admiral" not in actor_status:
        return False
    if "admiral" in current_target_status:
        return False                       # den Admiral ändert der Bot nie
    return target in allowed


def status_change(current: Iterable[str], target: str, all_status: List[str]) -> Tuple[List[str], List[str]]:
    """(entfernen, hinzufügen): genau eine Status-Rolle; der Admiral bleibt immer, wie er ist."""
    current = set(current)
    remove = [s for s in all_status if s in current and s != target and s != "admiral"]
    add = [] if target in current else [target]
    return remove, add


STATUS_ORDER = ["gast", "freund", "mitglied", "fuehrung"]


def choices(actor_status: Set[str], target_status: Set[str], alliance: Optional[str], gfk_tag: str = "GFK") -> List[str]:
    """Status, die der Handelnde der Person geben darf (ohne den, den sie schon allein hat)."""
    out = []
    for target in STATUS_ORDER:
        if not may_grant(actor_status, target, target_status) or not allowed_for_alliance(target, alliance, gfk_tag):
            continue
        if target_status - {"admiral"} == {target}:
            continue
        out.append(target)
    return out


# Wer den Bot nutzen darf (Meldungen, Events): nur allianzintern
INTERNAL = {"mitglied", "fuehrung", "admiral"}
LEAD = {"fuehrung", "admiral"}            # der Admiral zählt zur Führung


def is_internal(status: Set[str]) -> bool:
    return bool(status & INTERNAL)


def is_lead(status: Set[str]) -> bool:
    return bool(status & LEAD)

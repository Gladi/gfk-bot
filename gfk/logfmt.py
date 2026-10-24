"""GFK-Bot - Hilfen für die Server-Logs: Vergleiche, Kürzen, Nachrichten-Zwischenspeicher (ohne Discord-Aufrufe)."""
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

FIELD_MAX = 1024             # Discord-Grenze für ein Embed-Feld
NEW_ACCOUNT_DAYS = 7         # jüngere Konten werden im Beitritts-Log hervorgehoben

# Lesbare Namen für die wichtigsten Rechte (Rest: Originalname)
PERM_NAMES = {
    "administrator": "Administrator", "manage_guild": "Server verwalten", "manage_roles": "Rollen verwalten",
    "manage_channels": "Kanäle verwalten", "kick_members": "Mitglieder kicken", "ban_members": "Mitglieder bannen",
    "moderate_members": "Timeout vergeben", "manage_messages": "Nachrichten verwalten", "mention_everyone": "@everyone erwähnen",
    "manage_nicknames": "Nicknames verwalten", "manage_webhooks": "Webhooks verwalten", "view_audit_log": "Audit-Log anzeigen",
    "view_channel": "Kanal sehen", "send_messages": "Nachrichten senden", "read_message_history": "Verlauf lesen",
    "connect": "Sprachkanal betreten", "speak": "Sprechen", "manage_threads": "Threads verwalten",
    "create_public_threads": "Öffentliche Threads", "create_private_threads": "Private Threads",
    "attach_files": "Dateien anhängen", "embed_links": "Links einbetten", "add_reactions": "Reaktionen",
    "manage_events": "Events verwalten", "create_events": "Events erstellen",
}


def clip(text: Optional[str], limit: int = FIELD_MAX) -> str:
    text = (text or "").strip() or "–"
    return text if len(text) <= limit else text[:limit - 1] + "…"


def perm_name(name: str) -> str:
    return PERM_NAMES.get(name, name)


def perm_diff(before: Iterable[Tuple[str, bool]], after: Iterable[Tuple[str, bool]]) -> Tuple[List[str], List[str]]:
    """(neu erlaubt, entzogen) zwischen zwei Permissions-Objekten (iterierbar als (name, wert))."""
    b, a = dict(before), dict(after)
    added = [perm_name(k) for k, v in a.items() if v and not b.get(k)]
    removed = [perm_name(k) for k, v in b.items() if v and not a.get(k)]
    return added, removed


def overwrite_diff(before: Dict[str, Dict[str, Optional[bool]]], after: Dict[str, Dict[str, Optional[bool]]]) -> List[str]:
    """Rechte-Überschreibungen eines Kanals: {Ziel: {recht: True/False/None}} vorher/nachher -> Zeilen."""
    lines = []
    for target in sorted(set(before) | set(after)):
        b, a = before.get(target), after.get(target)
        if b is None:
            lines.append(f"➕ {target}")
            b = {}
        elif a is None:
            lines.append(f"➖ {target}")
            continue
        changes = []
        for perm in sorted(set(b) | set(a)):
            vb, va = b.get(perm), a.get(perm)
            if vb != va:
                sym = {True: "✅", False: "❌", None: "➖"}[va]
                changes.append(f"{sym} {perm_name(perm)}")
        if changes:
            lines.append(f"{target}: " + ", ".join(changes))
    return lines


def account_age(created: float, now: Optional[float] = None) -> Tuple[str, bool]:
    """("vor 3 Tagen" o. ä., ist_neu)."""
    days = int(((now or time.time()) - created) // 86400)
    if days < 1:
        text = "heute"
    elif days == 1:
        text = "vor 1 Tag"
    elif days < 60:
        text = f"vor {days} Tagen"
    elif days < 730:
        text = f"vor {days // 30} Monaten"
    else:
        text = f"vor {days // 365} Jahren"
    return text, days < NEW_ACCOUNT_DAYS


@dataclass
class Cached:
    channel_id: int
    author_id: int
    content: str
    attachments: List[str] = field(default_factory=list)
    at: float = field(default_factory=time.time)


class MessageCache:
    """Zuletzt gesehene Nachrichten - NUR im Arbeitsspeicher (nichts auf der Platte, nach einem Neustart leer).
    Begrenzt auf max_age Sekunden und max_items Einträge (älteste fliegen zuerst)."""

    def __init__(self, max_age: float, max_items: int = 50_000):
        self.max_age, self.max_items = max_age, max_items
        self._data: "OrderedDict[int, Cached]" = OrderedDict()

    def put(self, message_id: int, item: Cached):
        self._data[message_id] = item
        self._data.move_to_end(message_id)
        while len(self._data) > self.max_items:
            self._data.popitem(last=False)

    def get(self, message_id: int) -> Optional[Cached]:
        item = self._data.get(message_id)
        if item is not None and time.time() - item.at > self.max_age:
            del self._data[message_id]
            return None
        return item

    def pop(self, message_id: int) -> Optional[Cached]:
        item = self.get(message_id)
        self._data.pop(message_id, None)
        return item

    def prune(self, now: Optional[float] = None) -> int:
        now = now or time.time()
        old = [k for k, v in self._data.items() if now - v.at > self.max_age]
        for k in old:
            del self._data[k]
        return len(old)

    def __len__(self):
        return len(self._data)

"""
GFK-Bot - Events ohne Discord-Aufrufe: Eingaben (Datum, Dauer), was wann fällig ist (Sprachkanal, Erinnerung, Start,
Ende, Aufräumen) und Namen/Zeitangaben. Zeiten intern immer als UTC, Ein- und Ausgabe in Europe/Berlin.
"""
import datetime as dt
import re
from typing import Optional, Set
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")
UTC = dt.timezone.utc

# Schlüssel -> (Anzeige, Emoji)
CATEGORIES = {"armada": ("Armada", "⚔️"), "welle": ("Welle", "🌊"), "ansturm": ("Ansturm", "🔥"),
              "sonstiges": ("Sonstiges", "📌")}
KINDS = ("alliance", "private")

VOICE_LEAD = dt.timedelta(hours=1)          # Sprachkanal (und Discord-Event-Ort) so lange vor Beginn
MAX_AHEAD = dt.timedelta(days=365)
DURATION_DEFAULT, DURATION_MIN, DURATION_MAX = 60, 15, 24 * 60   # Minuten

REMIND_BIT, START_BIT = 1, 2                 # Spalte events.reminded: Vorlauf-Erinnerung / Start-Hinweis gesendet

WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
_WHEN_RE = re.compile(
    r"^(?:(?P<word>heute|morgen|übermorgen)|(?P<d>\d{1,2})\.(?P<m>\d{1,2})\.?(?P<y>\d{2,4})?)?"
    r"\s*(?:um\s*)?(?P<H>\d{1,2})[:.](?P<M>\d{2})\s*(?:uhr)?$", re.I)


def parse_when(text: str, now: dt.datetime) -> dt.datetime:
    """"25.10.2026 20:00", "25.10. 20:00", "morgen 20:00", "20:00" (heute, sonst morgen) -> UTC.
    ValueError("format" | "past" | "far")."""
    m = _WHEN_RE.match(" ".join((text or "").split()).lower())
    if not m:
        raise ValueError("format")
    local_now = now.astimezone(TZ)
    hour, minute = int(m["H"]), int(m["M"])
    try:
        if m["d"]:
            year = int(m["y"]) if m["y"] else local_now.year
            year += 2000 if year < 100 else 0
            day = dt.date(year, int(m["m"]), int(m["d"]))
            if not m["y"] and day < local_now.date():
                day = day.replace(year=year + 1)          # "05.01." im Dezember = nächstes Jahr
        else:
            offset = {"heute": 0, "morgen": 1, "übermorgen": 2}.get(m["word"] or "", 0)
            day = local_now.date() + dt.timedelta(days=offset)
        local = dt.datetime.combine(day, dt.time(hour, minute), tzinfo=TZ)
    except ValueError:
        raise ValueError("format") from None
    if not m["d"] and not m["word"] and local <= local_now:
        local += dt.timedelta(days=1)                      # nur Uhrzeit, schon vorbei -> morgen
    start = local.astimezone(UTC)
    if start <= now + dt.timedelta(minutes=1):
        raise ValueError("past")
    if start > now + MAX_AHEAD:
        raise ValueError("far")
    return start


def parse_duration(text: Optional[str]) -> int:
    """"" -> 60; "2", "1,5", "2h", "2 std" -> Stunden; "90", "90min" -> Minuten; "1:30" -> 90. ValueError("duration")."""
    raw = (text or "").strip().lower().replace(",", ".").replace(" ", "")
    if not raw:
        return DURATION_DEFAULT
    m = re.fullmatch(r"(\d{1,2}):(\d{2})h?", raw)
    if m:
        minutes = int(m[1]) * 60 + int(m[2])
    else:
        m = re.fullmatch(r"(\d+(?:\.\d+)?)(h|std|stunden?|m|min|minuten)?", raw)
        if not m:
            raise ValueError("duration")
        value, unit = float(m[1]), m[2]
        hours = unit in ("h", "std", "stunde", "stunden") or (unit is None and value <= 24)
        minutes = round(value * 60) if hours else round(value)
    if not DURATION_MIN <= minutes <= DURATION_MAX:
        raise ValueError("duration")
    return minutes


def due(start: dt.datetime, end: dt.datetime, status: str, has_voice: bool, reminded: int, now: dt.datetime,
        reminder_minutes: int) -> Set[str]:
    """Was der Minuten-Task für ein Event tun muss: voice, remind, start, end, cleanup."""
    out = set()
    if status == "planned":
        if now >= end:
            return {"end"}
        if not has_voice and now >= start - VOICE_LEAD:
            out.add("voice")
        if now >= start:
            if not reminded & START_BIT:
                out.add("start")
        elif not reminded & REMIND_BIT and now >= start - dt.timedelta(minutes=reminder_minutes):
            out.add("remind")
    elif status in ("ended", "cancelled") and now >= end:
        out.add("cleanup")
    return out


def initial_reminded(start: dt.datetime, now: dt.datetime, reminder_minutes: int) -> int:
    """Event erst kurz vor Beginn angelegt -> keine Vorlauf-Erinnerung mehr (nur der Start-Hinweis)."""
    return REMIND_BIT if start - now <= dt.timedelta(minutes=reminder_minutes) else 0


# ----------------- Anzeige -----------------
def local(ts: dt.datetime) -> dt.datetime:
    return ts.astimezone(TZ)


def short_time(ts: dt.datetime) -> str:
    """"Sa 25.10. 20:00" (Berliner Zeit)."""
    t = local(ts)
    return f"{WEEKDAYS[t.weekday()]} {t:%d.%m. %H:%M}"


def input_value(ts: dt.datetime) -> str:
    """Vorbelegung im Formular: "25.10.2026 20:00"."""
    return f"{local(ts):%d.%m.%Y %H:%M}"


def duration_text(minutes: int) -> str:
    hours, rest = divmod(minutes, 60)
    if not hours:
        return f"{rest} min"
    return f"{hours} h" if not rest else f"{hours}:{rest:02d} h"


def duration_input(minutes: int) -> str:
    hours, rest = divmod(minutes, 60)
    return str(hours) if not rest else f"{hours}:{rest:02d}"


def label(category: str) -> str:
    return CATEGORIES.get(category, CATEGORIES["sonstiges"])[0]


def emoji(category: str) -> str:
    return CATEGORIES.get(category, CATEGORIES["sonstiges"])[1]


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def voice_name(category: str, start: dt.datetime) -> str:
    return _clip(f"🔊 {label(category)} {local(start):%d.%m. %H:%M}", 100)


def thread_name(category: str, start: dt.datetime, description: Optional[str]) -> str:
    base = f"{emoji(category)} {label(category)} {local(start):%d.%m. %H:%M}"
    first = " ".join((description or "").split())
    return _clip(f"{base} – {first}" if first else base, 100)


def event_name(category: str, description: Optional[str]) -> str:
    """Name des Discord-Events."""
    first = " ".join((description or "").split())
    return _clip(f"{label(category)}: {first}" if first else label(category), 100)


def iso(ts: dt.datetime) -> str:
    return ts.astimezone(UTC).isoformat(timespec="seconds")


def from_iso(text: str) -> dt.datetime:
    ts = dt.datetime.fromisoformat(text)
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


def mention_chunks(user_ids, prefix: str = "", limit: int = 1900):
    """Erwähnungen auf mehrere Nachrichten verteilen (Discord: 2000 Zeichen)."""
    chunk = prefix
    for uid in user_ids:
        part = f"<@{uid}> "
        if len(chunk) + len(part) > limit:
            yield chunk.rstrip()
            chunk = ""
        chunk += part
    if chunk.strip():
        yield chunk.rstrip()

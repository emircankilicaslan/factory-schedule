"""Operasyon güncelleme iş kuralları (veritabanından bağımsız, saf fonksiyonlar).

R1 – Öncelik: bir operasyon, aynı iş emrindeki önceki operasyon bitmeden başlayamaz;
     sonraki operasyonun başlangıcı da yeni bitişten önce olamaz.
R2 – Hat (makine) tekilliği: aynı makinedeki operasyonlar zamanda çakışamaz.
R3 – Geçmiş yasak: başlangıç "şimdi"den önce olamaz.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional, Protocol


class _Timed(Protocol):
    id: str
    start: datetime
    end: datetime


class RuleViolation(Exception):
    """Bir iş kuralı ihlal edildiğinde fırlatılır; `code` kural kimliğidir (R1, R2, R3, INVALID)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def as_utc(dt: datetime) -> datetime:
    """Saat dilimi olmayan zamanları UTC kabul eder (SQLite gibi sürücüler naive döner)."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def validate_update(
    start: datetime,
    end: datetime,
    previous: Optional[_Timed],
    following: Optional[_Timed],
    lane_ops: Iterable[_Timed],
    now: datetime,
) -> tuple[datetime, datetime]:
    """Yeni (start, end) değerlerini kurallara göre doğrular ve UTC'ye normalize edip döndürür."""
    start, end, now = as_utc(start), as_utc(end), as_utc(now)

    if end <= start:
        raise RuleViolation("INVALID", "End must be after start.")

    if previous is not None and start < as_utc(previous.end):
        raise RuleViolation(
            "R1",
            f"R1 violation: Operation must start at or after previous operation ends "
            f"({previous.id} ends {as_utc(previous.end).isoformat()}).",
        )
    if following is not None and end > as_utc(following.start):
        raise RuleViolation(
            "R1",
            f"R1 violation: Operation must end at or before the next operation starts "
            f"({following.id} starts {as_utc(following.start).isoformat()}).",
        )

    for other in lane_ops:
        o_start, o_end = as_utc(other.start), as_utc(other.end)
        if start < o_end and end > o_start:
            raise RuleViolation(
                "R2",
                f"R2 violation: Overlaps with operation {other.id} on the same machine "
                f"({o_start.isoformat()}–{o_end.isoformat()}).",
            )

    if start < now:
        raise RuleViolation(
            "R3", f"R3 violation: Start {start.isoformat()} is before now {now.isoformat()}."
        )

    return start, end
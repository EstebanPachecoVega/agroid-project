"""Rate limiting en memoria para proteger el agente y la cuota del proveedor.

En producción este estado debería vivir en Redis para sobrevivir reinicios y
compartirse entre réplicas. Para la demostración académica se usa memoria del
proceso, con trazabilidad de cada bloqueo.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass
class RateLimitDecision:
    allowed: bool
    reason: str = ""
    retry_after: float = 0.0
    session_remaining_minute: int = 0
    global_remaining_minute: int = 0
    turns_remaining_today: int = 0
    active: int = 0


class RateLimiter:
    def __init__(
        self,
        per_minute: int = 15,
        per_minute_global: int = 15,
        turns_per_day: int = 45,
        max_concurrent: int = 3,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.per_minute = max(1, int(per_minute))
        self.per_minute_global = max(1, int(per_minute_global))
        self.turns_per_day = max(1, int(turns_per_day))
        self.max_concurrent = max(1, int(max_concurrent))
        self.on_event = on_event
        self._lock = threading.Lock()
        self._session_minute: dict[str, deque[float]] = {}
        self._global_minute: deque[float] = deque()
        self._day = self._today()
        self._turns_today = 0
        self._llm_requests_today = 0
        self._active = 0
        self._denied = 0
        self._last_denial: str = ""

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def _prune(self, now: float) -> None:
        cutoff = now - 60.0
        while self._global_minute and self._global_minute[0] < cutoff:
            self._global_minute.popleft()
        for session_id, queue in list(self._session_minute.items()):
            while queue and queue[0] < cutoff:
                queue.popleft()
            if not queue:
                self._session_minute.pop(session_id, None)

    def _emit(self, decision: RateLimitDecision, session_id: str) -> None:
        if self.on_event and not decision.allowed:
            self.on_event(
                {
                    "event_type": "rate_limit",
                    "session_id": session_id,
                    "reason": decision.reason,
                    "retry_after": decision.retry_after,
                    "turns_remaining_today": decision.turns_remaining_today,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    def acquire(self, session_id: str = "demo") -> RateLimitDecision:
        session_id = session_id or "demo"
        with self._lock:
            now = time.monotonic()
            today = self._today()
            if today != self._day:
                self._day = today
                self._turns_today = 0
                self._llm_requests_today = 0
            self._prune(now)

            remaining_turns = max(0, self.turns_per_day - self._turns_today)
            if self._active >= self.max_concurrent:
                decision = RateLimitDecision(
                    allowed=False,
                    reason="concurrencia_maxima",
                    retry_after=1.0,
                    session_remaining_minute=max(
                        0, self.per_minute - len(self._session_minute.get(session_id, ()))
                    ),
                    global_remaining_minute=max(
                        0, self.per_minute_global - len(self._global_minute)
                    ),
                    turns_remaining_today=remaining_turns,
                    active=self._active,
                )
            elif self._turns_today >= self.turns_per_day:
                decision = RateLimitDecision(
                    allowed=False,
                    reason="cuota_diaria",
                    retry_after=3600.0,
                    turns_remaining_today=0,
                    active=self._active,
                )
            elif len(self._global_minute) >= self.per_minute_global:
                decision = RateLimitDecision(
                    allowed=False,
                    reason="rpm_global",
                    retry_after=60.0 - (now - self._global_minute[0]),
                    global_remaining_minute=0,
                    turns_remaining_today=remaining_turns,
                    active=self._active,
                )
            else:
                queue = self._session_minute.setdefault(session_id, deque())
                if len(queue) >= self.per_minute:
                    decision = RateLimitDecision(
                        allowed=False,
                        reason="rpm_sesion",
                        retry_after=60.0 - (now - queue[0]),
                        session_remaining_minute=0,
                        global_remaining_minute=max(
                            0, self.per_minute_global - len(self._global_minute)
                        ),
                        turns_remaining_today=remaining_turns,
                        active=self._active,
                    )
                else:
                    queue.append(now)
                    self._global_minute.append(now)
                    self._turns_today += 1
                    self._active += 1
                    decision = RateLimitDecision(
                        allowed=True,
                        session_remaining_minute=max(
                            0, self.per_minute - len(queue)
                        ),
                        global_remaining_minute=max(
                            0, self.per_minute_global - len(self._global_minute)
                        ),
                        turns_remaining_today=max(
                            0, self.turns_per_day - self._turns_today
                        ),
                        active=self._active,
                    )
            if not decision.allowed:
                self._denied += 1
                self._last_denial = decision.reason
        self._emit(decision, session_id)
        return decision

    def release(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)

    def note_llm_requests(self, n: int = 1) -> None:
        with self._lock:
            if self._today() != self._day:
                self._day = self._today()
                self._turns_today = 0
                self._llm_requests_today = 0
            self._llm_requests_today += max(0, int(n))

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "day": self._day,
                "turns_today": self._turns_today,
                "turns_remaining_today": max(
                    0, self.turns_per_day - self._turns_today
                ),
                "llm_requests_today": self._llm_requests_today,
                "active": self._active,
                "denied": self._denied,
                "last_denial": self._last_denial,
                "per_minute": self.per_minute,
                "per_minute_global": self.per_minute_global,
                "turns_per_day": self.turns_per_day,
                "max_concurrent": self.max_concurrent,
            }

    def reset(self) -> None:
        with self._lock:
            self._session_minute.clear()
            self._global_minute.clear()
            self._day = self._today()
            self._turns_today = 0
            self._llm_requests_today = 0
            self._active = 0
            self._denied = 0
            self._last_denial = ""

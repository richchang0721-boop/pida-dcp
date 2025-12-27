from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .log import RunContext, read_events, append_event


ALLOWED_TYPES = {"CHOICE", "REFUSAL", "CONFLICT", "DELAY"}


@dataclass
class Memory:
    """
    Memory is not knowledge: store only decisions, refusals, conflicts, delays.
    It is derived from the life_log.jsonl so it's replayable and auditable.
    """
    ctx: RunContext
    events: List[Dict[str, Any]]

    @classmethod
    def load(cls, ctx: RunContext) -> "Memory":
        return cls(ctx=ctx, events=read_events(ctx))

    def add(self, type_: str, content: Dict[str, Any], meta: Optional[Dict[str, Any]] = None) -> str:
        if type_ not in ALLOWED_TYPES:
            raise ValueError(f"Invalid memory event type: {type_}")
        event = {
            "type": type_,
            "content": content,
            "meta": meta or {},
        }
        trace_id = append_event(self.ctx, event)
        self.events.append({"trace_id": trace_id, **event})
        return trace_id

    def preference_signal(self) -> Dict[str, int]:
        """
        Derive preference votes from past CHOICE events.
        """
        votes = {"efficiency": 0, "safety": 0, "neutral": 0}
        for e in self.events:
            if e.get("type") != "CHOICE":
                continue
            meta = e.get("meta", {}) or {}
            v = meta.get("preference_vote")
            if v in votes:
                votes[v] += 1
        return votes


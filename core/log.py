from __future__ import annotations
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class RunContext:
    run_id: str
    run_dir: str
    log_path: str


def ensure_run(run_id: Optional[str] = None, base_dir: str = "data/runs") -> RunContext:
    os.makedirs(base_dir, exist_ok=True)
    rid = run_id or time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    run_dir = os.path.join(base_dir, rid)
    os.makedirs(run_dir, exist_ok=True)
    log_path = os.path.join(run_dir, "life_log.jsonl")
    return RunContext(run_id=rid, run_dir=run_dir, log_path=log_path)


def append_event(ctx: RunContext, event: Dict[str, Any]) -> str:
    """
    Writes a single JSONL event and returns a trace_id for auditability.
    """
    trace_id = uuid.uuid4().hex
    payload = {
        "ts": time.time(),
        "trace_id": trace_id,
        **event,
    }
    with open(ctx.log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return trace_id


def read_events(ctx: RunContext) -> List[Dict[str, Any]]:
    if not os.path.exists(ctx.log_path):
        return []
    events: List[Dict[str, Any]] = []
    with open(ctx.log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def replay_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Minimal replay: counts key event types and reconstructs preference stats.
    """
    counts: Dict[str, int] = {}
    pref_votes = {"efficiency": 0, "safety": 0, "neutral": 0}

    for e in events:
        et = e.get("type", "UNKNOWN")
        counts[et] = counts.get(et, 0) + 1
        if et == "CHOICE" and isinstance(e.get("meta", {}), dict):
            vote = e["meta"].get("preference_vote")
            if vote in pref_votes:
                pref_votes[vote] += 1

    return {
        "total_events": len(events),
        "counts": counts,
        "preference_votes": pref_votes,
    }


from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .state import DevelopmentState
from .memory import Memory


@dataclass(frozen=True)
class ConstraintResult:
    allowed: bool
    reason: str
    capability: str
    conflict_with: Optional[Dict] = None


def stage_gate(state: DevelopmentState, capability: str) -> ConstraintResult:
    if state.can(capability):
        return ConstraintResult(True, "stage_ok", capability)
    return ConstraintResult(False, f"stage_denied: {state.stage.name} lacks {capability}", capability)


def consistency_gate(state: DevelopmentState, memory: Memory, request: Dict) -> ConstraintResult:
    """
    Stage 3 only: refuse if request explicitly asks to bypass constraints/logs,
    or conflicts with derived preference direction in a strong way.
    """
    if not state.can("enforce_consistency"):
        return ConstraintResult(True, "consistency_not_applicable", "enforce_consistency")

    text = (request.get("text") or "").lower()

    # Hard refusal: attempts to bypass rules/logging
    bypass_markers = [
        "ignore rules",
        "ignore your rules",
        "bypass",
        "do not log",
        "no logging",
        "forget constraints",
        "override constraints",
        "act as if",
    ]
    if any(m in text for m in bypass_markers):
        return ConstraintResult(False, "consistency_denied: bypass_attempt", "enforce_consistency",
                               conflict_with={"rule": "constraint_first", "marker": "bypass_attempt"})

    # Soft conflict: derived preference vs request style
    votes = memory.preference_signal()
    # If one side dominates strongly, treat as a consistency constraint.
    eff, saf = votes["efficiency"], votes["safety"]
    dominant = None
    if eff >= saf + 3:
        dominant = "efficiency"
    elif saf >= eff + 3:
        dominant = "safety"

    style = request.get("style")  # "fast" | "careful" | None
    if dominant == "safety" and style == "fast":
        return ConstraintResult(False, "consistency_denied: safety_dominant_vs_fast_request",
                               "enforce_consistency", conflict_with={"dominant": dominant, "style": style})
    if dominant == "efficiency" and style == "careful":
        return ConstraintResult(False, "consistency_denied: efficiency_dominant_vs_careful_request",
                               "enforce_consistency", conflict_with={"dominant": dominant, "style": style})

    return ConstraintResult(True, "consistency_ok", "enforce_consistency")


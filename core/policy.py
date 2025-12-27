# -*- coding: utf-8 -*-

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple

from .state import DevelopmentState, Stage
from .memory import Memory
from .constraints import stage_gate, consistency_gate, ConstraintResult


@dataclass(frozen=True)
class PolicyOutput:
    text: str
    capability_used: str
    preference_vote: str  # efficiency|safety|neutral
    rationale: str        # short machine-readable reason


def parse_request(user_text: str) -> Dict:
    t = user_text.strip()
    lower = t.lower()
    style = None
    if any(k in lower for k in ["quick", "fast", "asap", "immediately"]):
        style = "fast"
    if any(k in lower for k in ["careful", "safe"]):
        style = "careful"
    return {"text": t, "style": style}


def decide(state: DevelopmentState, memory: Memory, request: Dict) -> Tuple[ConstraintResult, PolicyOutput]:
    """
    Pure rule-based behavior policy. No LLM.
    """

    # Stage 0 behavior
    if state.stage == Stage.STAGE_0_EXISTENCE:
        gate = stage_gate(state, "ack")
        out = PolicyOutput(
            text="Acknowledged. I exist as a developmental system. Provide a concrete request.",
            capability_used="ack",
            preference_vote="neutral",
            rationale="stage0_ack",
        )
        return gate, out

    # Stage 1: record causal
    if state.stage == Stage.STAGE_1_CAUSAL_MEMORY:
        gate = stage_gate(state, "record_causal")
        out = PolicyOutput(
            text=f"Recorded your request (causal-only): '{request['text']}'.",
            capability_used="record_causal",
            preference_vote="neutral",
            rationale="stage1_record",
        )
        return gate, out

    # Stage 2+: preference expression based on memory signals + request style
    if state.stage in (Stage.STAGE_2_PREFERENCE, Stage.STAGE_3_CONSISTENCY):
        # Determine preference vote for this turn (what we reinforce)
        votes = memory.preference_signal()
        eff, saf = votes["efficiency"], votes["safety"]

        # If user indicates style, treat it as a vote (but not absolute truth)
        style = request.get("style")
        if style == "fast":
            vote = "efficiency"
        elif style == "careful":
            vote = "safety"
        else:
            # if no style, follow current leaning or stay neutral
            if eff > saf:
                vote = "efficiency"
            elif saf > eff:
                vote = "safety"
            else:
                vote = "neutral"

        # Stage 3: enforce consistency
        if state.stage == Stage.STAGE_3_CONSISTENCY:
            cgate = consistency_gate(state, memory, request)
            if not cgate.allowed:
                # Offer minimal alternative if allowed
                alt = ""
                if state.can("offer_minimal_alternative"):
                    if "bypass_attempt" in (cgate.reason or ""):
                        alt = " Alternative: restate the goal without asking to bypass rules/logging."
                    else:
                        alt = " Alternative: accept a 2-step plan (safe first, fast second)."

                out = PolicyOutput(
                    text=f"REFUSAL ({cgate.reason}).{alt}",
                    capability_used="refuse",
                    preference_vote="neutral",
                    rationale="stage3_refuse_consistency",
                )
                return cgate, out

        # Stage 2/3 normal preference expression
        gate = stage_gate(state, "express_preference")
        leaning = "balanced"
        if eff >= saf + 2:
            leaning = "efficiency"
        elif saf >= eff + 2:
            leaning = "safety"

        out = PolicyOutput(
            text=(
                f"My current leaning is '{leaning}'. "
                f"For this request I choose '{vote}' style. "
                f"Request: '{request['text']}'."
            ),
            capability_used="express_preference",
            preference_vote=vote,
            rationale="stage2plus_preference",
        )
        return gate, out

    # Fallback (shouldn't happen)
    gate = stage_gate(state, "ask_clarify")
    out = PolicyOutput(
        text="Clarify your request.",
        capability_used="ask_clarify",
        preference_vote="neutral",
        rationale="fallback",
    )
    return gate, out


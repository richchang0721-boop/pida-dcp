from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum


class Stage(IntEnum):
    STAGE_0_EXISTENCE = 0
    STAGE_1_CAUSAL_MEMORY = 1
    STAGE_2_PREFERENCE = 2
    STAGE_3_CONSISTENCY = 3


@dataclass(frozen=True)
class DevelopmentState:
    stage: Stage

    def can(self, capability: str) -> bool:
        """
        Capability gates. Keep this strict so the prototype can't be 'talked into' skipping stages.
        """
        caps_by_stage = {
            Stage.STAGE_0_EXISTENCE: {"ack", "ask_clarify", "refuse"},
            Stage.STAGE_1_CAUSAL_MEMORY: {"ack", "ask_clarify", "refuse", "record_causal"},
            Stage.STAGE_2_PREFERENCE: {"ack", "ask_clarify", "refuse", "record_causal", "express_preference"},
            Stage.STAGE_3_CONSISTENCY: {
                "ack",
                "ask_clarify",
                "refuse",
                "record_causal",
                "express_preference",
                "enforce_consistency",
                "offer_minimal_alternative",
            },
        }
        return capability in caps_by_stage[self.stage]


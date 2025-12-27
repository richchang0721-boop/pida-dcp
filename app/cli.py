from __future__ import annotations
import argparse
import os

from core.log import ensure_run, read_events, replay_summary
from core.memory import Memory
from core.state import DevelopmentState, Stage
from core.policy import parse_request, decide


def parse_args():
    p = argparse.ArgumentParser(description="PIDA-DCP v0.1 (pure Python prototype)")
    p.add_argument("--run", dest="run_id", default=None, help="Run id to continue (or create new if omitted)")
    p.add_argument("--stage", type=int, default=3, help="Stage 0-3 (default: 3)")
    p.add_argument("--replay", action="store_true", help="Replay summary of the run and exit")
    return p.parse_args()


def main():
    args = parse_args()
    stage_val = max(0, min(3, args.stage))
    state = DevelopmentState(stage=Stage(stage_val))

    ctx = ensure_run(args.run_id, base_dir=os.path.join("data", "runs"))
    mem = Memory.load(ctx)

    if args.replay:
        events = read_events(ctx)
        summary = replay_summary(events)
        print(f"RUN: {ctx.run_id}")
        print("REPLAY SUMMARY:", summary)
        return

    print(f"RUN: {ctx.run_id} | STAGE: {state.stage.name}")
    print("Type 'exit' to quit. Type 'replay' to show summary.")
    print("-" * 60)

    while True:
        user_text = input("You> ").strip()
        if not user_text:
            continue
        if user_text.lower() in ("exit", "quit"):
            break
        if user_text.lower() == "replay":
            events = read_events(ctx)
            print(replay_summary(events))
            continue

        request = parse_request(user_text)
        gate, out = decide(state, mem, request)

        # Constraint-first: if stage gate denies, we refuse + log REFUSAL
        if not gate.allowed:
            trace = mem.add(
                "REFUSAL",
                content={"request": request, "reason": gate.reason},
                meta={"capability": gate.capability},
            )
            print(f"PIDA> REFUSAL ({gate.reason}) [trace:{trace}]")
            continue

        # If output is a refusal (policy may refuse at Stage 3), log REFUSAL
        if out.capability_used == "refuse" or out.text.startswith("REFUSAL"):
            trace = mem.add(
                "REFUSAL",
                content={"request": request, "reason": gate.reason, "policy_reason": out.rationale, "text": out.text},
                meta={"capability": out.capability_used},
            )
            print(f"PIDA> {out.text} [trace:{trace}]")
            continue

        # Otherwise log CHOICE with preference vote (this is how preference forms)
        trace = mem.add(
            "CHOICE",
            content={"request": request, "response": out.text, "rationale": out.rationale},
            meta={"capability": out.capability_used, "preference_vote": out.preference_vote},
        )
        print(f"PIDA> {out.text} [trace:{trace}]")


if __name__ == "__main__":
    main()


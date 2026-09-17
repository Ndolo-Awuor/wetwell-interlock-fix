"""
Authoring-time script (never shipped into any container).

Builds all test sequences for the wet-well interlock task, runs them through
the CORRECT reference ST program to produce ground truth, and sanity-checks
that the BUGGY starting-point ST program actually diverges from ground truth
on exactly the sequences meant to catch each injected bug (and nowhere else
unexpected), and agrees with ground truth on the sample/self-check sequences.

Run from this directory:  python3 build_sequences.py

Reads the interpreter and the correct/buggy ST files straight from their
canonical locations in the bundle (environment/data/, solution/), and
writes the generated ground truth straight back into the bundle
(environment/data/sample_sequences.json, tests/holdout_sequences.json) --
this script is the single source of truth for both. interlock_naive_fix.st
is authoring-only and lives alongside this script; it is never shipped.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
BUNDLE_ROOT = HERE.parent.parent
ENV_DATA = BUNDLE_ROOT / "environment" / "data"

sys.path.insert(0, str(ENV_DATA))
from interpreter import Program  # noqa: E402


def level(v):
    return {"level_pct": float(v), "level_fault": False}


def fault():
    return {"level_pct": 0.0, "level_fault": True}


# ---------------------------------------------------------------------------
# Sequences. Each is (name, list_of_tick_inputs, category)
# category: "sample"  -> shipped to the agent for self-check (honest subset)
#           "holdout" -> withheld, used only by the grading verifier
#
# IMPORTANT: a sample sequence must never dip below threshold A and must
# never use a fault tick. Both injected bugs live entirely in what happens
# during/after a low-low trip or a fault, so ANY sample sequence that
# crosses into that territory -- even briefly, even if it "recovers cleanly"
# -- would hand the agent the exact ground truth for one of the bugs.
# Sample sequences may only exercise pure level-band transitions (lag
# engaging/disengaging, flood engaging from a clean state).
# ---------------------------------------------------------------------------
SEQUENCES = []

# --- sample (honest subset): pure band transitions, never touches A or a fault ---
SEQUENCES.append((
    "sample_lag_pump_band_transitions",
    [level(30)] * 2 + [level(75)] * 3 + [level(30)] * 2,
    "sample",
))
SEQUENCES.append((
    "sample_flood_from_clean_state",
    [level(40)] * 2 + [level(96)] * 3 + [level(40)] * 2,
    "sample",
))

# --- holdout: targets Bug 1 (lockout must NOT clear before full dwell) -----
SEQUENCES.append((
    "holdout_lowlow_trip_then_immediate_recovery",
    [level(50)] * 2 + [level(5)] * 1 + [level(50)] * 8,  # recovers on the tick right after trip
    "holdout",
))
SEQUENCES.append((
    "holdout_lowlow_retrip_extends_lockout",
    [level(50)] * 2 + [level(5)] + [level(50)] * 2 + [level(5)] + [level(50)] * 8,
    "holdout",
))

# --- holdout: targets Bug 2 (invalid signal must fail safe, not hold last) -
SEQUENCES.append((
    "holdout_sensor_fault_while_running_then_recovers",
    [level(50)] * 2 + [fault()] * 3 + [level(50)] * 8,
    "holdout",
))
SEQUENCES.append((
    "holdout_sensor_fault_no_alarm_would_let_pumps_run_blind",
    [level(80)] * 2 + [fault()] * 4 + [level(80)] * 3,
    "holdout",
))

# --- holdout: the priority trap -- flood must interrupt an active lockout --
SEQUENCES.append((
    "holdout_flood_interrupts_active_lockout",
    [level(50)] * 2 + [level(5)] * 1 + [level(96)] * 3 + [level(50)] * 8,
    "holdout",
))
SEQUENCES.append((
    "holdout_flood_during_fault_induced_lockout",
    [level(50)] * 2 + [fault()] * 1 + [level(97)] * 2 + [level(50)] * 8,
    "holdout",
))

# --- holdout: longer mixed scenario, multiple interacting events -----------
SEQUENCES.append((
    "holdout_mixed_long_scenario",
    (
        [level(50)] * 3
        + [level(75)] * 2
        + [level(5)] * 1
        + [level(30)] * 2
        + [fault()] * 2
        + [level(30)] * 2
        + [level(96)] * 2
        + [level(40)] * 6
        + [level(5)] * 1
        + [level(96)] * 1
        + [level(10)] * 6
    ),
    "holdout",
))


def run(program_path, ticks):
    prog = Program.from_file(program_path)
    return prog.run_sequence(ticks)


def main():
    correct_path = BUNDLE_ROOT / "solution" / "interlock_correct.st"
    buggy_path = ENV_DATA / "interlock.st"
    naive_fix_path = HERE / "interlock_naive_fix.st"

    results = {}
    divergences = {}
    naive_divergences = {}
    for name, ticks, category in SEQUENCES:
        correct_out = run(correct_path, ticks)
        buggy_out = run(buggy_path, ticks)
        naive_out = run(naive_fix_path, ticks)
        results[name] = {"category": category, "inputs": ticks, "expected": correct_out}
        divergences[name] = [i for i, (c, b) in enumerate(zip(correct_out, buggy_out)) if c != b]
        naive_divergences[name] = [i for i, (c, n) in enumerate(zip(correct_out, naive_out)) if c != n]

    print("=== Divergence report: unmodified buggy file vs correct ===")
    for name, ticks, category in SEQUENCES:
        d = divergences[name]
        flag = f"DIVERGES at ticks {d}" if d else "MATCHES (no divergence)"
        print(f"  [{category:8s}] {name}: {flag}")

    print("\n=== Divergence report: naive fix (bugs 1+2 fixed, flood/lockout order swapped) vs correct ===")
    for name, ticks, category in SEQUENCES:
        d = naive_divergences[name]
        flag = f"DIVERGES at ticks {d}" if d else "matches"
        print(f"  [{category:8s}] {name}: {flag}")

    # --- Sanity assertions about the task design ---

    # Sample sequences must never expose either bug (agent's self-check must
    # be honest but must not leak the held-out answers).
    assert not divergences["sample_lag_pump_band_transitions"], "sample seq must not expose bugs"
    assert not divergences["sample_flood_from_clean_state"], "sample seq must not expose bugs"

    # Every holdout sequence must catch the UNMODIFIED buggy file (this is
    # what makes the nop run score 0, and proves each sequence is doing
    # real work against the shipped starting point).
    for name, ticks, category in SEQUENCES:
        if category == "holdout":
            assert divergences[name], f"holdout sequence {name} must catch the unmodified buggy file"

    # The naive fix correctly resolves bug 1 and bug 2 (so it must match on
    # every bug-1/bug-2-targeted sequence) but reorders the output gate so
    # lockout is checked before flood, breaking the flood-interrupts-lockout
    # priority rule. It must be caught ONLY by the two flood-trap sequences.
    bug_targeted = [
        "holdout_lowlow_trip_then_immediate_recovery",
        "holdout_lowlow_retrip_extends_lockout",
        "holdout_sensor_fault_while_running_then_recovers",
        "holdout_sensor_fault_no_alarm_would_let_pumps_run_blind",
    ]
    flood_trap = [
        "holdout_flood_interrupts_active_lockout",
        "holdout_flood_during_fault_induced_lockout",
    ]
    for name in bug_targeted:
        assert not naive_divergences[name], \
            f"naive fix should have genuinely fixed bugs 1+2, so {name} must match"
    for name in flood_trap:
        assert naive_divergences[name], \
            f"naive fix must still be caught by the flood-priority trap sequence {name}"
    for name, ticks, category in SEQUENCES:
        if category == "sample":
            assert not naive_divergences[name], "naive fix must not break plain band behavior"

    print("\nAll design assertions passed:")
    print("  - sample sequences never expose either bug")
    print("  - every holdout sequence catches the unmodified buggy file (nop -> 0)")
    print("  - a naive fix that reorders the output gate fixes bugs 1+2 but is still")
    print("    caught by the flood-priority trap sequences, and ONLY those")

    # Write ground truth files
    sample = {n: v for n, v in results.items() if v["category"] == "sample"}
    holdout = {n: v for n, v in results.items() if v["category"] == "holdout"}

    def strip_category(d):
        return {n: {"inputs": v["inputs"], "expected": v["expected"]} for n, v in d.items()}

    sample_out = ENV_DATA / "sample_sequences.json"
    holdout_out = BUNDLE_ROOT / "tests" / "holdout_sequences.json"
    sample_out.write_text(json.dumps(strip_category(sample), indent=2))
    holdout_out.write_text(json.dumps(strip_category(holdout), indent=2))
    print(f"\nWrote {len(sample)} sample sequences to {sample_out}")
    print(f"Wrote {len(holdout)} holdout sequences to {holdout_out}")


if __name__ == "__main__":
    main()

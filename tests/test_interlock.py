"""
Sealed verifier. Runs the agent's corrected /app/interlock.st through the
baked-in ST interpreter for every held-out test sequence and compares the
output tick-by-tick against precomputed ground truth. Any mismatch, or any
failure to parse/run the file at all, fails the case.

Ground truth in holdout_sequences.json was generated once, at authoring
time, by running the reference-correct interlock.st (solution/) through
this same interpreter -- see authoring/build_sequences.py. Grading does
not re-run any reference implementation; it only compares the agent's
output against the frozen expected values.
"""
import json
import os
from pathlib import Path

import pytest

from interpreter import Program, STSyntaxError

ARTIFACT_PATH = Path("/app/interlock.st")
HOLDOUT_PATH = Path(__file__).parent / "holdout_sequences.json"

with open(HOLDOUT_PATH) as f:
    HOLDOUT = json.load(f)


@pytest.mark.parametrize("seq_name", sorted(HOLDOUT.keys()))
def test_holdout_sequence(seq_name):
    assert ARTIFACT_PATH.exists(), (
        f"expected artifact not found at {ARTIFACT_PATH}"
    )
    case = HOLDOUT[seq_name]
    try:
        program = Program.from_file(ARTIFACT_PATH)
        actual = program.run_sequence(case["inputs"])
    except STSyntaxError as e:
        pytest.fail(f"{seq_name}: interlock.st failed to parse/run -- {e}")
        return

    expected = case["expected"]
    assert len(actual) == len(expected), f"{seq_name}: wrong number of ticks produced"
    for i, (a, e) in enumerate(zip(actual, expected)):
        assert a == e, f"{seq_name}: output mismatch at tick {i} -- expected {e}, got {a}"

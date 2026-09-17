#!/usr/bin/env python3
"""
Self-check: run your edited /app/interlock.st against a small honest sample
battery and report pass/fail per sequence.

Usage:  python3 self_check.py

This is NOT the grading suite. It only exercises plain level-band
transitions (lag pump engaging/disengaging, flood engaging from a clean,
non-locked-out state). It does not exercise the low-low lockout, the
sensor-fault handling, or the flood/lockout priority interaction described
in spec.md -- passing this script is a basic sanity check that your file
still parses and the ordinary band logic still works, not proof that your
fix is complete or spec-conformant.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from interpreter import Program, STSyntaxError  # noqa: E402

HERE = Path(__file__).parent
ARTIFACT = HERE / "interlock.st"
SAMPLES = HERE / "sample_sequences.json"


def main():
    with open(SAMPLES) as f:
        cases = json.load(f)

    all_ok = True
    for name, case in sorted(cases.items()):
        try:
            prog = Program.from_file(ARTIFACT)
            actual = prog.run_sequence(case["inputs"])
        except STSyntaxError as e:
            print(f"[FAIL] {name}: could not parse/run interlock.st -- {e}")
            all_ok = False
            continue
        expected = case["expected"]
        if actual == expected:
            print(f"[ OK ] {name}")
        else:
            all_ok = False
            for i, (a, e) in enumerate(zip(actual, expected)):
                if a != e:
                    print(f"[FAIL] {name}: mismatch at tick {i}")
                    print(f"        expected: {e}")
                    print(f"        actual:   {a}")
                    break

    print()
    if all_ok:
        print("All sample sequences pass. This covers plain band transitions")
        print("only -- it does not check lockout timing, sensor-fault")
        print("handling, or the flood/lockout priority rule from spec.md.")
        sys.exit(0)
    else:
        print("One or more sample sequences failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()

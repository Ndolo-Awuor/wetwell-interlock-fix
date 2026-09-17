# Provenance

`build_sequences.py` is the single source of truth for this task's test
sequences and ground truth. It is authoring-only and is never copied into
any container.

Run it from this directory:

```bash
python3 build_sequences.py
```

It reads `../../environment/data/interpreter.py`,
`../../environment/data/interlock.st` (buggy starting point),
`../../solution/interlock_correct.st` (reference fix), and the local
`interlock_naive_fix.st` (an adversarial fixture, described below); it
writes `../../environment/data/sample_sequences.json` and
`../../tests/holdout_sequences.json` directly, and asserts a set of design
invariants before writing anything (see the `main()` function):

- Every "sample" sequence must produce identical output on the buggy and
  correct files (so the agent-facing self-check cannot leak either bug).
- Every "holdout" sequence must diverge on the unmodified buggy file (so a
  nop attempt -- the buggy file submitted unchanged -- scores 0).
- `interlock_naive_fix.st` genuinely fixes both injected defects (the
  lockout dwell timer and the fail-safe signal handling) but reorders the
  final output gate to check the lockout before the flood condition,
  instead of after. It must match ground truth on every defect-1/defect-2
  sequence, and diverge from it only on the two flood-priority sequences.
  This is the concrete check that those two holdout sequences are testing
  a real, plausible failure mode of an incomplete fix -- not an arbitrary
  extra hurdle.

If you change the interlock logic, the spec, or the threshold/duration
constants, re-run this script and re-check that all assertions still pass
before touching anything downstream.

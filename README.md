# wetwell-interlock-fix

Fix two behavioral defects in a PLC-style Structured Text interlock for a
duplex wet-well pump station, against a written functional spec
(`environment/data/spec.md`), without regressing a flood/lockout priority
exception that the starting file already implements correctly.

## Difficulty

The starting `interlock.st` has two independent defects relative to the
spec:

1. The low-low lockout clears the instant the level signal recovers,
   instead of holding for its full fixed dwell time.
2. An out-of-range (invalid) level signal is handled by holding the last
   known-good reading instead of failing safe (treat as low-low, raise a
   distinct alarm).

Either defect, read in isolation against the spec, is a plausible thing to
find and patch. What makes the task hard is that the *obvious* way to
patch defect 1 -- restructuring the final pump-output decision so
everything is gated behind "not in an active lockout" -- silently breaks a
requirement that was already correctly implemented in the starting file:
flood (high-high) must be able to interrupt an active lockout. A fix that
is verified only against "does the lockout now last the right duration"
and "does an invalid signal now fail safe" can look complete while still
failing this interaction, because the interaction only appears when a
flood condition and an active lockout co-occur -- something that does not
show up by testing either defect individually. A correct fix has to
preserve output-gate branch ordering (or equivalent logic) that a
surface-level reading of "gate pump output behind lockout" does not
suggest is load-bearing.

We validated this concretely: `authoring/build_sequences.py` constructs a
"naive fix" of the starting file that correctly resolves both defects but
reorders the output gate (checks lockout before flood instead of after).
That fix passes every defect-1 and defect-2 test but fails both
flood-priority holdout sequences -- proof that those sequences are testing
something a plausible incomplete fix actually gets wrong, not an
arbitrary extra hurdle.

The scenario, thresholds, spec, and defects are authored by us for this
task (synthetic), grounded in real duplex lift-station interlock design
practice; they are not drawn from a public incident or dataset.

## Reference solution

`solution/solve.sh` copies `solution/interlock_correct.st` (a from-scratch
correct implementation of the full spec) to the declared artifact path,
`/app/interlock.st`. See `interlock_correct.st` for the fix: the lockout
clear condition changes from "trip condition has cleared" to "the fixed
dwell timer has counted down to zero", and signal-fault handling changes
from "carry forward the last good reading" to "treat as low-low and raise
`sensor_fault_alarm`" -- both applied without changing the existing
output-gate branch order (flood checked before lockout, unconditionally).

## Verification

`tests/test_interlock.py` (pytest, run by `tests/test.sh`) loads the
agent's corrected `/app/interlock.st` through the same small ST
interpreter (`tests/interpreter.py`, identical to the copy shipped to the
agent) and replays a held-out battery of tick sequences
(`tests/holdout_sequences.json`) that the agent never sees. For every
sequence, every tick's full output (`pump1_run`, `pump2_run`,
`lockout_active`, `sensor_fault_alarm`) must match the precomputed
expected value exactly; a single mismatched tick, or a file that fails to
parse/run at all, fails that sequence. Reward is 1 only if every held-out
sequence passes in full; otherwise 0. Ground truth was generated once, at
authoring time, by running the reference-correct `interlock.st` through
this same interpreter (`authoring/build_sequences.py`) -- grading never
re-executes any reference implementation, it only compares against frozen
expected values baked into the verifier image.

The agent is given a small, disjoint "sample" battery
(`environment/data/sample_sequences.json`, run via
`environment/data/self_check.py`) that only exercises plain level-band
transitions (lag engaging, flood engaging from a clean state) and never
crosses the low-low threshold or uses a fault input, so it cannot leak
either defect's expected behavior while still letting the agent sanity-
check that its edited file parses and runs.

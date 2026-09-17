<!--
DRAFT ONLY. Rewrite this in your own words before submission -- the
platform screens instruction.md for AI-generated text and rejects flagged
submissions. Keep the facts (paths, deliverable, closing sentence) but
express it the way you'd actually write it. Delete this comment block
before submitting.
-->

# Wet-well pump interlock -- fix against spec

You are given a small PLC-style interlock program for a duplex wet-well
pump station, written in a minimal Structured Text (IEC 61131-3-style)
subset, at `/app/interlock.st`. It has not been validated against its
functional spec and does not conform to it in every case.

Read the functional spec at `/app/spec.md`. It describes the intended
behavior of the interlock in full: the level thresholds and zones, the
lead/lag duty rotation between the two pumps, the low-low dry-run lockout,
how an invalid/out-of-range level signal must be handled, and a priority
rule governing how a flood condition interacts with an active lockout.

`/app/interpreter.py` is the exact interpreter that will execute your
`interlock.st` (both now, for your own testing, and later, for grading).
Read it if you want to see precisely which language constructs are
supported and how a single scan cycle ("tick") is evaluated -- inputs in,
persistent state updated, outputs out.

`/app/self_check.py`, run against `/app/sample_sequences.json`, replays a
small set of sample scenarios through your edited file and reports
pass/fail. It only exercises ordinary level-band transitions. It is a
sanity check that your file still parses and runs, not a substitute for
verifying your fix against the full spec.

## Your task

Bring `/app/interlock.st` into full conformance with `/app/spec.md`. You
may restructure the program as needed, but it must keep the same input
and output variable names and meanings (`level_pct`, `level_fault` in;
`pump1_run`, `pump2_run`, `lockout_active`, `sensor_fault_alarm` out), and
it must remain valid syntax for the interpreter at `/app/interpreter.py`.

Save your corrected program in place, at `/app/interlock.st`. That is the
only file that will be graded.

You have 10800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.

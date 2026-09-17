# Functional Spec — Duplex Wet-Well Pump Station Interlock

## System

One wet well, one level transmitter (4-20 mA field signal, scaled by the PLC
to `level_pct`, 0-100%), two identical submersible pumps (P1, P2) in a
lead/lag duty-sharing arrangement. The interlock logic runs once per PLC
scan cycle ("tick"): it reads the current level, and drives `pump1_run`,
`pump2_run`, `lockout_active`, and `sensor_fault_alarm` for that cycle.

## Level thresholds

Three thresholds divide the well into zones, `A < B < C`:

- **A — low-low.** Dry-run protection. The well should never normally be
  drawn down this far; reaching it means something is wrong downstream
  (blocked inflow, stuck check valve, mis-set thresholds) and running a
  pump dry will destroy it.
- **B — lag engage.** Above this level, one pump alone isn't keeping up;
  the lag pump joins the lead pump.
- **C — high-high / flood.** The well is at serious risk of overflow.

Zones and required pump behavior, level signal assumed valid:

| Zone | Required behavior |
|---|---|
| `level < A` | Low-low trip (see below) |
| `A <= level < B` | Duty (lead) pump runs, lag pump off |
| `B <= level < C` | Both pumps run |
| `level >= C` | Both pumps run, unconditionally (see Priority below) |

## Duty rotation

P1 and P2 must wear evenly. Every time the pumps go from *not running* to
*running* under normal conditions (i.e. the well level rises back through
`A` after a stop, and the interlock is not in a lockout), the pump that
takes the *lead* role for that run swaps from whichever pump led last time.
The pump that is not leading in a given cycle is the one that would be
commanded on as the *lag* pump if the level reaches zone B-C.

## Low-low lockout

A trip at or below threshold A must stop both pumps immediately and hold
them off for a **fixed dwell time** — a firm, timed lockout — even if the
level signal recovers above A right away. This exists because a level
signal bouncing around the low-low threshold (turbulence, a sticking
float, transmitter noise) must not be allowed to chatter the pumps on and
off across the trip point; the lockout has to run its full, fixed
duration once started, only clearing when that timer has completely
elapsed, never early just because the reading looks fine again. If a new
low-low condition (or a sensor fault — see below) occurs again before the
timer has finished, the dwell time starts over from the top.

## Signal validation

If the field signal goes outside its valid range (a broken wire, a shorted
loop, a disconnected transmitter — anything that makes the 4-20 mA reading
invalid), the interlock must **never continue to trust the level it last
had**. An unreadable signal is treated exactly like a low-low condition:
both pumps stop, the fixed-duration lockout engages (same as any other
low-low trip), and — in addition — a **distinct sensor-fault alarm** is
raised for as long as the signal stays invalid, so operators can tell a
genuine low-low trip apart from an instrumentation fault. Holding the
last-known-good reading, or defaulting to "level OK," is not acceptable:
an unreadable signal must always fail toward stopping the pumps, never
toward keeping them running unattended.

## Priority: flood always wins

The high-high/flood condition (zone C) is the one condition allowed to
**interrupt an active lockout**. If the well level spikes into the flood
zone while the pumps are locked out from a prior low-low trip (or a prior
sensor fault), the flood requirement takes precedence: both pumps are
commanded on immediately, regardless of the lockout timer. The lockout
timer itself keeps running underneath — the flood does not cancel or reset
it — but it must not be allowed to block the pumps while the well is
actively flooding. Overflowing the wet well is a worse outcome than a
pump running against a still-elevated level, so this exception is
deliberate and must be preserved by any change to the interlock logic.

## Deliverable

The interlock is implemented in a small Structured Text (IEC 61131-3-style)
program, `interlock.st`, interpreted by `interpreter.py` (also provided —
read it if you want to see exactly what language subset and per-tick
semantics are supported: assignment, `IF/ELSIF/ELSE/END_IF`, `AND/OR/NOT`,
comparisons, `+`/`-`, and persistent state across ticks). The current
`interlock.st` has not been validated against this spec and does not
conform to it in every case. Your job is to bring it into full conformance
with everything stated above, without changing its outward interface
(same `VAR_INPUT`/`VAR_OUTPUT` names and meanings).

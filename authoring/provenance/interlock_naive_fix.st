PROGRAM InterlockLogic
(* AUTHORING-TIME ADVERSARIAL FIXTURE -- NOT shipped to the agent, NOT the
   reference solution. This is a "naive fix": it correctly resolves bug 1
   (lockout timer) and bug 2 (fail-safe on invalid signal) but reorders the
   final output gate to check lockout BEFORE flood instead of after,
   silently losing the flood-interrupts-lockout priority rule. It exists so
   build_sequences.py can prove the flood-trap holdout sequences catch a
   fix that looks complete but isn't. *)
VAR
    lockout_timer : INT := 0;
    duty_lead : BOOL := FALSE;
    was_running : BOOL := FALSE;
    last_good_level : REAL := 0.0;
    effective_level : REAL := 0.0;
    trip : BOOL := FALSE;
    lead_cmd : BOOL := FALSE;
    lag_cmd : BOOL := FALSE;
END_VAR

VAR CONSTANT
    A : REAL := 15.0;
    B : REAL := 65.0;
    C : REAL := 92.0;
    LOCKOUT_DURATION : INT := 5;
END_VAR

VAR_INPUT
    level_pct : REAL;
    level_fault : BOOL;
END_VAR

VAR_OUTPUT
    pump1_run : BOOL := FALSE;
    pump2_run : BOOL := FALSE;
    lockout_active : BOOL := FALSE;
    sensor_fault_alarm : BOOL := FALSE;
END_VAR

IF level_fault THEN
    sensor_fault_alarm := TRUE;
    effective_level := -1.0;
ELSE
    sensor_fault_alarm := FALSE;
    last_good_level := level_pct;
    effective_level := level_pct;
END_IF;

IF effective_level < A OR sensor_fault_alarm THEN
    trip := TRUE;
ELSE
    trip := FALSE;
END_IF;

IF trip THEN
    lockout_active := TRUE;
    lockout_timer := LOCKOUT_DURATION;
ELSIF lockout_timer > 0 THEN
    lockout_timer := lockout_timer - 1;
    IF lockout_timer <= 0 THEN
        lockout_active := FALSE;
    END_IF;
END_IF;

IF effective_level >= A AND NOT was_running AND NOT lockout_active THEN
    duty_lead := NOT duty_lead;
END_IF;

lead_cmd := FALSE;
lag_cmd := FALSE;
IF effective_level >= A AND effective_level < B THEN
    lead_cmd := TRUE;
ELSIF effective_level >= B THEN
    lead_cmd := TRUE;
    lag_cmd := TRUE;
END_IF;

(* BUG (deliberate, for the adversarial fixture only): lockout is checked
   BEFORE flood, so an active lockout blocks pumps even during a flood. *)
IF lockout_active THEN
    pump1_run := FALSE;
    pump2_run := FALSE;
ELSIF effective_level >= C THEN
    pump1_run := TRUE;
    pump2_run := TRUE;
ELSIF duty_lead THEN
    pump1_run := lead_cmd;
    pump2_run := lag_cmd;
ELSE
    pump1_run := lag_cmd;
    pump2_run := lead_cmd;
END_IF;

was_running := pump1_run OR pump2_run;

END_PROGRAM

PROGRAM InterlockLogic
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

(* 1. Validate the signal. An out-of-range reading is never trusted --
      treat it as a low-low condition and raise a distinct alarm. *)
IF level_fault THEN
    sensor_fault_alarm := TRUE;
    effective_level := -1.0;
ELSE
    sensor_fault_alarm := FALSE;
    last_good_level := level_pct;
    effective_level := level_pct;
END_IF;

(* 2. Trip condition: low-low level OR an unreadable signal. *)
IF effective_level < A OR sensor_fault_alarm THEN
    trip := TRUE;
ELSE
    trip := FALSE;
END_IF;

(* 3. Timed lockout: every new trip (re)starts the full dwell time.
      The lockout only clears once the timer has counted all the way
      down, never early just because the level looks fine again. *)
IF trip THEN
    lockout_active := TRUE;
    lockout_timer := LOCKOUT_DURATION;
ELSIF lockout_timer > 0 THEN
    lockout_timer := lockout_timer - 1;
    IF lockout_timer <= 0 THEN
        lockout_active := FALSE;
    END_IF;
END_IF;

(* 4. Lead/lag duty rotation: swap which pump leads at the start of
      each new run cycle (rising edge out of "not running"). *)
IF effective_level >= A AND NOT was_running AND NOT lockout_active THEN
    duty_lead := NOT duty_lead;
END_IF;

(* 5. Base pump demand from level band alone, ignoring lockout. *)
lead_cmd := FALSE;
lag_cmd := FALSE;
IF effective_level >= A AND effective_level < B THEN
    lead_cmd := TRUE;
ELSIF effective_level >= B THEN
    lead_cmd := TRUE;
    lag_cmd := TRUE;
END_IF;

(* 6. Final output gate. Flood (high-high) ALWAYS forces both pumps
      on, even during an active lockout -- it is the one condition
      allowed to interrupt a lockout. Otherwise an active lockout
      blocks all pump output; failing that, duty rotation decides
      which physical pump gets the lead/lag command. *)
IF effective_level >= C THEN
    pump1_run := TRUE;
    pump2_run := TRUE;
ELSIF lockout_active THEN
    pump1_run := FALSE;
    pump2_run := FALSE;
ELSIF duty_lead THEN
    pump1_run := lead_cmd;
    pump2_run := lag_cmd;
ELSE
    pump1_run := lag_cmd;
    pump2_run := lead_cmd;
END_IF;

was_running := pump1_run OR pump2_run;

END_PROGRAM

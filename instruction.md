# Wet-well pump interlock

There’s a wet-well interlock program at `/app/interlock.st` for a duplex pump station with two pumps, a level transmitter, and lead/lag duty sharing. The program hasn’t been fully validated against its specification, and it doesn’t behave correctly in every situation.

Start by reading `/app/spec.md` in full. It contains all the requirements, including the level zones, lead/lag duty rotation, low-low dry-run lockout and its dwell time, handling of out-of-range level signals, and the priority rule for when flooding occurs during an active lockout.

Pay particular attention to the flood-versus-lockout priority rule. It’s easy to get the other parts right while missing this one.

You can also review `/app/interpreter.py` to understand how `interlock.st` is executed. The interpreter supports assignment, IF/ELSIF/ELSE, AND/OR/NOT, comparisons, and persistent state across ticks. Make sure any changes you make use only the syntax and features supported by this interpreter, since the same interpreter will be used during grading.

The file `/app/self_check.py` runs the program against `/app/sample_sequences.json` and reports pass or fail. Keep in mind that these tests only cover basic level-band behavior. They don't check the lockout timing, sensor fault handling, or the interaction between flooding and an active lockout. Passing the self-check is a useful starting point, but it doesn't mean the implementation is fully correct.

Your task is to update `/app/interlock.st` so that it meets the specification in all cases. You can reorganize the code however you like, but keep the existing input and output variables and their meanings:
• Inputs: level_pct, level_fault
• Outputs: pump1_run, pump2_run, lockout_active, sensor_fault_alarm

Once you've finished, save the corrected program back to `/app/interlock.st`. That is the only file that will be graded.

You have 10800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.

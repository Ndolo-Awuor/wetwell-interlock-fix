#!/bin/bash
# Sealed verifier entrypoint. Always writes /logs/verifier/reward.txt,
# even on a crash -- there is no code path that skips it.
set -u

mkdir -p /logs/verifier

pytest /tests/test_interlock.py \
    --ctrf /logs/verifier/ctrf-report.json \
    -q \
    > /logs/verifier/pytest_output.log 2>&1
PYTEST_EXIT=$?

cat /logs/verifier/pytest_output.log

if [ "$PYTEST_EXIT" -eq 0 ]; then
    printf '1' > /logs/verifier/reward.txt
else
    printf '0' > /logs/verifier/reward.txt
fi

exit 0

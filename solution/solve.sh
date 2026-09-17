#!/bin/bash
# Reference solution. Writes the corrected interlock logic to the declared
# artifact path. Uses the script's own directory (not an assumed mount
# path for solution/) so it works regardless of where harbor mounts it.
set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/interlock_correct.st" /app/interlock.st

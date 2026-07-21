#!/bin/bash
# Typecheck script that filters out errors from third-party code.
# Doing this because frappe-ui has a lot of errors that are not related to our
# code, and vue-tsc exits non-zero whenever any of them are present.
#
# Excludes by path rather than allow-listing src/, so errors that belong to
# neither (a broken tsconfig, a failed startup) still fail the build. Matching
# only "error TSxxxx" header lines keeps the indented continuation lines from
# counting as errors of their own.
OUTPUT=$(vue-tsc --noEmit 2>&1)
STATUS=$?

# 126/127 mean vue-tsc was never executed (not found, not executable). Its
# output carries no "error TSxxxx" lines, so the filter below would read that
# as a clean run.
if [ "$STATUS" -ge 126 ]; then
  echo "$OUTPUT"
  echo "vue-tsc failed to run (exit $STATUS)"
  exit 1
fi

ERRORS=$(echo "$OUTPUT" | grep -E "error TS[0-9]+" | grep -vE "^(node_modules|frappe-ui)/")

if [ -n "$ERRORS" ]; then
  echo "$ERRORS"
  exit 1
else
  echo "Type check completed successfully (node_modules errors ignored)"
  exit 0
fi
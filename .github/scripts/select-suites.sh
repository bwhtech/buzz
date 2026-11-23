#!/usr/bin/env bash
# Decides which suites a pull request can reach and writes `backend` and `ui` (true/false) to
# GITHUB_OUTPUT. Only pull requests are narrowed: pushes and the merge queue run everything.
# A file matched by no rule below reruns everything, so new paths are tested until listed.
#
# usage: select-suites.sh   (run inside the checkout, cloned with fetch-depth 2)
set -euo pipefail

# Changes the Python suite cannot reach: the dashboard SPA, browser tests, docs.
BACKEND_UNREACHABLE='^(dashboard/|e2e/|playwright\.config\.ts$|docs/|.*\.md$|\.oxlintrc\.json$|\.oxfmtrc\.json$|\.github/workflows/(checks|ui-tests|pr-[a-z-]+)\.yml$)'
# Changes the browser suite cannot reach: Python and dashboard unit tests, docs.
UI_UNREACHABLE='^(buzz/.*/test_[^/]*\.py$|buzz/tests/|dashboard/src/.*\.test\.ts$|docs/|.*\.md$|\.github/workflows/(checks|ci|pr-[a-z-]+)\.yml$)'

reachable() {
	[ -z "$CHANGED" ] && return 0
	grep -qvE "$1" <<< "$CHANGED"
}

write() {
	echo "$1=$2" | tee -a "$GITHUB_OUTPUT"
}

if [ "${GITHUB_EVENT_NAME}" != "pull_request" ]; then
	write backend true
	write ui true
	exit 0
fi

# The pull request checkout is its merge commit; the first parent is the base it merges into.
CHANGED=$(git diff --name-only HEAD^1 HEAD)
echo "Changed files:"
echo "$CHANGED"

reachable "$BACKEND_UNREACHABLE" && write backend true || write backend false
reachable "$UI_UNREACHABLE" && write ui true || write ui false

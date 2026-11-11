---
name: cloud-bench
description: Spin up a Frappe bench with buzz installed inside a cloud (remote) Claude Code container, then run backend tests on it. Use when `bench` is missing and you need to run tests, reproduce a bug, or verify a fix or PR in a remote session.
---

# Cloud bench

A cloud container starts with no bench, MariaDB or Python 3.14. `scripts/setup-bench.sh`
copies `.github/actions/setup-bench`, adjusted for this container. Building from nothing
takes about 5 minutes.

## Steps

1. Run the setup as root, in the background, logging to the scratchpad:
   `.claude/skills/cloud-bench/scripts/setup-bench.sh > <scratchpad>/bench-setup.log 2>&1`.
   It is done when the log ends with `==> done`. It is idempotent: after a failure, fix the
   cause and rerun it. Delete `/home/frappe/frappe-bench` first only if `bench init` failed
   partway.
2. Run bench through `scripts/bench.sh`, which runs it as the `frappe` user:
   `.claude/skills/cloud-bench/scripts/bench.sh --site buzz.localhost run-tests --module buzz.api.forms.test_forms`.
   Filter the output with `grep -E "^(Ran|OK|FAILED|FAIL:|ERROR:)"`.

## How the bench is laid out

- `apps/buzz` is a symlink to the repo checkout, so tests run against whatever branch is
  checked out. Switch branches only between runs, never during one. Use `git worktree` to
  edit another branch while a suite is running.
- Site `buzz.localhost` (Administrator/admin). MariaDB root password is `root`. Redis runs on
  ports 13000 (cache) and 11000 (queue).
- Assets are not built, so UI and Playwright checks need `bench build` first.

## Gotchas the script already handles

- bench refuses to run as root, so it runs as the `frappe` user, with the agent proxy's CA
  bundle passed in through `SSL_CERT_FILE` and similar variables.
- uv reads `uv.toml` from the working directory and errors when that directory is root-only.
- Frappe's `package.json` requires Node 24 and the container has 22. Assets are skipped, so
  `YARN_IGNORE_ENGINES=1` is enough.
- `sites/apps.txt` has no trailing newline, so a plain `>>` append merges two app names into
  one line.

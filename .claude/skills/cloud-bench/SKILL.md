---
name: cloud-bench
description: Set up a Frappe bench with Buzz installed inside a Claude Code cloud session (a fresh Ubuntu container with no bench, no MariaDB and Node 22), so that backend tests can run locally instead of only in CI. Use this when `bench` is missing, when you need to run `run-tests` in a cloud or remote session, or when the user says "set up a bench", "run the tests here", "I need a test site", or "frappe env in the cloud".
---

# Bench in a cloud session

A cloud container starts with no bench. `setup.sh` in this folder builds one the same way that
`.github/actions/setup-bench` does in CI. It is idempotent: every step is skipped when its work is
already done. A re-run takes less than a second.

## Run it

```bash
sudo bash .claude/skills/cloud-bench/setup.sh   # ~10 min on a fresh container
```

Then run tests as the `frappe` user:

```bash
as-frappe 'cd ~/frappe-bench && bench --site testbuzz.localhost run-tests --module buzz.api.booking.test_booking'
as-frappe 'cd ~/frappe-bench && bench --site testbuzz.localhost run-tests --app buzz'   # ~2 min
```

Run the script in the background, because it takes longer than the default command timeout. Start
the full suite in the background as well.

## What the script sets up

| Piece | Detail |
| --- | --- |
| MariaDB 10.11 | From apt. Root password is `root`, and crash-safe flushing is off. |
| Redis | Ports 13000 (cache, socketio) and 11000 (queue). `--save ""`, so there is no `dump.rdb`. |
| Node 24 | In `/opt/node24`. Frappe refuses the image's Node 22. |
| Python 3.14 | Installed with `uv`. |
| `frappe` user | bench refuses to run as root. `as-frappe '<cmd>'` runs a command as this user from its home, keeping the proxy environment. |
| `~frappe/frappe-bench` | `frappe` (develop), `payments`, `zoom_integration`, and `frappe_factory_bot` at the commit CI pins. |
| `apps/buzz` | A **symlink** to this checkout, installed editable. Edits are what the tests run, and you don't need `get-app` again. |
| Site | `testbuzz.localhost` with `allow_tests`, set as the default site. Admin password is `admin`. |

## Each new session

The container is reclaimed when the session ends, so run the script again in a new session. The
MariaDB and redis processes do not survive a container restart either. A re-run starts them again,
even when the bench is already there.

To skip the wait, the user can add the script to the environment's setup script (cloud environment
menu → Edit → Setup script).

## Traps

- **Run bench only through `as-frappe`.** When run as root, bench exits with "You should not run this
  command as root".
- **`/usr/local/bin/node` links to Node 22.** `as-frappe` puts `/opt/node24/bin` first in PATH. A
  login shell (`bash -l`) resets PATH, so do not use one.
- **Do not restart redis while tests run.** Every test still in flight fails, usually in
  `setUpClass`.
- **Start redis from `/tmp`.** If you start `redis-server` by hand from the repo without `--dir /tmp`,
  it drops a `dump.rdb` in the repo.
- **One bench runs one checkout.** `apps/buzz` is a single symlink, so parallel agents in the same
  container cannot test different worktrees. Give each parallel workstream its own session.
- **The script changes the repo's group.** It runs `chgrp -R frappe` on the repo, so the bench user
  can write `__pycache__` and test files. Git ignores the group, so this is harmless.
- **Network access.** GitHub, PyPI, npm, nodejs.org and the Ubuntu apt mirrors must be reachable
  through the session proxy. If a download fails, check `curl -sS "$HTTPS_PROXY/__agentproxy/status"`.

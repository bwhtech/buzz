# Bench setup for Buzz

How to get a working Frappe bench with Buzz installed on a blank machine (VM, container, cloud
sandbox or laptop) so you can run the backend tests and, if you need it, the dashboard.

Work through the steps in order. Each step starts with a **check**. If the check passes, skip the
step. If it fails, follow the **fix** for your platform. A step is **done** only when its check
passes. Caveats go with the step they affect, and the blockers list at the end maps error text to
fixes.

Plan for about 1 GB of disk for the bench and 5 to 8 minutes of wall time, most of it spent in
`bench init` and `bench new-site`.

## 0. Pick your values

```bash
export BENCH_USER=frappe                 # bench refuses to run as root
export BENCH_DIR=/home/$BENCH_USER/frappe-bench
export SITE=buzz.localhost               # CI uses test_site; *.localhost needs no /etc/hosts line
export DB_ROOT_PASSWORD=root
export ADMIN_PASSWORD=admin
export FRAPPE_BRANCH=develop             # or version-16; Buzz supports frappe >=16,<18
export BUZZ_SRC=/path/to/buzz/checkout
```

Keep these exported in every shell you open later. Switching users with `su` drops them (see step 1).

## 1. Run as a non-root user

**Check:** `[ "$(id -u)" != 0 ] && echo ok`

**Fix (you are root):**

```bash
id "$BENCH_USER" || useradd -m -s /bin/bash "$BENCH_USER"
```

From here on, run bench commands as that user. Use a wrapper script so the environment stays the
same between calls:

```bash
cat > /home/$BENCH_USER/run.sh <<'EOF'
export HOME=/home/frappe USER=frappe
export PATH=/home/frappe/.local/bin:/usr/local/bin:/usr/bin:/bin   # add your node bin dir
cd /home/frappe/frappe-bench 2>/dev/null || cd /home/frappe
"$@"
EOF
chown "$BENCH_USER" /home/$BENCH_USER/run.sh
su -m "$BENCH_USER" -c "bash /home/$BENCH_USER/run.sh bench --version"
```

Caveats:
- `bench init` as root prints `WARN: You should not run this command as root` and exits 1.
- `su -m` keeps the environment but **resets `PATH`**. Tools installed under `/root/.local/bin` or
  `/opt/*/bin` disappear. Put the binaries the user needs in `/usr/local/bin`
  (`cp /root/.local/bin/uv /usr/local/bin/`), or list their directories in the wrapper's `PATH`,
  and make sure those directories are world-readable.
- **Behind a TLS-intercepting proxy** (cloud sandboxes): copy the proxy's CA bundle to a path the
  bench user can read, then export `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `GIT_SSL_CAINFO` and
  `NODE_EXTRA_CA_CERTS` pointing to it, plus `UV_NATIVE_TLS=1`, in the wrapper. Without them, uv
  fails with `No CA certificates were loaded from the system`. uv's warning that `UV_NATIVE_TLS`
  is deprecated is harmless.

## 2. uv and Python 3.14

Frappe develop and version-16 need Python `>=3.14,<3.15`.

**Check:** `uv --version && uv python find 3.14`

**Fix:**

```bash
command -v uv || curl -LsSf https://astral.sh/uv/install.sh | sh   # or: pip install uv
uv python install 3.14
```

You do not need a system Python 3.14. Pass `--python "$(uv python find 3.14)"` to `bench init`.

## 3. MariaDB server

**Check:** `mariadb-admin -u root -p"$DB_ROOT_PASSWORD" ping` prints `mysqld is alive`.

**Fix, by what you find:**

| State | Fix |
|---|---|
| Not installed (Debian/Ubuntu) | `apt-get update && apt-get install -y --no-install-recommends mariadb-server mariadb-client libmariadb-dev pkg-config` |
| Not installed (macOS) | `brew install mariadb pkg-config && brew services start mariadb` |
| Not installed, Docker available | `docker run -d --name mariadb -p 3306:3306 -e MARIADB_ROOT_PASSWORD=$DB_ROOT_PASSWORD mariadb:11.8` (and still install `libmariadb-dev pkg-config` on the host) |
| Installed, not running, systemd present | `systemctl start mariadb` |
| Installed, not running, no systemd (containers) | `mkdir -p /run/mysqld && chown mysql:mysql /run/mysqld && (mysqld_safe --user=mysql &)`, then poll `mariadb -u root -e 'select 1'` until it answers |
| Running, but `ping` with password fails | `mariadb -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '$DB_ROOT_PASSWORD'; FLUSH PRIVILEGES;"` |

Caveats:
- Debian and Ubuntu set root to `unix_socket` auth, so `mariadb -u root` works from the root shell
  while bench's password login fails. The `ALTER USER` row fixes it.
- `libmariadb-dev` and `pkg-config` are build headers for the Python MySQL client. Without them,
  `bench init` fails while building `mysqlclient`.
- On a disposable test or CI database, add `--innodb_flush_log_at_trx_commit=0 --sync_binlog=0` to
  `mysqld_safe` (or run `SET GLOBAL` with the same settings). This gives fewer fsyncs and a faster
  suite. Never do this on a database whose data you care about.
- If MariaDB runs in Docker, run `bench new-site` with `--db-host 127.0.0.1` and
  `--mariadb-user-host-login-scope='%'`.
- MariaDB 10.6+ defaults to utf8mb4, and so does the Docker image. If `new-site` complains about
  the character set, set `character-set-server=utf8mb4` and `collation-server=utf8mb4_unicode_ci`
  in `my.cnf`.

## 4. Redis on ports 13000 and 11000

`bench init --skip-redis-config-generation` points the site at `redis://127.0.0.1:13000` (cache)
and `redis://127.0.0.1:11000` (queue). Something must listen on both ports.

**Check:** `redis-cli -p 13000 ping && redis-cli -p 11000 ping` both print `PONG`.

**Fix:**

```bash
command -v redis-server || apt-get install -y redis-server     # macOS: brew install redis
redis-server --port 13000 --daemonize yes
redis-server --port 11000 --daemonize yes
```

To let `bench start` manage Redis for you instead, drop `--skip-redis-config-generation` from
step 6.

## 5. Node 24 and yarn, or a no-op yarn

`bench init` and `bench get-app` run `yarn install` for every app that has a `package.json`,
**even with `--skip-assets`**. Frappe declares `"node": ">=24"`, so an older Node fails with
`The engine "node" is incompatible with this module`.

**Check:** `node -v` prints v24 or later, and `yarn -v` succeeds.

**Fix, by what you need:**

- **Dashboard, UI work or Playwright:** install Node 24 (`fnm install 24`, `nvm install 24`, or
  NodeSource) and run `corepack enable` (or `npm i -g yarn`).
- **Backend tests only:** shadow yarn with a no-op. It saves about 30 s and avoids the Node
  requirement entirely:

  ```bash
  mkdir -p /home/$BENCH_USER/shim
  printf '#!/bin/sh\necho "yarn shim: skipped $*"\n' > /home/$BENCH_USER/shim/yarn
  chmod +x /home/$BENCH_USER/shim/yarn   # put /home/$BENCH_USER/shim first on PATH
  ```

  With the shim, `bench build` and the dashboard do not work. Remove the shim and run
  `bench setup requirements --node` when you need them.

## 6. bench CLI and `bench init`

**Check:** `[ -f "$BENCH_DIR/apps/frappe/pyproject.toml" ] && echo ok`

**Fix:**

```bash
command -v bench || uv tool install frappe-bench        # installs to ~/.local/bin
bench init "$BENCH_DIR" \
  --frappe-branch "$FRAPPE_BRANCH" \
  --skip-redis-config-generation --skip-assets --no-backups \
  --python "$(uv python find 3.14)"
```

Caveats:
- If `bench init` fails partway, it asks `Do you want to rollback these changes? [y/N]`. A
  non-interactive shell aborts and leaves a half-built directory. Run `rm -rf "$BENCH_DIR"` before
  you retry, because `bench init` refuses an existing directory.
- `git` may report `dubious ownership` when the user running a command does not own the repo. Run
  bench and git as the user who owns `$BENCH_DIR`. Root inspecting the bench can add
  `git config --global --add safe.directory '*'` for its own reads.

## 7. Get the apps

Order matters. Buzz lists `payments` in `required_apps`, and the tests import
`frappe_factory_bot` and `zoom_integration`.

**Check:** `ls "$BENCH_DIR/apps"` shows `buzz frappe frappe_factory_bot payments zoom_integration`.

**Fix** (run in `$BENCH_DIR`):

```bash
bench get-app --skip-assets ${FRAPPE_BRANCH:+--branch $FRAPPE_BRANCH} https://github.com/frappe/payments

# Pinned commit, same as CI (.github/actions/setup-bench/action.yml). --branch rejects a SHA,
# so check out first and hand bench the local path.
git clone https://github.com/harshtandiya/frappe_factory_bot /tmp/frappe_factory_bot
git -C /tmp/frappe_factory_bot checkout "$(grep -o 'checkout [0-9a-f]\{40\}' "$BUZZ_SRC/.github/actions/setup-bench/action.yml" | cut -d' ' -f2)"
bench get-app --skip-assets /tmp/frappe_factory_bot

bench get-app --skip-assets https://github.com/bwhtech/zoom_integration
bench get-app --skip-assets buzz "$BUZZ_SRC"
bench setup requirements --dev
```

Caveats:
- `bench get-app <local path>` runs `git clone --branch <current branch> <path>`. It copies only
  **committed** work, and the path must be a git repo the bench user can read and owns. If it is
  owned by another user, clone a copy for the bench user first (`git clone "$BUZZ_SRC" ~/buzz-src`).
- Because of that clone, edits in `$BUZZ_SRC` do not reach the bench. Pick one approach:
  - Work inside `$BENCH_DIR/apps/buzz`.
  - Replace that directory with a symlink to your checkout. Then verify with
    `env/bin/python -c "import buzz; print(buzz.__file__)"`.
  - Sync your changes in before each test run.
- If a failed `get-app` left `apps/buzz` (or `apps/<name>-src`) behind, delete it before retrying.

## 8. Create the site and install the apps

**Check:** `bench --site "$SITE" list-apps` shows `frappe`, `zoom_integration`, `payments` and `buzz`.

**Fix:**

```bash
bench new-site "$SITE" --db-root-password "$DB_ROOT_PASSWORD" --admin-password "$ADMIN_PASSWORD"
bench --site "$SITE" install-app zoom_integration
bench --site "$SITE" install-app buzz          # pulls in payments as a required app
bench --site "$SITE" set-config allow_tests true
bench use "$SITE"
```

Caveats:
- A site name that does not end in `.localhost` needs `127.0.0.1 <site>` in `/etc/hosts` before
  you browse to it or run UI tests.
- Leave out `--db-root-password` and `new-site` prompts for it, which hangs a non-interactive agent.
- Frappe throttles User creation to 60 per hour (`throttle_user_limit`). Re-running user-heavy
  tests in a loop can raise `Throttled`. On a test-only site, run
  `bench --site "$SITE" set-config throttle_user_limit 100000`.

## 9. Verify

**Check, backend:**

```bash
bench --site "$SITE" run-tests --module buzz.api.booking.test_booking
```

The check passes when the output ends with `OK`. The full suite
(`run-tests --app buzz`, about 1,200 tests) takes about 3 minutes. In an agent harness, run it in
the background, because it can exceed a 2-minute tool timeout.

**Check, dashboard** (needs real Node 24 from step 5):

```bash
bench build --app buzz && bench start      # then open http://$SITE:8000/dashboard
```

Log in as Administrator with `$ADMIN_PASSWORD`. Ports 8000 (web), 9000 (socketio), 3306, 13000
and 11000 must be free. Check with `ss -ltnp`.

## 10. Optional: run the suite in parallel shards

The suite spends most of its time waiting on database round-trips, so shards on one machine
overlap well. Measured on 4 cores: 1 process takes 156s, 2 take 82s, 3 take 65s and 4 take 46s.

Each shard needs its own site. Cloning the database takes about 3s, whereas `new-site` takes
about 40s. Run this as a user with MariaDB root access:

```bash
cd "$BENCH_DIR/sites"
for n in 1 2 3 4; do
  src_db=$(python3 -c "import json;print(json.load(open('$SITE/site_config.json'))['db_name'])")
  db_password=$(python3 -c "import json;print(json.load(open('$SITE/site_config.json'))['db_password'])")
  new_db="${src_db}_shard_$n"
  rm -rf "shard_$n" && cp -r "$SITE" "shard_$n"
  python3 - "shard_$n/site_config.json" "$new_db" <<'PY'
import json, sys
path, name = sys.argv[1:]
config = json.load(open(path))
config["db_name"] = config["db_user"] = name
json.dump(config, open(path, "w"), indent=1)
PY
  mariadb -uroot -p"$DB_ROOT_PASSWORD" -e "DROP DATABASE IF EXISTS \`$new_db\`; CREATE DATABASE \`$new_db\`;
    CREATE USER IF NOT EXISTS '$new_db'@'localhost' IDENTIFIED BY '$db_password';
    GRANT ALL ON \`$new_db\`.* TO '$new_db'@'localhost';"
  mariadb-dump -uroot -p"$DB_ROOT_PASSWORD" --single-transaction --quick "$src_db" | mariadb -uroot -p"$DB_ROOT_PASSWORD" "$new_db"
done
chown -R "$BENCH_USER" shard_*

# as the bench user
for n in 1 2 3 4; do
  bench --site "shard_$n" run-parallel-tests --app buzz --build-number $n --total-builds 4 > "shard_$n.log" 2>&1 &
done; wait
grep -h '^Tests:' shard_*.log   # every line must read "Failing: 0, Errors: 0"
```

Caveat: `run-parallel-tests` resolves a test file that sits directly in the app package
(`buzz/test_*.py`) to the module `buzz` itself, so those tests **silently do not run**. Keep test
files in subpackages (for example `buzz/tests/`), or also run the root-level modules with
`run-tests --module`.

## Blockers by error text

| Error | Cause → fix |
|---|---|
| `You should not run this command as root` | Step 1: run as the bench user |
| `uv: command not found` / `bench: command not found` after `su` | `su -m` reset `PATH` → step 1 wrapper |
| `No CA certificates were loaded from the system` | Proxy CA not exported → step 1 caveat |
| `The engine "node" is incompatible` | Node < 24 → step 5 |
| `yarn install --check-files` failed | Node or network problem → step 5 (shim, if backend only) |
| `Access denied for user 'root'@'localhost'` | `unix_socket` auth or wrong password → step 3 `ALTER USER` |
| `Can't connect to local server through socket` | MariaDB not running → step 3 |
| `mysqlclient` / `mariadb_config not found` | Missing `libmariadb-dev pkg-config` → step 3 |
| `ConnectionRefusedError ... 13000` / `11000` | Redis not on those ports → step 4 |
| `detected dubious ownership` | Wrong user running git → step 6 caveat |
| `git clone ... --branch <x>` failed in `get-app` | Local repo not readable or not owned by the bench user, or branch not committed → step 7 caveat |
| `Directory already exists` on `bench init` | Half-built bench → `rm -rf "$BENCH_DIR"` |
| `Throttled` when creating users in tests | `throttle_user_limit` → step 8 caveat |
| `ModuleNotFoundError: frappe_factory_bot` / `zoom_integration` | Step 7: the apps are missing |

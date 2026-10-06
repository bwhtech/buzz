#!/bin/bash
# Provision a Frappe bench for Buzz backend tests inside a Claude Code cloud session.
# Mirrors .github/actions/setup-bench. Safe to re-run: every step skips work already done.
#
# Usage:  sudo bash .claude/scripts/setup-cloud-bench.sh
# Then:   as-frappe 'cd ~/frappe-bench && bench --site testbuzz.localhost run-tests --app buzz'
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BENCH_USER=frappe
BENCH_DIR=/home/$BENCH_USER/frappe-bench
NODE_DIR=/opt/node24
SITE=testbuzz.localhost
FACTORY_BOT_COMMIT=48904d0df778513934e92a4e7663c74bfe31bc56

main() {
	install_system_packages
	start_mariadb
	start_redis
	install_node
	create_bench_user
	install_bench_cli
	init_bench
	get_apps
	create_site
	echo "Bench ready at $BENCH_DIR, site $SITE"
}

install_system_packages() {
	command -v mariadbd > /dev/null && return
	apt-get update -qq
	DEBIAN_FRONTEND=noninteractive apt-get install -y -qq mariadb-server mariadb-client libmariadb-dev pkg-config
}

start_mariadb() {
	if ! mariadb-admin ping --silent 2> /dev/null; then
		(cd /tmp && mysqld_safe --user=mysql > /tmp/mariadb.log 2>&1 &)
		until mariadb-admin ping --silent 2> /dev/null; do sleep 1; done
	fi
	# A fresh install uses unix_socket auth; bench needs a root password.
	if mariadb -u root -e "SELECT 1" > /dev/null 2>&1; then
		mariadb -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('root'); FLUSH PRIVILEGES;"
	fi
	# Test data is throwaway, so skip crash-safe flushing.
	mariadb -u root -proot -e "SET GLOBAL innodb_flush_log_at_trx_commit = 0; SET GLOBAL sync_binlog = 0;"
}

start_redis() {
	local port
	for port in 13000 11000; do
		redis-cli -p "$port" ping > /dev/null 2>&1 && continue
		redis-server --port "$port" --save "" --appendonly no --dir /tmp --daemonize yes > /dev/null
	done
}

install_node() {
	[ -x "$NODE_DIR/bin/yarn" ] && return
	local tarball
	tarball=$(curl -sS https://nodejs.org/dist/latest-v24.x/ | grep -oE 'node-v24[0-9.]+-linux-x64.tar.xz' | head -1)
	mkdir -p "$NODE_DIR"
	curl -sSL "https://nodejs.org/dist/latest-v24.x/$tarball" | tar -xJ -C "$NODE_DIR" --strip-components=1
	"$NODE_DIR/bin/npm" install -g --prefix "$NODE_DIR" yarn > /dev/null
	chmod -R a+rX "$NODE_DIR"
}

create_bench_user() {
	# bench refuses to run as root.
	id "$BENCH_USER" > /dev/null 2>&1 || useradd -m -s /bin/bash "$BENCH_USER"
	install -m 755 "$(command -v uv)" /usr/local/bin/uv
	write_as_frappe_wrapper
	# The bench links to this checkout, so the bench user needs write access to it.
	chmod o+rx "$(dirname "$REPO_DIR")"
	chgrp -R "$BENCH_USER" "$REPO_DIR"
	chmod -R g+rwX "$REPO_DIR"
}

write_as_frappe_wrapper() {
	# Node 24 must come before /usr/local/bin, which links an older node.
	cat > /usr/local/bin/as-frappe << EOF
#!/bin/bash
# Run a command as $BENCH_USER from its home, keeping the proxy env so downloads work.
exec runuser -u $BENCH_USER --preserve-environment -- env HOME=/home/$BENCH_USER \\
	PATH=$NODE_DIR/bin:/home/$BENCH_USER/.local/bin:/usr/local/bin:/usr/bin:/bin bash -c "cd ~ && \$*"
EOF
	chmod +x /usr/local/bin/as-frappe
}

install_bench_cli() {
	as-frappe 'command -v bench > /dev/null || (uv python install 3.14 && uv tool install frappe-bench)'
}

init_bench() {
	[ -d "$BENCH_DIR/apps/frappe" ] && return
	as-frappe "bench init $BENCH_DIR --skip-redis-config-generation --skip-assets --no-backups --python \"\$(uv python find 3.14)\""
	as-frappe "cd $BENCH_DIR && bench set-config -g redis_cache redis://127.0.0.1:13000 \
		&& bench set-config -g redis_queue redis://127.0.0.1:11000 \
		&& bench set-config -g redis_socketio redis://127.0.0.1:13000"
}

get_apps() {
	get_app payments https://github.com/frappe/payments
	get_app zoom_integration https://github.com/bwhtech/zoom_integration
	get_factory_bot
	link_buzz
	# install-app reads this order; frappe must come first and buzz after its dependencies.
	as-frappe "printf 'frappe\npayments\nfrappe_factory_bot\nzoom_integration\nbuzz\n' > $BENCH_DIR/sites/apps.txt"
}

get_app() {
	[ -d "$BENCH_DIR/apps/$1" ] && return
	as-frappe "cd $BENCH_DIR && bench get-app --skip-assets $2"
}

get_factory_bot() {
	[ -d "$BENCH_DIR/apps/frappe_factory_bot" ] && return
	# Same pinned commit as CI; get-app --branch rejects a SHA.
	as-frappe "rm -rf /tmp/frappe_factory_bot && git clone -q https://github.com/harshtandiya/frappe_factory_bot /tmp/frappe_factory_bot \
		&& git -C /tmp/frappe_factory_bot checkout -q $FACTORY_BOT_COMMIT \
		&& cd $BENCH_DIR && bench get-app --skip-assets /tmp/frappe_factory_bot"
}

link_buzz() {
	# A symlink, not a clone, so edits in this checkout are what the bench runs.
	[ -e "$BENCH_DIR/apps/buzz" ] && return
	as-frappe "cd $BENCH_DIR && ln -s $REPO_DIR apps/buzz \
		&& uv pip install --quiet -e apps/buzz --python env/bin/python \
		&& bench setup requirements --dev"
}

create_site() {
	[ -d "$BENCH_DIR/sites/$SITE" ] && return
	as-frappe "cd $BENCH_DIR && bench new-site --db-root-password root --admin-password admin $SITE \
		&& bench --site $SITE install-app zoom_integration \
		&& bench --site $SITE install-app buzz \
		&& bench --site $SITE set-config allow_tests true \
		&& bench --site $SITE set-config host_name http://$SITE:8000 \
		&& bench use $SITE"
}

main "$@"

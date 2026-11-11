#!/usr/bin/env bash
# Spin a test bench for buzz in a cloud container, mirroring .github/actions/setup-bench.
# Run as root; idempotent, so a rerun resumes after a failure.
# usage: setup-bench.sh [BUZZ_PATH] [SITE]
set -euo pipefail
BUZZ=${1:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}
SITE=${2:-buzz.localhost}
BENCH=${BENCH:-$HOME/frappe-bench}

step() { echo "==> $* ($(date +%T))"; }

if [ -z "${SKIP_ROOT_STEPS:-}" ]; then

step "system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq mariadb-server mariadb-client pkg-config libmariadb-dev jq >/dev/null

step "mariadb"
if ! mariadb-admin ping --silent 2>/dev/null; then
	mkdir -p /run/mysqld && chown mysql:mysql /run/mysqld
	(mysqld_safe --skip-log-bin --innodb-flush-log-at-trx-commit=0 >/tmp/mysqld.log 2>&1 &)
	for _ in $(seq 30); do mariadb-admin ping --silent 2>/dev/null && break; sleep 1; done
fi
mariadb -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED BY 'root'; FLUSH PRIVILEGES;" 2>/dev/null || true
mariadb -u root -proot -e "SELECT 1" >/dev/null

grep -q " $SITE$" /etc/hosts || echo "127.0.0.1 $SITE" >> /etc/hosts

step "redis"
for port in 13000 11000; do
	redis-cli -p $port ping >/dev/null 2>&1 || redis-server --port $port --daemonize yes --save "" >/dev/null
done
fi

# bench refuses to run as root, so everything from here runs as a plain user.
if [ "$(id -u)" = 0 ]; then
	id frappe >/dev/null 2>&1 || useradd -m -s /bin/bash frappe
	install -m 755 "$(command -v uv)" /usr/local/bin/uv
	chmod o+x "$(dirname "$BUZZ")" && chmod -R a+rwX "$BUZZ"
	git config --system --add safe.directory "$BUZZ"
	# The agent proxy's CA, so pip, uv, yarn and git trust it as the plain user.
	install -o frappe -m 644 /root/.ccr/ca-bundle.crt /home/frappe/ca-bundle.crt
	# A copy the plain user can read: the original may sit in a root-only directory.
	install -o frappe -m 755 "$0" /home/frappe/setup-bench.sh
	exec runuser -u frappe -- env HTTPS_PROXY="${HTTPS_PROXY:-}" HTTP_PROXY="${HTTP_PROXY:-}" \
		NO_PROXY="${NO_PROXY:-}" SSL_CERT_FILE=/home/frappe/ca-bundle.crt REQUESTS_CA_BUNDLE=/home/frappe/ca-bundle.crt \
		NODE_EXTRA_CA_CERTS=/home/frappe/ca-bundle.crt GIT_SSL_CAINFO=/home/frappe/ca-bundle.crt UV_SYSTEM_CERTS=1 \
		YARN_IGNORE_ENGINES=1 \
		HOME=/home/frappe SKIP_ROOT_STEPS=1 bash /home/frappe/setup-bench.sh "$BUZZ" "$SITE"
fi

step "python + bench"
# uv reads uv.toml from the working directory, which may be root-only.
cd "$HOME"
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.14
PYTHON=$(uv python find 3.14)
command -v bench >/dev/null || uv tool install frappe-bench

if [ ! -d "$BENCH/apps/frappe" ]; then
	step "bench init"
	bench init "$BENCH" --skip-redis-config-generation --skip-assets --no-backups --python "$PYTHON"
fi
cd "$BENCH"
jq '.redis_cache="redis://127.0.0.1:13000" | .redis_queue="redis://127.0.0.1:11000" | .redis_socketio="redis://127.0.0.1:13000"' \
	sites/common_site_config.json > /tmp/csc.json && mv /tmp/csc.json sites/common_site_config.json

step "apps"
[ -d apps/bwh_payments ] || bench get-app --skip-assets --branch v1-stable https://github.com/bwhtech/bwh_payments
if [ ! -d apps/frappe_factory_bot ]; then
	rm -rf /tmp/frappe_factory_bot
	git clone -q https://github.com/harshtandiya/frappe_factory_bot /tmp/frappe_factory_bot
	git -C /tmp/frappe_factory_bot checkout -q 48904d0df778513934e92a4e7663c74bfe31bc56
	bench get-app --skip-assets /tmp/frappe_factory_bot
fi
[ -d apps/zoom_integration ] || bench get-app --skip-assets https://github.com/bwhtech/zoom_integration
if [ ! -e apps/buzz ]; then
	# Symlink so the bench always tests the working checkout.
	ln -s "$BUZZ" apps/buzz
	./env/bin/uv pip install -q -e apps/buzz 2>/dev/null || ./env/bin/pip install -q -e apps/buzz
	grep -qx buzz sites/apps.txt || printf "\nbuzz\n" >> sites/apps.txt; sed -i "/^$/d" sites/apps.txt
fi
bench setup requirements --dev

step "site $SITE"
if [ ! -d "sites/$SITE" ]; then
	bench new-site --db-root-password root --admin-password admin "$SITE"
	bench --site "$SITE" install-app zoom_integration
	bench --site "$SITE" install-app buzz
	bench --site "$SITE" set-config allow_tests true
	bench --site "$SITE" set-config host_name "http://$SITE:8000"
fi
step "done"

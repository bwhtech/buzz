#!/usr/bin/env bash
# Runs the buzz suite as parallel shards, each on its own copy of SITE. Tests mostly wait on the
# database, so shards overlap well on one runner. Run from the bench directory.
#
# usage: run-sharded-tests.sh SITE SHARD_COUNT [extra run-parallel-tests options]
set -euo pipefail

SITE=$1
SHARD_COUNT=$2
shift 2
DB_HOST=${DB_HOST:-127.0.0.1}
DB_ROOT_PASSWORD=${DB_ROOT_PASSWORD:-root}
# run-parallel-tests only exits non-zero on failure when CI is set.
export CI=${CI:-true}

mariadb_root() {
	mariadb --host "$DB_HOST" -u root -p"$DB_ROOT_PASSWORD" "$@"
}

site_config_value() {
	python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' \
		"sites/$SITE/site_config.json" "$1"
}

shard_site() {
	if [ "$1" -eq 1 ]; then echo "$SITE"; else echo "${SITE}_shard_$1"; fi
}

clone_site() {
	local shard_site=$1 database=$2 source_database password user_host
	source_database=$(site_config_value db_name)
	password=$(site_config_value db_password)
	user_host=$(mariadb_root -N -e "SELECT host FROM mysql.user WHERE user = '$source_database' LIMIT 1")

	rm -rf "sites/$shard_site"
	cp -r "sites/$SITE" "sites/$shard_site"
	python3 -c 'import json, sys
path, name = sys.argv[1:]
config = json.load(open(path))
config["db_name"] = config["db_user"] = name
json.dump(config, open(path, "w"), indent=1)' "sites/$shard_site/site_config.json" "$database"

	mariadb_root -e "DROP DATABASE IF EXISTS \`$database\`; CREATE DATABASE \`$database\`;
		CREATE OR REPLACE USER '$database'@'$user_host' IDENTIFIED BY '$password';
		GRANT ALL ON \`$database\`.* TO '$database'@'$user_host';"
	mariadb-dump --host "$DB_HOST" -u root -p"$DB_ROOT_PASSWORD" --single-transaction --quick \
		"$source_database" | mariadb_root "$database"
}

run_shard() {
	bench --site "$(shard_site "$1")" run-parallel-tests --app buzz \
		--build-number "$1" --total-builds "$SHARD_COUNT" "${@:2}" > "logs/test-shard-$1.log" 2>&1
}

print_shard_log() {
	if [ "$2" -eq 0 ]; then
		echo "::group::Shard $1 passed"
		cat "logs/test-shard-$1.log"
		echo "::endgroup::"
	else
		echo "::error::Shard $1 failed"
		cat "logs/test-shard-$1.log"
	fi
}

for shard in $(seq 2 "$SHARD_COUNT"); do
	clone_site "$(shard_site "$shard")" "$(site_config_value db_name)_shard_$shard"
done

mkdir -p logs
pids=()
for shard in $(seq 1 "$SHARD_COUNT"); do
	run_shard "$shard" "$@" &
	pids+=("$!")
done

failed=0
for shard in $(seq 1 "$SHARD_COUNT"); do
	status=0
	wait "${pids[$((shard - 1))]}" || status=$?
	print_shard_log "$shard" "$status"
	[ "$status" -eq 0 ] || failed=1
done
exit "$failed"

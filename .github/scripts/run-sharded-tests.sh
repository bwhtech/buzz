#!/usr/bin/env bash
# Runs the buzz suite as parallel shards, each on its own copy of SITE. Tests mostly wait on the
# database, so shards overlap well on one runner. Run from the bench directory on a fresh CI runner.
#
# usage: run-sharded-tests.sh SITE SHARD_COUNT [extra run-parallel-tests options]
set -euo pipefail

SITE=$1
SHARD_COUNT=$2
shift 2
# `root` must match MARIADB_ROOT_PASSWORD on the caller's service.
DB=(--host 127.0.0.1 -u root -proot)
SOURCE_DB=$(jq -r .db_name "sites/$SITE/site_config.json")
PASSWORD=$(jq -r .db_password "sites/$SITE/site_config.json")
USER_HOST=$(mariadb "${DB[@]}" -N -e "SELECT host FROM mysql.user WHERE user = '$SOURCE_DB' LIMIT 1")

clone_site() {
	local database="${SOURCE_DB}_$1"
	cp -r "sites/$SITE" "sites/${SITE}_$1"
	jq --arg name "$database" '.db_name = $name | .db_user = $name' \
		"sites/$SITE/site_config.json" > "sites/${SITE}_$1/site_config.json"
	mariadb "${DB[@]}" -e "CREATE DATABASE \`$database\`;
		CREATE USER '$database'@'$USER_HOST' IDENTIFIED BY '$PASSWORD';
		GRANT ALL ON \`$database\`.* TO '$database'@'$USER_HOST';"
	mariadb-dump "${DB[@]}" "$SOURCE_DB" | mariadb "${DB[@]}" "$database"
}

for shard in $(seq 2 "$SHARD_COUNT"); do
	clone_site "$shard"
done

pids=()
for shard in $(seq 1 "$SHARD_COUNT"); do
	site=$SITE
	[ "$shard" -eq 1 ] || site="${SITE}_$shard"
	bench --site "$site" run-parallel-tests --app buzz --build-number "$shard" \
		--total-builds "$SHARD_COUNT" "$@" > "logs/test-shard-$shard.log" 2>&1 &
	pids+=("$!")
done

# run-parallel-tests exits non-zero on failure only when CI is set, as it is on GitHub runners.
failed=0
for shard in $(seq 1 "$SHARD_COUNT"); do
	wait "${pids[$((shard - 1))]}" || { failed=1; echo "::error::Shard $shard failed"; }
	cat "logs/test-shard-$shard.log"
done
exit "$failed"

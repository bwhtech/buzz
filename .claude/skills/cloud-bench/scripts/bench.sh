#!/usr/bin/env bash
# Run bench as the frappe user from root: bench.sh --site buzz.localhost run-tests --module x.y
cmd=$(printf '%q ' "$@")
exec runuser -u frappe -- bash -c "export PATH=\$HOME/.local/bin:\$PATH; cd ~/frappe-bench && bench $cmd"

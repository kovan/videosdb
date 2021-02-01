#!/usr/bin/env bash
DEFAULT_API_FILE="$HOME/.ipfs/api"
API_FILE="${IPFS_PATH-$DEFAULT_API_FILE}"

if [ -e "$API_FILE" ]; then
	echo "IPFS API is already running"
	exit 1
fi

PORT=5001

printf "/ip4/127.0.0.1/tcp/$PORT" > "$API_FILE"


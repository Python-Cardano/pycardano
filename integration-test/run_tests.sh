#!/bin/bash

set -e
set -o pipefail

ROOT=$(pwd)

poetry install

# Cleanup containers and volumes in case there is any running
docker-compose down --volumes --remove-orphans

# Run alonzo integration tests
./bootstrap.sh local-alonzo

# Launch containers
docker-compose up -d

export PAYMENT_KEY="$ROOT"/configs/local-alonzo/shelley/utxo-keys/utxo1.skey
export EXTENDED_PAYMENT_KEY="$ROOT"/keys/extended.skey
export POOL_ID=$(cat "$ROOT"/keys/pool/pool.id)

# Wait for stake pool to start producing blocks
sleep 8

poetry run pytest -s -n 4 "$ROOT"/test

# Cleanup
docker-compose down --volumes --remove-orphans
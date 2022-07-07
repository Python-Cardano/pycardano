#!/bin/bash

set -e
set -o pipefail

ROOT=$(pwd)

poetry install

##########
# Alonzo #
##########
#
## Cleanup containers and volumes in case there is any running
#docker-compose down --volumes --remove-orphans
#
## Run alonzo integration tests
#./bootstrap.sh local-alonzo
#
## Launch containers
#docker-compose up -d
#
#export PAYMENT_KEY="$ROOT"/configs/local-alonzo/shelley/utxo-keys/utxo1.skey
#export EXTENDED_PAYMENT_KEY="$ROOT"/keys/extended.skey
#export POOL_ID=$(cat "$ROOT"/keys/pool/pool.id)
#
## Wait for stake pool to start producing blocks
#sleep 20
#
#poetry run pytest -s -vv -n 4 "$ROOT"/test -m "not (post_alonzo)"
#
## Cleanup
#docker-compose down --volumes --remove-orphans

#########
# Vasil #
#########

# Cleanup containers and volumes in case there is any running
docker-compose down --volumes --remove-orphans

# Run alonzo integration tests
./bootstrap.sh local-vasil

# Launch containers
docker-compose up -d

export PAYMENT_KEY="$ROOT"/configs/local-vasil/shelley/utxo-keys/utxo1.skey
export EXTENDED_PAYMENT_KEY="$ROOT"/keys/extended.skey
export POOL_ID=$(cat "$ROOT"/keys/pool/pool.id)

# Wait for stake pool to start producing blocks
sleep 60

poetry run pytest -s -vv -n 4 "$ROOT"/test

# Cleanup
docker-compose down --volumes --remove-orphans
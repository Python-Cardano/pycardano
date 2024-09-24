#!/bin/bash

set -e
set -o pipefail

ROOT=$(pwd)

poetry install
#poetry run pip install ogmios

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
#sleep 10
#
## Cleanup
#docker-compose down --volumes --remove-orphans
#
##########
## Vasil #
##########
#
## Cleanup containers and volumes in case there is any running
#docker-compose down --volumes --remove-orphans
#
## Run integration tests
#./bootstrap.sh local-vasil
#
## Launch containers
#docker-compose up -d
#
#export PAYMENT_KEY="$ROOT"/configs/local-vasil/shelley/utxo-keys/utxo1.skey
#export EXTENDED_PAYMENT_KEY="$ROOT"/keys/extended.skey
#export POOL_ID=$(cat "$ROOT"/keys/pool/pool.id)
#
## Wait for stake pool to start producing blocks
#sleep 30
#
#poetry run pytest -s -vv -n 4 "$ROOT"/test
#
## Cleanup
#docker-compose down --volumes --remove-orphans


#########
# Chang #
#########

# Cleanup containers and volumes in case there is any running
docker compose -f docker-compose-chang.yml down --volumes --remove-orphans

# Run integration tests
./bootstrap.sh local-chang

# Launch containers
docker compose -f docker-compose-chang.yml up -d

export PAYMENT_KEY="$ROOT"/configs/local-chang/shelley/utxo-keys/utxo1.skey
export EXTENDED_PAYMENT_KEY="$ROOT"/keys/extended.skey
export POOL_ID=$(cat "$ROOT"/keys/pool/pool.id)

# Wait for stake pool to start producing blocks
sleep 30

poetry run pytest -m "not (CardanoCLI)" -s -vv -n 4 "$ROOT"/test  --cov=pycardano --cov-config=../.coveragerc --cov-report=xml:../coverage.xml

# Cleanup
docker compose -f docker-compose-chang.yml down --volumes --remove-orphans
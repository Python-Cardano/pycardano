#!/bin/bash

set -e
set -o pipefail

ROOT=$(pwd)

poetry install

# Run alonzo integration tests
./bootstrap.sh local-alonzo

# Cleanup containers and volumes in case there is any running
docker-compose down --volumes

# Launch containers
docker-compose up -d

export PAYMENT_KEY="$ROOT"/configs/local-alonzo/shelley/utxo-keys/utxo1.skey
export EXTENDED_PAYMENT_KEY="$ROOT"/keys/extended.skey
poetry run pytest -s "$ROOT"/test

# Cleanup
docker-compose down --volumes

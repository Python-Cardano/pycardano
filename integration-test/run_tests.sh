#!/bin/sh

ROOT=$(pwd)

poetry install

# Run alonzo integration tests
./bootstrap.sh local-alonzo
docker-compose up -d

export PAYMENT_KEY="$ROOT"/configs/local-alonzo/shelley/utxo-keys/utxo1.skey
poetry run pytest -s "$ROOT"/test

docker-compose down --volume

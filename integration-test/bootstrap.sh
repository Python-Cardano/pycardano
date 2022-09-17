#!/bin/sh

set -e

if [ "$#" -ne 1 ] || [ "$1" = "-h" ]; then
  echo "Bootstrap network configs and environment variables."
  echo "Usage: $0 [network] (e.g. local-alonzo, testnet, mainnet)"
  exit 0
fi

if [ -d "./tmp_configs" ]; then
  echo "Removing tmp_configs"
  rm -rf ./tmp_configs
fi

echo "Copying configs to tmp_configs"
cp -r configs tmp_configs

NETWORK=$1

echo "Bootstrapping network: $NETWORK"

if [ "$NETWORK" = "local-alonzo" ] || [ "$NETWORK" = "local-vasil" ]; then
  echo "Updating byron startTime to present in local mode, $NETWORK era"
  jq -M ".startTime = ""$(date +%s)" configs/"$NETWORK"/byron-genesis.json > \
    tmp_configs/"$NETWORK"/byron-genesis.json
fi

echo "NETWORK=$NETWORK" >.env
NETWORK_MAGIC=$(jq .networkMagic tmp_configs/"$NETWORK"/shelley-genesis.json)
echo "Found network magic: $NETWORK_MAGIC"
echo "NETWORK_MAGIC=$NETWORK_MAGIC" >>.env
echo "Done"

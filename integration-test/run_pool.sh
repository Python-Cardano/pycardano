#!/bin/bash

echo "$NETWORK"
if [ "$NETWORK" = "local-alonzo" ] || [ "$NETWORK" = "local-vasil" ] || [ "$NETWORK" = "local-chang" ]
then

  # Waiting for BFT node to be ready
  while [ ! -S /ipc/node.socket ]
  do
    sleep 0.1
  done

  sleep 5

  export CARDANO_NODE_SOCKET_PATH=/ipc/node.socket

  cardano-cli alonzo transaction submit \
    --tx-file /code/keys/pool/pool_registration_tx.signed \
    --testnet-magic 42

  mkdir -p /data/db
  chmod 400 /code/keys/pool/*.skey
  chmod 400 /code/keys/pool/*.vkey

  # Start pool node
  cardano-node run \
    --config /code/tmp_configs/"$NETWORK"/config.json \
    --topology /code/keys/pool/topology.json \
    --database-path /data/db \
    --socket-path /ipc/pool.socket \
    --shelley-kes-key /code/keys/pool/kes.skey \
    --shelley-vrf-key /code/keys/pool/vrf.skey \
    --shelley-operational-certificate /code/keys/pool/node.cert \
    --host-addr 0.0.0.0 \
    --port 3000
fi
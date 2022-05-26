#!/bin/bash

echo "$NETWORK"
if [ "$NETWORK" = "local-alonzo" ]
then

# Waiting for BFT node to be ready
while [ ! -S /ipc/node.socket ]
do
  sleep 0.1
done

  export CARDANO_NODE_SOCKET_PATH=/ipc/node.socket

  cardano-cli transaction build \
    --tx-in 732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5#0 \
    --tx-out "$(cat /code/keys/pool/full.addr)"+450000000000 \
    --change-address "$(cat /code/tmp_configs/local-alonzo/shelley/utxo-keys/payment.addr)" \
    --out-file tx.raw \
    --testnet-magic 42 \
    --certificate-file /code/keys/pool/stake.cert \
    --certificate-file /code/keys/pool/pool-registration.cert \
    --certificate-file /code/keys/pool/delegation.cert \
    --witness-override 3

  cat tx.raw

  cardano-cli transaction sign \
    --tx-body-file tx.raw \
    --signing-key-file /code/tmp_configs/local-alonzo/shelley/utxo-keys/utxo1.skey \
    --signing-key-file /code/keys/pool/stake.skey \
    --signing-key-file /code/keys/pool/cold.skey \
    --testnet-magic 42 \
    --out-file tx.signed

  cat tx.signed

  cardano-cli transaction submit \
    --tx-file tx.signed \
    --testnet-magic 42

  mkdir -p /data/db
  chmod 400 /code/keys/pool/*.skey
  chmod 400 /code/keys/pool/*.vkey

  # Start pool node
  cardano-node run \
    --config /code/tmp_configs/"$NETWORK"/config.json \
    --topology /code/keys/pool/topology.json \
    --database-path /data/db \
    --socket-path /data/db/node.socket \
    --shelley-kes-key /code/keys/pool/kes.skey \
    --shelley-vrf-key /code/keys/pool/vrf.skey \
    --shelley-operational-certificate /code/keys/pool/node.cert \
    --port 3000
fi
#!/bin/sh

if [ "$NETWORK" = "local" ]
then
  cardano-node run \
    --config /code/tmp_configs/"$NETWORK"/"$NETWORK"-config.json \
    --topology /code/tmp_configs/"$NETWORK"/"$NETWORK"-topology.json \
    --database-path /data/db --socket-path /ipc/node.socket \
    --shelley-kes-key /code/tmp_configs/"$NETWORK"/shelley/kes.skey \
    --shelley-vrf-key /code/tmp_configs/"$NETWORK"/shelley/vrf.skey \
    --shelley-operational-certificate /code/tmp_configs/"$NETWORK"/shelley/node.cert
else
  cardano-node run \
    --config /code/tmp_configs/"$NETWORK"/"$NETWORK"-config.json \
    --topology /code/tmp_configs/"$NETWORK"/"$NETWORK"-topology.json \
    --database-path /data/db --socket-path /ipc/node.socket
fi
#!/bin/bash
# Submit a Conway governance action to add PlutusV2 cost model.
# Runs inside the cardano-pool-1 container via `docker exec`.
# cardano-node 10.7+ no longer auto-initializes PlutusV2 cost model at
# the Babbage hard fork, so it has to be added by an explicit parameter
# update action. conway-genesis is set up with zero thresholds so the
# action ratifies trivially.

set -euo pipefail

NETWORK="${NETWORK:-local-chang}"
TESTNET_MAGIC="${TESTNET_MAGIC:-42}"
CFG=/code/tmp_configs/$NETWORK
POOL=/code/keys/pool
COST_MODEL_FILE=/tmp/v2-cost-model.json
ANCHOR_FILE=/tmp/anchor.json
ACTION_FILE=/tmp/v2.action
TX_RAW=/tmp/v2.tx.raw
TX_SIGNED=/tmp/v2.tx.signed
ANCHOR_PORT=18080

export CARDANO_NODE_SOCKET_PATH=/ipc/node.socket

# Submit the gov action from the pool's wallet (full.addr ≈ 450K ADA) rather
# than utxo1 (which the integration tests need intact). The deposit (100K)
# returns to the pool's own stake key after enactment, so funds stay within
# the pool wallet — utxo1 is never touched.
PAYMENT_ADDR=$(cat "$POOL/full.addr")

echo "[gov] Building V2 cost-model file from alonzo-genesis…"
# alonzo-genesis stores PlutusV2 either as a dict (legacy) or a list. Normalize
# to a list of values sorted by key (canonical order matches list form).
jq '.costModels.PlutusV2
    | if type == "object"
        then to_entries | sort_by(.key) | map(.value)
        else .
      end
    | { PlutusV2: . }' "$CFG/alonzo-genesis.json" > "$COST_MODEL_FILE"
echo "[gov] V2 length: $(jq '.PlutusV2 | length' "$COST_MODEL_FILE")"

# cardano-cli `transaction build` always verifies that --anchor-url is
# fetchable and its body hashes to --anchor-data-hash. Serve a tiny static
# anchor file locally over http so the verification succeeds offline.
echo '{"title":"add PlutusV2 cost model","authors":["pycardano-tests"]}' > "$ANCHOR_FILE"
ANCHOR_HASH=$(cardano-cli hash anchor-data --file-text "$ANCHOR_FILE")
echo "[gov] anchor hash: $ANCHOR_HASH"

ANCHOR_LEN=$(stat -c%s "$ANCHOR_FILE")
RESPONSE_FILE=/tmp/anchor.http
{
  printf 'HTTP/1.0 200 OK\r\n'
  printf 'Content-Type: application/json\r\n'
  printf 'Content-Length: %d\r\n' "$ANCHOR_LEN"
  printf '\r\n'
  cat "$ANCHOR_FILE"
} > "$RESPONSE_FILE"

socat -d TCP-LISTEN:"$ANCHOR_PORT",fork,reuseaddr SYSTEM:"cat $RESPONSE_FILE" &
SOCAT_PID=$!
trap 'kill $SOCAT_PID 2>/dev/null || true' EXIT
sleep 1
echo "[gov] anchor server up on :$ANCHOR_PORT (pid $SOCAT_PID)"

ANCHOR_URL="http://127.0.0.1:$ANCHOR_PORT/anchor.json"

echo "[gov] Creating parameter-update action…"
cardano-cli conway governance action create-protocol-parameters-update \
  --testnet \
  --governance-action-deposit 100000000000 \
  --deposit-return-stake-verification-key-file "$POOL/stake.vkey" \
  --anchor-url "$ANCHOR_URL" \
  --anchor-data-hash "$ANCHOR_HASH" \
  --cost-model-file "$COST_MODEL_FILE" \
  --out-file "$ACTION_FILE"

echo "[gov] Selecting UTxO at $PAYMENT_ADDR…"
TX_IN=$(cardano-cli conway query utxo \
  --address "$PAYMENT_ADDR" \
  --testnet-magic "$TESTNET_MAGIC" \
  --output-json | jq -r 'keys[0]')
echo "[gov] tx-in: $TX_IN"

echo "[gov] Building transaction with proposal…"
cardano-cli conway transaction build \
  --testnet-magic "$TESTNET_MAGIC" \
  --tx-in "$TX_IN" \
  --change-address "$PAYMENT_ADDR" \
  --proposal-file "$ACTION_FILE" \
  --out-file "$TX_RAW"

echo "[gov] Signing…"
cardano-cli conway transaction sign \
  --testnet-magic "$TESTNET_MAGIC" \
  --tx-body-file "$TX_RAW" \
  --signing-key-file "$POOL/payment.skey" \
  --out-file "$TX_SIGNED"

echo "[gov] Submitting…"
cardano-cli conway transaction submit \
  --testnet-magic "$TESTNET_MAGIC" \
  --tx-file "$TX_SIGNED"

echo "[gov] Waiting for V2 cost model to appear on chain…"
for i in $(seq 1 60); do
  if cardano-cli conway query protocol-parameters --testnet-magic "$TESTNET_MAGIC" 2>/dev/null \
      | jq -e '.costModels.PlutusV2' >/dev/null; then
    echo "[gov] V2 cost model is now on chain (after ${i} iterations)."
    # Record the ratified action's id so test_governance can chain to it.
    # `cardano-cli ... transaction txid` returns JSON like {"txhash":"..."}.
    TX_ID=$(cardano-cli conway transaction txid --tx-file "$TX_SIGNED" | jq -r '.txhash // .')
    printf '{"tx_id":"%s","index":0}\n' "$TX_ID" > "$CFG/last_param_action.json"
    echo "[gov] wrote prev-action id to $CFG/last_param_action.json (tx=$TX_ID)"
    exit 0
  fi
  sleep 5
done

echo "[gov] ERROR: V2 cost model did not appear within timeout." >&2
cardano-cli conway query protocol-parameters --testnet-magic "$TESTNET_MAGIC" \
  | jq '.costModels | keys' >&2
exit 1

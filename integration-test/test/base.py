"""An example that demonstrates low-level construction of a transaction."""

import os

import ogmios as python_ogmios
from retry import retry

from pycardano import *

TEST_RETRIES = 6


def _fetch_protocol_param(self) -> ProtocolParameters:
    with python_ogmios.Client(self.host, self.port, self.secure) as client:
        protocol_parameters, _ = client.query_protocol_parameters.execute()
        pyc_protocol_params = ProtocolParameters(
            min_fee_constant=protocol_parameters.min_fee_constant.lovelace,
            min_fee_coefficient=protocol_parameters.min_fee_coefficient,
            min_pool_cost=protocol_parameters.min_stake_pool_cost.lovelace,
            max_block_size=protocol_parameters.max_block_body_size.get("bytes"),
            max_tx_size=protocol_parameters.max_transaction_size.get("bytes"),
            max_block_header_size=protocol_parameters.max_block_header_size.get(
                "bytes"
            ),
            key_deposit=protocol_parameters.stake_credential_deposit.lovelace,
            pool_deposit=protocol_parameters.stake_pool_deposit.lovelace,
            pool_influence=eval(protocol_parameters.stake_pool_pledge_influence),
            monetary_expansion=eval(protocol_parameters.monetary_expansion),
            treasury_expansion=eval(protocol_parameters.treasury_expansion),
            decentralization_param=None,  # TODO
            extra_entropy=protocol_parameters.extra_entropy,
            protocol_major_version=protocol_parameters.version.get("major"),
            protocol_minor_version=protocol_parameters.version.get("minor"),
            min_utxo=None,
            price_mem=eval(protocol_parameters.script_execution_prices.get("memory")),
            price_step=eval(protocol_parameters.script_execution_prices.get("cpu")),
            max_tx_ex_mem=protocol_parameters.max_execution_units_per_transaction.get(
                "memory"
            ),
            max_tx_ex_steps=protocol_parameters.max_execution_units_per_transaction.get(
                "cpu"
            ),
            max_block_ex_mem=protocol_parameters.max_execution_units_per_block.get(
                "memory"
            ),
            max_block_ex_steps=protocol_parameters.max_execution_units_per_block.get(
                "cpu"
            ),
            max_val_size=protocol_parameters.max_value_size.get("bytes"),
            collateral_percent=protocol_parameters.collateral_percentage,
            max_collateral_inputs=protocol_parameters.max_collateral_inputs,
            coins_per_utxo_word=ALONZO_COINS_PER_UTXO_WORD,
            coins_per_utxo_byte=protocol_parameters.min_utxo_deposit_coefficient,
            maximum_reference_scripts_size=protocol_parameters.max_ref_script_size,
            min_fee_reference_scripts=protocol_parameters.min_fee_ref_scripts,
            cost_models=self._parse_cost_models(protocol_parameters.plutus_cost_models),
        )
        return pyc_protocol_params


@retry(tries=10, delay=4)
def check_chain_context(chain_context):
    print(f"Current chain tip: {chain_context.last_block_slot}")


class TestBase:
    # Define chain context
    NETWORK = Network.TESTNET

    # TODO: Bring back kupo test
    KUPO_URL = "http://localhost:1442"

    python_ogmios.OgmiosChainContext._fetch_protocol_param = _fetch_protocol_param
    chain_context = python_ogmios.OgmiosChainContext(
        host="localhost",
        port=1337,
        network=Network.TESTNET,
        refetch_chain_tip_interval=1,
    )

    check_chain_context(chain_context)

    payment_key_path = os.environ.get("PAYMENT_KEY")
    extended_key_path = os.environ.get("EXTENDED_PAYMENT_KEY")
    if not payment_key_path or not extended_key_path:
        raise Exception(
            "Cannot find payment key. Please specify environment variable PAYMENT_KEY and extended_key_path"
        )
    payment_skey = PaymentSigningKey.load(payment_key_path)
    payment_vkey = PaymentVerificationKey.from_signing_key(payment_skey)
    extended_payment_skey = PaymentExtendedSigningKey.load(extended_key_path)
    extended_payment_vkey = PaymentExtendedVerificationKey.from_signing_key(
        extended_payment_skey
    )

    payment_key_pair = PaymentKeyPair.generate()
    stake_key_pair = StakeKeyPair.generate()

    @retry(tries=TEST_RETRIES, delay=3)
    def assert_output(self, target_address, target_output):
        utxos = self.chain_context.utxos(target_address)
        found = False

        for utxo in utxos:
            output = utxo.output
            if output == target_output:
                found = True

        assert found, f"Cannot find target UTxO in address: {target_address}"

    @retry(tries=TEST_RETRIES, delay=6, backoff=2, jitter=(1, 3))
    def fund(self, source_address, source_key, target_address, amount=5000000):
        builder = TransactionBuilder(self.chain_context)

        builder.add_input_address(source_address)
        output = TransactionOutput(target_address, amount)
        builder.add_output(output)

        signed_tx = builder.build_and_sign([source_key], source_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)
        self.assert_output(target_address, target_output=output)

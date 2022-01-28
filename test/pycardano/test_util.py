from pycardano.hash import DATUM_HASH_SIZE, SCRIPT_HASH_SIZE
from pycardano.transaction import TransactionOutput
from pycardano.utils import min_lovelace
from test.pycardano.util import TEST_ADDR, chain_context


def test_min_lovelace_ada_only(chain_context):
    tx_out = TransactionOutput.from_primitive(
        [TEST_ADDR, 2000000]
    )

    assert min_lovelace(tx_out, chain_context) == chain_context.protocol_param.min_utxo


class TestMinLoveLaceMultiAsset:

    # Tests copied from: https://github.com/input-output-hk/cardano-ledger/blob/master/doc/explanations/min-utxo-alonzo.rst#example-min-ada-value-calculations-and-current-constants

    def test_min_lovelace_multi_asset_1(self, chain_context):
        tx_out = TransactionOutput.from_primitive(
            [TEST_ADDR,
             [2000000,
              {
                  b"1" * SCRIPT_HASH_SIZE: {
                      b"": 1000000
                  }
              }]]
        )
        assert min_lovelace(tx_out, chain_context) == 1310316

    def test_min_lovelace_multi_asset_2(self, chain_context):
        tx_out = TransactionOutput.from_primitive(
            [TEST_ADDR,
             [2000000,
              {
                  b"1" * SCRIPT_HASH_SIZE: {
                      b"1": 1000000
                  }
              }]]
        )

        assert min_lovelace(tx_out, chain_context) == 1344798

    def test_min_lovelace_multi_asset_3(self, chain_context):
        tx_out = TransactionOutput.from_primitive(
            [TEST_ADDR,
             [2000000,
              {
                  b"1" * SCRIPT_HASH_SIZE: {
                      b"1": 1000000,
                      b"2": 2000000,
                      b"3": 3000000
                  }
              }]]
        )

        assert min_lovelace(tx_out, chain_context) == 1448244

    def test_min_lovelace_multi_asset_4(self, chain_context):
        tx_out = TransactionOutput.from_primitive(
            [TEST_ADDR,
             [2000000,
              {
                  b"1" * SCRIPT_HASH_SIZE: {
                      b"": 1000000
                  },
                  b"2" * SCRIPT_HASH_SIZE: {
                      b"": 1000000
                  }
              }]]
        )

        assert min_lovelace(tx_out, chain_context) == 1482726

    def test_min_lovelace_multi_asset_5(self, chain_context):
        tx_out = TransactionOutput.from_primitive(
            [TEST_ADDR,
             [2000000,
              {
                  b"1" * SCRIPT_HASH_SIZE: {
                      b"1": 1000000
                  },
                  b"2" * SCRIPT_HASH_SIZE: {
                      b"2": 1000000
                  }
              }]]
        )

        assert min_lovelace(tx_out, chain_context) == 1517208

    def test_min_lovelace_multi_asset_6(self, chain_context):
        tx_out = TransactionOutput.from_primitive(
            [TEST_ADDR,
             [2000000,
              {
                  b"1" * SCRIPT_HASH_SIZE: {
                      i.to_bytes(1, byteorder='big'): 1000000 * i for i in range(32)
                  },
                  b"2" * SCRIPT_HASH_SIZE: {
                      i.to_bytes(1, byteorder='big'): 1000000 * i for i in range(32, 64)
                  },
                  b"3" * SCRIPT_HASH_SIZE: {
                      i.to_bytes(1, byteorder='big'): 1000000 * i for i in range(64, 96)
                  }
              }]]
        )

        assert min_lovelace(tx_out, chain_context) == 6896400

    def test_min_lovelace_multi_asset_7(self, chain_context):
        tx_out = TransactionOutput.from_primitive(
            [TEST_ADDR,
             [2000000,
              {
                  b"1" * SCRIPT_HASH_SIZE: {
                      b"": 1000000
                  }
              }],
             b"1" * DATUM_HASH_SIZE]
        )

        assert min_lovelace(tx_out, chain_context) == 1655136

    def test_min_lovelace_multi_asset_8(self, chain_context):
        tx_out = TransactionOutput.from_primitive(
            [TEST_ADDR,
             [2000000,
              {
                  b"1" * SCRIPT_HASH_SIZE: {
                      b"1" * 32: 1000000,
                      b"2" * 32: 1000000,
                      b"3" * 32: 1000000,
                  }
              }],
             b"1" * DATUM_HASH_SIZE]
        )

        assert min_lovelace(tx_out, chain_context) == 2172366

    def test_min_lovelace_multi_asset_9(self, chain_context):
        tx_out = TransactionOutput.from_primitive(
            [TEST_ADDR,
             [2000000,
              {
                  b"1" * SCRIPT_HASH_SIZE: {
                      b"": 1000000,
                  },
                  b"2" * SCRIPT_HASH_SIZE: {
                      b"": 1000000,
                  }
              }],
             b"1" * DATUM_HASH_SIZE]
        )

        assert min_lovelace(tx_out, chain_context) == 1827546

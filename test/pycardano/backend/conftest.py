import json
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(scope="session")
def genesis_json():
    return {
        "activeSlotsCoeff": 0.05,
        "epochLength": 432000,
        "genDelegs": {
            "637f2e950b0fd8f8e3e811c5fbeb19e411e7a2bf37272b84b29c1a0b": {
                "delegate": "aae9293510344ddd636364c2673e34e03e79e3eefa8dbaa70e326f7d",
                "vrf": "227116365af2ed943f1a8b5e6557bfaa34996f1578eec667a5e2b361c51e4ce7",
            },
            "8a4b77c4f534f8b8cc6f269e5ebb7ba77fa63a476e50e05e66d7051c": {
                "delegate": "d15422b2e8b60e500a82a8f4ceaa98b04e55a0171d1125f6c58f8758",
                "vrf": "0ada6c25d62db5e1e35d3df727635afa943b9e8a123ab83785e2281605b09ce2",
            },
            "b00470cd193d67aac47c373602fccd4195aad3002c169b5570de1126": {
                "delegate": "b3b539e9e7ed1b32fbf778bf2ebf0a6b9f980eac90ac86623d11881a",
                "vrf": "0ff0ce9b820376e51c03b27877cd08f8ba40318f1a9f85a3db0b60dd03f71a7a",
            },
            "b260ffdb6eba541fcf18601923457307647dce807851b9d19da133ab": {
                "delegate": "7c64eb868b4ef566391a321c85323f41d2b95480d7ce56ad2abcb022",
                "vrf": "7fb22abd39d550c9a022ec8104648a26240a9ff9c88b8b89a6e20d393c03098e",
            },
            "ced1599fd821a39593e00592e5292bdc1437ae0f7af388ef5257344a": {
                "delegate": "de7ca985023cf892f4de7f5f1d0a7181668884752d9ebb9e96c95059",
                "vrf": "c301b7fc4d1b57fb60841bcec5e3d2db89602e5285801e522fce3790987b1124",
            },
            "dd2a7d71a05bed11db61555ba4c658cb1ce06c8024193d064f2a66ae": {
                "delegate": "1e113c218899ee7807f4028071d0e108fc790dade9fd1a0d0b0701ee",
                "vrf": "faf2702aa4893c877c622ab22dfeaf1d0c8aab98b837fe2bf667314f0d043822",
            },
            "f3b9e74f7d0f24d2314ea5dfbca94b65b2059d1ff94d97436b82d5b4": {
                "delegate": "fd637b08cc379ef7b99c83b416458fcda8a01a606041779331008fb9",
                "vrf": "37f2ea7c843a688159ddc2c38a2f997ab465150164a9136dca69564714b73268",
            },
        },
        "initialFunds": {},
        "maxKESEvolutions": 62,
        "maxLovelaceSupply": 45000000000000000,
        "networkId": "Testnet",
        "networkMagic": 1,
        "protocolParams": {
            "protocolVersion": {"minor": 0, "major": 2},
            "decentralisationParam": 1,
            "eMax": 18,
            "extraEntropy": {"tag": "NeutralNonce"},
            "maxTxSize": 16384,
            "maxBlockBodySize": 65536,
            "maxBlockHeaderSize": 1100,
            "minFeeA": 44,
            "minFeeB": 155381,
            "minUTxOValue": 1000000,
            "poolDeposit": 500000000,
            "minPoolCost": 340000000,
            "keyDeposit": 2000000,
            "nOpt": 150,
            "rho": 0.003,
            "tau": 0.20,
            "a0": 0.3,
        },
        "securityParam": 2160,
        "slotLength": 1,
        "slotsPerKESPeriod": 129600,
        "staking": {"pools": {}, "stake": {}},
        "systemStart": "2022-06-01T00:00:00Z",
        "updateQuorum": 5,
    }


@pytest.fixture(autouse=True)
def mock_check_socket():
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_socket", return_value=True
    ), patch("pathlib.Path.is_file", return_value=True):
        yield


@pytest.fixture(scope="session")
def genesis_file(genesis_json):
    genesis_file_path = Path.cwd() / "shelley-genesis.json"

    with open(genesis_file_path, "w", encoding="utf-8") as file:
        file.write(json.dumps(genesis_json, indent=4))

    yield genesis_file_path

    try:
        genesis_file_path.unlink()
    except FileNotFoundError:
        pass


@pytest.fixture(scope="session")
def config_file():
    config_file_path = Path.cwd() / "config.json"

    config_json = {
        "AlonzoGenesisFile": "alonzo-genesis.json",
        "AlonzoGenesisHash": "7e94a15f55d1e82d10f09203fa1d40f8eede58fd8066542cf6566008068ed874",
        "ApplicationName": "cardano-sl",
        "ApplicationVersion": 0,
        "ByronGenesisFile": "byron-genesis.json",
        "ByronGenesisHash": "d4b8de7a11d929a323373cbab6c1a9bdc931beffff11db111cf9d57356ee1937",
        "ConwayGenesisFile": "conway-genesis.json",
        "ConwayGenesisHash": "f28f1c1280ea0d32f8cd3143e268650d6c1a8e221522ce4a7d20d62fc09783e1",
        "EnableP2P": True,
        "LastKnownBlockVersion-Alt": 0,
        "LastKnownBlockVersion-Major": 2,
        "LastKnownBlockVersion-Minor": 0,
        "Protocol": "Cardano",
        "RequiresNetworkMagic": "RequiresMagic",
        "ShelleyGenesisFile": "shelley-genesis.json",
        "ShelleyGenesisHash": "162d29c4e1cf6b8a84f2d692e67a3ac6bc7851bc3e6e4afe64d15778bed8bd86",
        "TargetNumberOfActivePeers": 20,
        "TargetNumberOfEstablishedPeers": 50,
        "TargetNumberOfKnownPeers": 100,
        "TargetNumberOfRootPeers": 100,
        "TraceAcceptPolicy": True,
        "TraceBlockFetchClient": False,
        "TraceBlockFetchDecisions": False,
        "TraceBlockFetchProtocol": False,
        "TraceBlockFetchProtocolSerialised": False,
        "TraceBlockFetchServer": False,
        "TraceChainDb": True,
        "TraceChainSyncBlockServer": False,
        "TraceChainSyncClient": False,
        "TraceChainSyncHeaderServer": False,
        "TraceChainSyncProtocol": False,
        "TraceConnectionManager": True,
        "TraceDNSResolver": True,
        "TraceDNSSubscription": True,
        "TraceDiffusionInitialization": True,
        "TraceErrorPolicy": True,
        "TraceForge": True,
        "TraceHandshake": False,
        "TraceInboundGovernor": True,
        "TraceIpSubscription": True,
        "TraceLedgerPeers": True,
        "TraceLocalChainSyncProtocol": False,
        "TraceLocalErrorPolicy": True,
        "TraceLocalHandshake": False,
        "TraceLocalRootPeers": True,
        "TraceLocalTxSubmissionProtocol": False,
        "TraceLocalTxSubmissionServer": False,
        "TraceMempool": True,
        "TraceMux": False,
        "TracePeerSelection": True,
        "TracePeerSelectionActions": True,
        "TracePublicRootPeers": True,
        "TraceServer": True,
        "TraceTxInbound": False,
        "TraceTxOutbound": False,
        "TraceTxSubmissionProtocol": False,
        "TracingVerbosity": "NormalVerbosity",
        "TurnOnLogMetrics": True,
        "TurnOnLogging": True,
        "defaultBackends": ["KatipBK"],
        "defaultScribes": [["StdoutSK", "stdout"]],
        "hasEKG": 12788,
        "hasPrometheus": ["0.0.0.0", 12798],
        "minSeverity": "Info",
        "options": {
            "mapBackends": {
                "cardano.node.metrics": ["EKGViewBK"],
                "cardano.node.resources": ["EKGViewBK"],
            },
            "mapSubtrace": {"cardano.node.metrics": {"subtrace": "Neutral"}},
        },
        "rotation": {
            "rpKeepFilesNum": 10,
            "rpLogLimitBytes": 5000000,
            "rpMaxAgeHours": 24,
        },
        "setupBackends": ["KatipBK"],
        "setupScribes": [
            {
                "scFormat": "ScText",
                "scKind": "StdoutSK",
                "scName": "stdout",
                "scRotation": None,
            }
        ],
    }

    with open(config_file_path, "w", encoding="utf-8") as file:
        file.write(json.dumps(config_json, indent=4))

    yield config_file_path

    try:
        config_file_path.unlink()
    except FileNotFoundError:
        pass

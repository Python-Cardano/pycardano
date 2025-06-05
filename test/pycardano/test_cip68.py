import pytest
from dataclasses import dataclass

from pycardano.cip.cip68 import (
    CIP68TokenName,
    CIP68ReferenceNFTName,
    CIP68UserNFTName,
    CIP68UserFTName,
    CIP68UserRFTName,
    CIP68Datum,
    InvalidCIP68ReferenceNFT,
    CIP68UserNFTFiles,
    CIP68UserNFTMetadata
)
from pycardano.plutus import Unit, PlutusData


def assert_roundtrip(obj: PlutusData) -> None:
    serialized = obj.to_cbor_hex()
    deserialized = obj.__class__.from_cbor(serialized)
    reserialized = deserialized.to_cbor_hex()
    assert serialized == reserialized


@pytest.mark.parametrize("reference_nft", [
    ("000643b04d794e4654", "000643b04d794e4654"),  # Reference NFT (100) -> Reference NFT (100)
    ("000de1404d794e4654", "000643b04d794e4654"),  # User NFT (222) -> Reference NFT (100)
    ("0014df10546f6b656e", "000643b0546f6b656e"),  # User FT (333) -> Reference NFT (100)
    ("001bc280546f6b656e", "000643b0546f6b656e"),  # User RFT (444) -> Reference NFT (100)
])

def test_reference_token(reference_nft):
    token_name, expected_reference_token = reference_nft
    token = CIP68TokenName(token_name)
    ref_token = token.reference_token
    assert ref_token.payload == bytes.fromhex(expected_reference_token)
    assert ref_token.label == 100


@pytest.mark.parametrize("token_class,valid_token,expected_label", [
    (CIP68ReferenceNFTName, "000643b04d794e4654", 100),
    (CIP68UserNFTName, "000de1404d794e4654", 222),
    (CIP68UserFTName, "0014df10546f6b656e", 333),
    (CIP68UserRFTName, "001bc280546f6b656e", 444),
])

def test_cip68_token_label_validation(token_class, valid_token, expected_label):
    # Test valid labels
    token = token_class(valid_token)
    assert token.label == expected_label
    # Test invalid label
    invalid_token = "000000004d794e4654"
    with pytest.raises(InvalidCIP68ReferenceNFT):
        token_class(invalid_token)


def test_cip68_string_key_conversion():
    files = CIP68UserNFTFiles(
        mediaType=b"image/png",
        src=b"ipfs://QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco"
    )
    metadata = CIP68UserNFTMetadata(
        name=b"My NFT",
        image=b"https://example.com/image.jpeg",
        description=b"This is a description of my NFT",
        files=[files]   
    )
    datum = CIP68Datum(metadata=metadata, version=1, extra=Unit())
    assert b"name" in datum.metadata
    assert b"image" in datum.metadata
    assert b"description" in datum.metadata
    assert b"files" in datum.metadata
    assert b"mediaType" in datum.metadata[b"files"][0]
    assert b"src" in datum.metadata[b"files"][0]
    assert_roundtrip(datum)


def test_cip68_multiple_files():
    files1 = CIP68UserNFTFiles(
        mediaType=b"image/png",
        src=b"ipfs://QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco"
    )
    files2 = CIP68UserNFTFiles(
        mediaType=b"image/png",
        src=b"ipfs://QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco"
    )
    metadata = CIP68UserNFTMetadata(
        name=b"My NFT",
        image=b"https://example.com/image.jpeg",
        files=[files1, files2]
    )
    datum = CIP68Datum(metadata=metadata, version=1, extra=Unit())
    assert b"mediaType" in datum.metadata[b"files"][0]
    assert b"src" in datum.metadata[b"files"][0]
    assert b"mediaType" in datum.metadata[b"files"][1]
    assert b"src" in datum.metadata[b"files"][1]
    assert_roundtrip(datum)
    restored = datum.from_cbor(datum.to_cbor_hex())
    print(restored)
    print(datum)


def test_cip68_with_extra():
    metadata = CIP68UserNFTMetadata(
        name=b"My NFT",
        image=b"ipfs://Qm..."
    )

    @dataclass
    class CustomData(PlutusData):
        CONSTR_ID = 2
        value: bytes
        count: int

    extra_data = CustomData(value=b"test value", count=42)

    datum_with_extra = CIP68Datum(
        metadata=metadata,
        version=1,
        extra=extra_data
    )
    assert datum_with_extra.extra.value == b"test value"
    assert datum_with_extra.extra.count == 42
    assert datum_with_extra.extra.CONSTR_ID == 2
    assert_roundtrip(datum_with_extra)


@pytest.mark.parametrize("onchain_datum", [
    # ADA Handle
    "d8799fab446e616d65472468616e646c6545696d6167655838697066733a2f2f7a646a3757687465384638454d666a54625541637036356f574c426f5445677934647a64386b4c61784239394a55437847496d65646961547970654a696d6167652f6a706567426f6700496f675f6e756d626572004672617269747946636f6d6d6f6e466c656e677468064a63686172616374657273476c657474657273516e756d657269635f6d6f64696669657273404b68616e646c655f747970654668616e646c654776657273696f6e0101b4527265736f6c7665645f616464726573736573a04862675f696d6167655f5840697066733a2f2f62616679626569676e376e71367971786c64786d61677274766b6779326368737561706d78686e3566616b6d766c6966637a6c6f747a736c6d426971ff497066705f696d6167654046706f7274616c5838697066733a2f2f7a6232726857666d6433416d795646784368626b766a75363241447539714a7047325545514246587341725747677276374864657369676e65725838697066733a2f2f7a623272686377626b6536326e634b326e5239686e704e4a743165564a666d424e536473594e313647455550714843614b47736f6369616c735838697066733a2f2f7a623272685a4d50315457466234366f7842766369314c666b6d3146386f5a4c6369555768736e6a417245784e4d72684c4676656e646f72404764656661756c74004e7374616e646172645f696d6167655838697066733a2f2f7a623272686d6f503932516973576468733736655559734c62483835636673346d6b4a7a596d363965413145505a595753536c6173745f7570646174655f616464726573735839018e41aa027f2351ee8e0279ab05e7d92acaa4a2735650bd51c6564413c67e12eb7cf98da0d2fa795fb7c20060c964f2ceeba0feae4d5c9b2d4c76616c6964617465645f6279581c4da965a049dfd15ed1ee19fba6e2974a0b79fc416dd1796a1f97f5e14a696d6167655f686173685820c102fe43ea1c6919bcffb570c6cc7eaf07cfcdb98fdc32a1e26398cddaf725d9537374616e646172645f696d6167655f686173685820e134411636b3a147dde4763cff01d651aacd1a5a397c11736810020cf95cf3074b7376675f76657273696f6e46332e302e31354c6167726565645f7465726d735768747470733a2f2f68616e646c652e6d652f242f746f75546d6967726174655f7369675f726571756972656400446e7366770045747269616c004a707a5f656e61626c6564014862675f6173736574582eb06e84cae01ef5871a6fe6ac556134e21b4b8eb55b833cd3dac95126001bc28048616e646c652043617264203238ff",
    # NFT
    "d8799fa5446e616d654e5370616365427564202338313034467472616974739f4a4368657374706c6174654442656c744e436f76657265642048656c6d65744a576f6f6c20426f6f747346416e63686f72ff447479706545416c69656e45696d6167655f5840697066733a2f2f6261666b726569626e77647635646f6f706536636d796e36726d6865776e6b6672706e777361376a71353770376f78686f686f6c6664683475423571ff4673686132353658202db0ebd1b9cf2784cc37d161c966a8b17b6d207d30efdff75cee3b96519f94ec01d87980ff",
])

def test_cip68_onchain_datum(onchain_datum):
    datum = CIP68Datum.from_cbor(bytes.fromhex(onchain_datum))
    assert_roundtrip(datum)
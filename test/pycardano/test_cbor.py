"""Tests for the conditional cbor2 import and the CBOR_C_EXTENSION guard rails.

``pycardano.cbor`` reads ``CBOR_C_EXTENSION`` once at import time, so tests that
flip the flag must reload the module (or run a subprocess) for the change to take
effect. A plain ``monkeypatch.setenv`` after import has no effect.
"""

import importlib
import subprocess
import sys
import warnings

import pytest

import pycardano.cbor as pycardano_cbor
from pycardano.exception import PyCardanoException

# A transaction whose body contains tag-258 sets (the structure the C extension
# reorders), so the cross-impl id comparison is meaningful.
# https://cardanoscan.io/transaction/941502b0aa104c850d197923259444d2b57cab7af18b63143775465aaacc84f5
TX_WITH_SETS_CBOR = (
    "84a700d90102868258202f980a7d47a6195c975c266335211afd3b9cabb5db5165e6e6d9cb18418415ab00"
    "8258202f980a7d47a6195c975c266335211afd3b9cabb5db5165e6e6d9cb18418415ab01"
    "8258202f980a7d47a6195c975c266335211afd3b9cabb5db5165e6e6d9cb18418415ab02"
    "8258202f980a7d47a6195c975c266335211afd3b9cabb5db5165e6e6d9cb18418415ab03"
    "82582040aba0069d0dce7f801a9d16c26d469ec8ce16e1eb68379ae2774e5d28f33d5b00"
    "8258206ba686304126196267200c6502df4b42af898ad2fb1621561fdb0a457fd8b68b00"
    "0dd90102818258202f980a7d47a6195c975c266335211afd3b9cabb5db5165e6e6d9cb18418415ab04"
    "0181825839013c55ef61a7fac4c7f94dc65052586f31dd659acddffc69f13d2c4364646c9e5f7484e8aeceba94566b73b8b50394eb6bfb54f67ac5885d591ab25dc1bf"
    "021a0004ee04031a08d0f5dc0b58204a080e29d89a598d6a3c000c9f15f4ab74a10ffdaa320f256fc7f69b75ff8a59"
    "14d9010281841b000000174876e800581de1646c9e5f7484e8aeceba94566b73b8b50394eb6bfb54f67ac5885d598400825820b2a591ac219ce6dcca5847e0248015209c7cb0436aa6bd6863d0c1f152a60bc500a10bd81e82010a581cfa24fb305126805cf2164c161d852a0e7330cf988f1fe558cf7d4a64827835697066733a2f2f516d634b51676763706f757568414176555947447a6f4b674d77625a536b57716945654536633637534a336b457158209b2438f0032a0c24ed62d12d6bdb79b47e2bd0c4d2dd4f4936c055ead7109caf"
    "a300d90102818258205d58313597871a1823742d172d738fcd1fee4800ba41859db790f981d4dae74e584089b07924734e5b9d813b43638c3e2e6f4ac1e473e454d2d5b404b7bee939d8b5046b6a5c4ba0b51096d5538feb933e802a5944442b046ef11b2381ffce70f70e0"
    "7d90102815908545908510101003232323232323232323232323232323232323232323232323232323232323232323232323232323232259323255333573466e1d20000011180098111bab357426ae88d55cf00104554ccd5cd19b87480100044600422c6aae74004dd51aba1357446ae88d55cf1baa3255333573466e1d200a35573a002226ae84d5d11aab9e00111637546ae84d5d11aba235573c6ea800642b26006003149a2c8a4c301f801c0052000c00e0070018016006901e4070c00e003000c00d20d00fc000c0003003800a4005801c00e003002c00d20c09a0c80e1801c006001801a4101b5881380018000600700148013003801c006005801a410100078001801c006001801a4101001f8001800060070014801b0038018096007001800600690404002600060001801c0052008c00e006025801c006001801a41209d8001800060070014802b003801c006005801a410112f501c3003800c00300348202b7881300030000c00e00290066007003800c00b003482032ad7b806038403060070014803b00380180960003003800a4021801c00e003002c00d20f40380e1801c006001801a41403f800100a0c00e0029009600f0030078040c00e002900a600f003800c00b003301a483403e01a600700180060066034904801e00060001801c0052016c01e00600f801c006001801980c2402900e30000c00e002901060070030128060c00e00290116007003800c00b003483c0ba03860070018006006906432e00040283003800a40498003003800a404d802c00e00f003800c00b003301a480cb0003003800c003003301a4802b00030001801c01e0070018016006603490605c0160006007001800600660349048276000600030000c00e0029014600b003801c00c04b003800c00300348203a2489b00030001801c00e006025801c006001801a4101b11dc2df80018000c0003003800a4055802c00e007003012c00e003000c00d2080b8b872c000c0006007003801809600700180060069040607e4155016000600030000c00e00290166007003012c00e003000c00d2080c001c000c0003003800a405d801c00e003002c00d20c80180e1801c006001801a412007800100a0c00e00290186007003013c0006007001480cb005801801e006003801800e00600500403003800a4069802c00c00f003001c00c007003803c00e003002c00c05300333023480692028c0004014c00c00b003003c00c00f003003c00e00f003800c00b00301480590052008003003800a406d801c00e003002c00d2000c00d2006c00060070018006006900a600060001801c0052038c00e007001801600690006006901260003003800c003003483281300020141801c005203ac00e006027801c006001801a403d800180006007001480f3003801804e00700180060069040404af3c4e302600060001801c005203ec00e006013801c006001801a4101416f0fd20b80018000600700148103003801c006005801a403501c3003800c0030034812b00030000c00e0029021600f003800c00a01ac00e003000c00ccc08d20d00f4800b00030000c0000000000803c00c016008401e006009801c006001801807e0060298000c000401e006007801c0060018018074020c000400e00f003800c00b003010c000802180020070018006006019801805e0003000400600580180760060138000800c00b00330134805200c400e00300080330004006005801a4001801a410112f58000801c00600901260008019806a40118002007001800600690404a75ee01e00060008018046000801801e000300c4832004c025201430094800a0030028052003002c00d2002c000300648010c0092002300748028c0312000300b48018c0292012300948008c0212066801a40018000c0192008300a2233335573e00250002801994004d55ce800cd55cf0008d5d08014c00cd5d10011263009222532900389800a4d2219002912c80344c01526910c80148964cc04cdd68010034564cc03801400626601800e0071801226601800e01518010096400a3000910c008600444002600244004a664600200244246466004460044460040064600444600200646a660080080066a00600224446600644b20051800484ccc02600244666ae68cdc3801000c00200500a91199ab9a33710004003000801488ccd5cd19b89002001800400a44666ae68cdc4801000c00a00122333573466e20008006005000912a999ab9a3371200400222002220052255333573466e2400800444008440040026eb400a42660080026eb000a4264666015001229002914801c8954ccd5cd19b8700400211333573466e1c00c006001002118011229002914801c88cc044cdc100200099b82002003245200522900391199ab9a3371066e08010004cdc1001001c002004403245200522900391199ab9a3371266e08010004cdc1001001c00a00048a400a45200722333573466e20cdc100200099b820020038014000912c99807001000c40062004912c99807001000c400a2002001199919ab9a357466ae880048cc028dd69aba1003375a6ae84008d5d1000934000dd60010a40064666ae68d5d1800c0020052225933006003357420031330050023574400318010600a444aa666ae68cdc3a400000222c22aa666ae68cdc4000a4000226600666e05200000233702900000088994004cdc2001800ccdc20010008cc010008004c01088954ccd5cd19b87480000044400844cc00c004cdc300100091119803112c800c60012219002911919806912c800c4c02401a442b26600a004019130040018c008002590028c804c8888888800d1900991111111002a244b267201722222222008001000c600518000001112a999ab9a3370e004002230001155333573466e240080044600823002229002914801c88ccd5cd19b893370400800266e0800800e00100208c8c0040048c0088cc00800800505a"
    "182050082a0821a0007c6d41a06a71df2f5f6"
)


@pytest.fixture
def reset_cbor_module():
    """Reload ``pycardano.cbor`` back to its default (cbor2pure) state on teardown."""
    yield
    importlib.reload(pycardano_cbor)


def _reload_cbor(monkeypatch, *, c_extension, selftest=None):
    """Reload ``pycardano.cbor`` with the given environment configuration."""
    monkeypatch.setenv("CBOR_C_EXTENSION", "1" if c_extension else "0")
    if selftest is None:
        monkeypatch.delenv("PYCARDANO_CBOR_SELFTEST", raising=False)
    else:
        monkeypatch.setenv("PYCARDANO_CBOR_SELFTEST", selftest)
    return importlib.reload(pycardano_cbor)


def test_warning_emitted_when_flag_set(monkeypatch, reset_cbor_module):
    """Test 1: a RuntimeWarning fires when the C extension is requested."""
    pytest.importorskip("cbor2", reason="C cbor2 extension not installed")
    with pytest.warns(RuntimeWarning, match="CBOR_C_EXTENSION"):
        # Disable the self-test so the warning is asserted in isolation.
        _reload_cbor(monkeypatch, c_extension=True, selftest="0")


def test_no_warning_by_default(monkeypatch, reset_cbor_module):
    """Test 2: no RuntimeWarning when the flag is unset (the default)."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        module = _reload_cbor(monkeypatch, c_extension=False)
    assert module.cbor2.__name__ == "cbor2pure"
    assert not [w for w in caught if issubclass(w.category, RuntimeWarning)]


def test_logger_also_emits(monkeypatch, caplog, reset_cbor_module):
    """Test 3: the package logger also emits the warning text."""
    pytest.importorskip("cbor2", reason="C cbor2 extension not installed")
    with caplog.at_level("WARNING", logger="PyCardano"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _reload_cbor(monkeypatch, c_extension=True, selftest="0")
    assert any("CBOR_C_EXTENSION" in record.message for record in caplog.records)


def _is_byte_stable(backend):
    """Independently round-trip the golden bytes with the 258 decoder removed."""
    semantic_decoders = backend._decoder.semantic_decoders
    original = semantic_decoders.pop(258, None)
    try:
        reencoded = backend.dumps(backend.loads(pycardano_cbor._SELFTEST_GOLDEN))
    finally:
        if original is not None:
            semantic_decoders[258] = original
    return reencoded == pycardano_cbor._SELFTEST_GOLDEN


def test_selftest_passes_for_pure_python():
    """Test 4a: cbor2pure is byte-stable, so the self-test is a no-op."""
    import cbor2pure

    assert _is_byte_stable(cbor2pure)
    # Must not raise.
    pycardano_cbor._run_cbor_selftest(cbor2pure)


def test_selftest_contract_for_c_extension():
    """Test 4b: the self-test raises iff the active backend is not byte-stable."""
    cbor2 = pytest.importorskip("cbor2", reason="C cbor2 extension not installed")
    if _is_byte_stable(cbor2):
        pycardano_cbor._run_cbor_selftest(cbor2)  # passes for an order-stable build
    else:
        with pytest.raises(PyCardanoException, match="round-trip self-test"):
            pycardano_cbor._run_cbor_selftest(cbor2)


def test_selftest_disabled_does_not_raise(monkeypatch, reset_cbor_module):
    """The self-test can be opted out of with PYCARDANO_CBOR_SELFTEST=0."""
    pytest.importorskip("cbor2", reason="C cbor2 extension not installed")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        module = _reload_cbor(monkeypatch, c_extension=True, selftest="0")
    assert module.cbor2.__name__ == "cbor2"


def _tx_id_in_subprocess(c_extension):
    """Compute TX_WITH_SETS_ID in a fresh process with the given backend."""
    script = (
        "from pycardano import Transaction;"
        f"print(Transaction.from_cbor('{TX_WITH_SETS_CBOR}').id)"
    )
    env = {"CBOR_C_EXTENSION": "1" if c_extension else "0"}
    # The self-test would abort import on an order-unstable C build; disable it
    # here so we can observe the (wrong) id the backend would actually produce.
    if c_extension:
        env["PYCARDANO_CBOR_SELFTEST"] = "0"
    import os

    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env={**os.environ, **env},
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip().splitlines()[-1]


def test_cross_impl_tx_id_stability():
    """Test 5: the headline cross-impl tx-id stability check (audit §10.9 #1).

    The pure-Python backend is deterministic. When the C extension is available,
    the two backends agree iff the C build is byte-stable -- which is exactly the
    condition the import-time self-test guards.
    """
    pure_id = _tx_id_in_subprocess(c_extension=False)
    assert pure_id == _tx_id_in_subprocess(c_extension=False)

    cbor2 = pytest.importorskip("cbor2", reason="C cbor2 extension not installed")
    c_id = _tx_id_in_subprocess(c_extension=True)
    assert (c_id == pure_id) == _is_byte_stable(cbor2)

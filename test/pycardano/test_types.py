import typeguard

from pycardano.types import check_type, typechecked


def test_types(monkeypatch):
    monkeypatch.setenv("PYCARDANO_NO_TYPE_CHECK", "true")

    assert typeguard.typechecked != typechecked
    assert typeguard.check_type != check_type

    @typechecked
    def func1():
        pass

    @typechecked()
    def func2():
        pass

    check_type()

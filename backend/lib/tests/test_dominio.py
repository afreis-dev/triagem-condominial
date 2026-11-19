import pytest

from lib.dominio import inteiro, texto


@pytest.mark.parametrize(
    "valor, esperado",
    [
        ("  oi  ", "oi"),
        ("", None),
        ("   ", None),
        (None, None),
        (5, "5"),
        (True, None),
        (1.5, None),
        ([], None),
        ("a\x00b", "ab"),
        ("\x00", None),
        ("x\ud800", "x?"),
        pytest.param(10**5000, None, id="inteiro_gigante"),
    ],
)
def test_texto(valor, esperado):
    assert texto(valor) == esperado


@pytest.mark.parametrize(
    "valor, esperado",
    [
        (1, 1),
        ("42", 42),
        (" 42 ", 42),
        (2**31 - 1, 2**31 - 1),
        (0, None),
        ("0", None),
        (-1, None),
        ("-1", None),
        (2**31, None),
        ("9" * 11, None),
        ("9" * 5000, None),
        ("abc", None),
        ("4.5", None),
        (4.0, None),
        (True, None),
        (None, None),
    ],
)
def test_inteiro(valor, esperado):
    assert inteiro(valor) == esperado

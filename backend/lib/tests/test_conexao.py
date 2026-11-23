import pytest

import lib.conexao as modulo


def test_exige_a_database_url(monkeypatch):
    monkeypatch.setattr(modulo, "load_dotenv", lambda: None)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        modulo.conectar()

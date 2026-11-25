import pytest

import lib.conexao as modulo


def test_exige_database_url_do_ambiente(monkeypatch):
    def sem_url():
        raise RuntimeError("DATABASE_URL_DEV não configurada")

    monkeypatch.setattr(modulo, "obter_database_url", sem_url)

    with pytest.raises(RuntimeError, match="DATABASE_URL_DEV"):
        modulo.conectar()

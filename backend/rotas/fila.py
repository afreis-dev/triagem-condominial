import logging

import psycopg2
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from lib.listar_fila import listar_fila
from lib.auth_deps import sindico_autenticado

router = APIRouter()
registro = logging.getLogger(__name__)


@router.get("/ocorrencias")
def rota_listar_fila(sindico=Depends(sindico_autenticado)):
    """Devolve a fila lida do banco a cada chamada; se o banco falhar, responde 503 sem expor o erro."""
    try:
        return listar_fila(sindico["id"])
    except (psycopg2.Error, RuntimeError):
        registro.exception("falha ao buscar a fila")
        return JSONResponse(
            status_code=503,
            content={"ok": False, "erros": {"banco": "Não foi possível buscar a fila agora. Tente de novo."}},
        )
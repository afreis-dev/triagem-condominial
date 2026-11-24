from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..lib.concluir_ocorrencia import concluir_ocorrencia

router = APIRouter(prefix="/api/ocorrencias")


@router.patch("/{ocorrencia_id}/concluir")
def concluir(ocorrencia_id: str):
    resultado = concluir_ocorrencia(ocorrencia_id)
    if resultado["ok"]:
        return resultado

    status = 404 if "ocorrenciaId" in resultado["erros"] else 409
    return JSONResponse(status_code=status, content=resultado)

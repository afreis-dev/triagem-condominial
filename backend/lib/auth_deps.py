from contextlib import closing

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth import validar_token
from .conexao import conectar

seguranca = HTTPBearer(auto_error=False)

def sindico_autenticado(
    credenciais: HTTPAuthorizationCredentials | None = Depends(seguranca),
):
    if credenciais is None:
        raise HTTPException(status_code=401, detail="Autenticação necessária")

    sindico_id = validar_token(credenciais.credentials)

    with closing(conectar()) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT id, email FROM sindicos WHERE id = %s",
                (sindico_id,),
            )
            sindico = cursor.fetchone()

    if sindico is None:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    return {
        "id": str(sindico[0]),
        "email": sindico[1],
    }
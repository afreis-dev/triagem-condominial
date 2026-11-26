
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
                "SELECT id, nome, email FROM sindicos WHERE id = %s",
                (sindico_id,),
            )
            sindico = cursor.fetchone()

    if sindico is None:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    return {
        "id": sindico[0],
        "nome": sindico[1],
        "email": sindico[2],
    }


def verificar_acesso_ocorrencia(cursor, ocorrencia_id: int, sindico_id: int):
    """Confirma que a ocorrência pertence à carteira do síndico."""
    cursor.execute(
        """
        SELECT o.id
        FROM ocorrencias o
        JOIN condominios c ON c.id = o.condominio_id
        WHERE o.id = %s AND c.sindico_id = %s
        """,
        (ocorrencia_id, sindico_id),
    )

    if cursor.fetchone() is None:
        raise HTTPException(
            status_code=404,
            detail="Ocorrência não encontrada",
        )

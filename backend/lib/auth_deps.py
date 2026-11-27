
from contextlib import closing

import hmac

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from .auth import token_csrf, validar_token
from .conexao import conectar

COOKIE_SESSAO = "triagem_sessao"
csrf_header = APIKeyHeader(
    name="X-CSRF-Token",
    scheme_name="CSRF",
    description="Após o login, copie csrfToken de GET /auth/me para autorizar alterações.",
    auto_error=False,
)


def sindico_autenticado(
    request: Request,
):
    token = request.cookies.get(COOKIE_SESSAO)
    if not token:
        raise HTTPException(status_code=401, detail="Autenticação necessária")

    sindico_id = validar_token(token)
    request.state.csrf_token = token_csrf(token)

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


def sindico_com_csrf(
    request: Request,
    recebido: str | None = Security(csrf_header),
    sindico=Depends(sindico_autenticado),
):
    recebido = recebido or ""
    if not hmac.compare_digest(recebido, request.state.csrf_token):
        raise HTTPException(status_code=403, detail="Verificação de segurança inválida")
    return sindico


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

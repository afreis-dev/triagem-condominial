"""Seed idempotente da Sprint 1.

Uso:
    python scripts/db_seed.py              # dados fixos oficiais do PO
    python scripts/db_seed.py --demo       # inclui cenários demonstrativos
    python scripts/db_seed.py --check      # verifica presença dos dados fixos

Não modifica bancos de teste, remotos nem ambientes não-dev.
"""

import argparse
import json
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "database" / "dados_fixos_sprint1.json"
REVISION = "dc53387e1802"

# Frases provenientes da aba "Frases de teste" do PO.
# A distribuição entre condomínios e status é ilustrativa para a demonstração.
DEMOS = (
    ("aurora", "lâmpada do hall queimada", "normal", "manutencao", "zelador", "manutenção simples de área comum", None, "nova"),
    ("vista-verde", "estamos sem água no bloco A desde cedo", "alta", "manutencao", "zelador", "falta de água afeta muitos moradores", None, "em_andamento"),
    ("palmeiras", "tem cheiro de gás no bloco B", "urgente", "manutencao", "sindico", "palavra de risco: cheiro de gás", "cheiro de gás", "nova"),
    ("aurora", "preciso da segunda via do boleto", "baixa", "pedido_administrativo", "sindico", "pedido administrativo sem prazo curto", None, "concluida"),
    ("vista-verde", "o portão da garagem travou aberto", "alta", "seguranca_acesso", "portaria", "deixa o acesso ao prédio aberto", None, "em_andamento"),
)
DEMO_NAME = "Demonstração Sprint 1"


def conexao_segura():
    load_dotenv(ROOT / ".env")
    raw_url = os.getenv("DATABASE_URL")
    if not raw_url:
        raise RuntimeError("DATABASE_URL não encontrada no .env")
    url = make_url(raw_url)
    if url.host not in {"127.0.0.1", "localhost"} or not url.database or not url.database.endswith("_dev"):
        raise RuntimeError("Seed permitido apenas em PostgreSQL local e banco com sufixo _dev")
    return psycopg2.connect(raw_url, connect_timeout=5), url.database


def exigir_migration(cur):
    cur.execute("SELECT to_regclass('public.alembic_version')")
    if cur.fetchone()[0] is None:
        raise RuntimeError("Migration ausente. Execute: task db-migrate")
    cur.execute("SELECT version_num FROM public.alembic_version")
    rows = [r[0] for r in cur.fetchall()]
    if REVISION not in rows:
        raise RuntimeError(f"Migration {REVISION} não aplicada. Execute: task db-migrate")


def buscar_id(cur, tabela, campo, valor):
    # Tabela/coluna são constantes do código, nunca texto do usuário.
    cur.execute(f"SELECT id FROM {tabela} WHERE {campo} = %s ORDER BY id LIMIT 1", (valor,))
    row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"Registro não encontrado: {tabela}.{campo}={valor}")
    return row[0]


def carregar_referencias(cur, dados):
    for s in dados["sindicos"]:
        cur.execute("SELECT id FROM sindicos WHERE email = %s ORDER BY id LIMIT 1", (s["email"],))
        row = cur.fetchone()
        if row is None:
            cur.execute("INSERT INTO sindicos (nome, celular, email) VALUES (%s,%s,%s) RETURNING id", (s["nome"],s["celular"],s["email"]))
            sindico_id = cur.fetchone()[0]
        else:
            sindico_id = row[0]

    for c in dados["condominios"]:
        cur.execute("""INSERT INTO condominios (identificador,nome,bairro,sindico_id)
                       VALUES (%s,%s,%s,%s)
                       ON CONFLICT (identificador) DO NOTHING""",
                    (c["identificador"],c["nome"],c["bairro"],sindico_id))
        # Se a linha já existe, apenas preenche o vínculo ausente — não sobrescreve dados editados.
        cur.execute("""UPDATE condominios SET sindico_id = %s
                       WHERE identificador = %s AND sindico_id IS NULL""",(sindico_id,c["identificador"]))

    for r in dados["responsaveis"]:
        condo_id = buscar_id(cur,"condominios","identificador",r["condominio"])
        cur.execute("""INSERT INTO responsaveis (condominio_id,papel,nome,celular)
                       VALUES (%s,%s,%s,%s)
                       ON CONFLICT (condominio_id,papel) DO NOTHING""",
                    (condo_id,r["papel"],r["nome"],r["celular"]))

    for ordem, p in enumerate(dados["palavras_risco"],start=1):
        cur.execute("""INSERT INTO palavras_risco
                       (palavra,categoria,prioridade,responsavel_sugerido,motivo,ordem)
                       VALUES (%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (palavra) DO NOTHING""",
                    (p["palavra"],p["categoria"],p["prioridade"],p["responsavel_sugerido"],p["motivo"],ordem))


def carregar_demonstracao(cur):
    for slug, descricao, prioridade, categoria, responsavel, motivo, palavra_risco, status in DEMOS:
        condo_id = buscar_id(cur,"condominios","identificador",slug)
        cur.execute("""SELECT id FROM ocorrencias WHERE condominio_id=%s AND nome=%s AND descricao=%s
                       ORDER BY id LIMIT 1""",(condo_id,DEMO_NAME,descricao))
        if cur.fetchone():
            continue
        cur.execute("SELECT nextval(pg_get_serial_sequence('ocorrencias','id'))")
        ocorrencia_id = cur.fetchone()[0]
        protocolo = f"TS-{ocorrencia_id:06d}"
        cur.execute("""INSERT INTO ocorrencias
                       (id,protocolo,condominio_id,origem,nome,descricao,status,prioridade,categoria,
                        responsavel_sugerido,motivo,travada,palavra_de_risco,fonte,concluida_em)
                       VALUES (%s,%s,%s,'whatsapp_sindico',%s,%s,%s,%s,%s,%s,%s,%s,%s,'regras',
                               CASE WHEN %s='concluida' THEN now() ELSE NULL END)""",
                    (ocorrencia_id,protocolo,condo_id,DEMO_NAME,descricao,status,prioridade,categoria,
                     responsavel,motivo,bool(palavra_risco),palavra_risco,status))
        cur.execute("""INSERT INTO registros_decisao
                       (ocorrencia_id,tipo,quem_decidiu,origem,prioridade_sugerida)
                       VALUES (%s,'entrada','sistema','whatsapp_sindico',%s)""",(ocorrencia_id,prioridade))
        if status in ("em_andamento","concluida"):
            cur.execute("""INSERT INTO registros_decisao
                           (ocorrencia_id,tipo,quem_decidiu,prioridade_sugerida,prioridade_final)
                           VALUES (%s,'prioridade_confirmada','sindico',%s,%s)""",(ocorrencia_id,prioridade,prioridade))
            cur.execute("""INSERT INTO registros_decisao
                           (ocorrencia_id,tipo,quem_decidiu,acao,responsavel,nota)
                           VALUES (%s,'acao','sindico','delegar',%s,'Exemplo fictício para demonstração')""",(ocorrencia_id,responsavel))
        if status == "concluida":
            cur.execute("""INSERT INTO registros_decisao (ocorrencia_id,tipo,quem_decidiu)
                           VALUES (%s,'conclusao','sindico')""",(ocorrencia_id,))


def resumo(cur):
    counts={}
    for table in ("sindicos","condominios","responsaveis","palavras_risco","ocorrencias","registros_decisao"):
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table]=cur.fetchone()[0]
    return counts


def main():
    parser=argparse.ArgumentParser(description="Carga idempotente do PO para ambiente dev")
    parser.add_argument("--demo",action="store_true",help="Adiciona exemplos ilustrativos de ocorrências e histórico")
    parser.add_argument("--check",action="store_true",help="Consulta contagens sem modificar dados")
    args=parser.parse_args()
    dados=json.loads(DATA_FILE.read_text(encoding="utf-8"))
    assert (len(dados["sindicos"]),len(dados["condominios"]),len(dados["responsaveis"]),len(dados["palavras_risco"])) == (1,3,6,12)
    conn,banco=conexao_segura()
    try:
        with conn:
            with conn.cursor() as cur:
                exigir_migration(cur)
                if not args.check:
                    # Evita que duas execuções simultâneas dupliquem registros não únicos.
                    cur.execute("SELECT pg_advisory_xact_lock(7321, 2026)")
                    carregar_referencias(cur,dados)
                    if args.demo:
                        carregar_demonstracao(cur)
                counts=resumo(cur)
        print(f"Banco: {banco}")
        print("Registros totais:", ", ".join(f"{k}={v}" for k,v in counts.items()))
        if args.check:
            assert all(counts[t] >= n for t,n in (("sindicos",1),("condominios",3),("responsaveis",6),("palavras_risco",12))),"Carga de referência incompleta"
            print("Verificação aprovada")
        else:
            print("Seed concluído. Repetir o comando não duplica os registros do seed.")
    finally:
        conn.close()


if __name__=="__main__":
    try:
        main()
    except (Exception,) as e:
        raise SystemExit(f"Falha no seed: {e}") from e

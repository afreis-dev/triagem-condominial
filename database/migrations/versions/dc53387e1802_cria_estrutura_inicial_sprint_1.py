"""cria estrutura inicial sprint 1

Revision ID: dc53387e1802
Revises:
Create Date: 2026-11-20 14:39:10.689816
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "dc53387e1802"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRIORIDADES = "'urgente', 'alta', 'normal', 'baixa'"
ORIGENS = "'morador', 'proprietario', 'funcionario', 'whatsapp_sindico'"
RESPONSAVEIS = "'zelador', 'portaria', 'sindico'"
CATEGORIAS = (
    "'manutencao', 'seguranca_acesso', 'convivencia', "
    "'pedido_administrativo', 'duvida', 'nao_reconhecida'"
)


def upgrade() -> None:
    op.create_table(
        "sindicos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("celular", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
    )

    op.create_table(
        "condominios",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("identificador", sa.Text(), nullable=False, unique=True),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("bairro", sa.Text(), nullable=True),
        # Excecao temporaria da Sprint 1: fixtures atuais nao informam sindico_id.
        # Revisar a obrigatoriedade na SQU-76, apos a demonstracao.
        sa.Column("sindico_id", sa.Integer(), sa.ForeignKey("sindicos.id", ondelete="RESTRICT"), nullable=True),
    )

    op.create_table(
        "responsaveis",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("condominio_id", sa.Integer(), sa.ForeignKey("condominios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("papel", sa.Text(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("celular", sa.Text(), nullable=True),
        sa.UniqueConstraint("condominio_id", "papel", name="uq_responsaveis_condominio_papel"),
        sa.CheckConstraint("papel IN ('zelador', 'portaria')", name="ck_responsaveis_papel"),
    )

    op.create_table(
        "palavras_risco",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("palavra", sa.Text(), nullable=False, unique=True),
        sa.Column("categoria", sa.Text(), nullable=False),
        sa.Column("prioridade", sa.Text(), nullable=False, server_default="urgente"),
        sa.Column("responsavel_sugerido", sa.Text(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False, unique=True),
        sa.CheckConstraint(f"categoria IN ({CATEGORIAS})", name="ck_palavras_risco_categoria"),
        sa.CheckConstraint("prioridade = 'urgente'", name="ck_palavras_risco_prioridade"),
        sa.CheckConstraint(f"responsavel_sugerido IN ({RESPONSAVEIS})", name="ck_palavras_risco_responsavel"),
        sa.CheckConstraint("ordem > 0", name="ck_palavras_risco_ordem"),
    )

    op.create_table(
        "ocorrencias",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("protocolo", sa.Text(), nullable=False, unique=True),
        sa.Column("condominio_id", sa.Integer(), sa.ForeignKey("condominios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("origem", sa.Text(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=True),
        sa.Column("apartamento", sa.Text(), nullable=True),
        sa.Column("celular", sa.Text(), nullable=True),
        sa.Column("local", sa.Text(), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="nova"),
        sa.Column("prioridade", sa.Text(), nullable=True),
        sa.Column("categoria", sa.Text(), nullable=True),
        sa.Column("responsavel_sugerido", sa.Text(), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("travada", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("palavra_de_risco", sa.Text(), nullable=True),
        sa.Column("fonte", sa.Text(), nullable=True),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("concluida_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"origem IN ({ORIGENS})", name="ck_ocorrencias_origem"),
        sa.CheckConstraint("status IN ('nova', 'em_andamento', 'concluida')", name="ck_ocorrencias_status"),
        sa.CheckConstraint(f"prioridade IN ({PRIORIDADES})", name="ck_ocorrencias_prioridade"),
        sa.CheckConstraint(f"categoria IN ({CATEGORIAS})", name="ck_ocorrencias_categoria"),
        sa.CheckConstraint(f"responsavel_sugerido IN ({RESPONSAVEIS})", name="ck_ocorrencias_responsavel"),
        sa.CheckConstraint("fonte IN ('regras', 'ia')", name="ck_ocorrencias_fonte"),
        sa.CheckConstraint("char_length(descricao) BETWEEN 1 AND 2000", name="ck_ocorrencias_descricao"),
        sa.CheckConstraint("concluida_em IS NULL OR status = 'concluida'", name="ck_ocorrencias_conclusao"),
    )
    op.create_index("ix_ocorrencias_condominio_status_criada", "ocorrencias", ["condominio_id", "status", "criada_em"])
    op.create_index("ix_ocorrencias_condominio_concluida", "ocorrencias", ["condominio_id", "concluida_em"])

    op.create_table(
        "registros_decisao",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ocorrencia_id", sa.Integer(), sa.ForeignKey("ocorrencias.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tipo", sa.Text(), nullable=False),
        sa.Column("quem_decidiu", sa.Text(), nullable=False),
        sa.Column("origem", sa.Text(), nullable=True),
        sa.Column("prioridade_sugerida", sa.Text(), nullable=True),
        sa.Column("prioridade_final", sa.Text(), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("acao", sa.Text(), nullable=True),
        sa.Column("responsavel", sa.Text(), nullable=True),
        sa.Column("data_agendada", sa.Date(), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("rebaixou_travada", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("data_hora", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("tipo IN ('entrada', 'prioridade_confirmada', 'prioridade_alterada', 'acao', 'conclusao', 'aprovacao_lote')", name="ck_registros_tipo"),
        sa.CheckConstraint("quem_decidiu IN ('sistema', 'sindico')", name="ck_registros_quem"),
        sa.CheckConstraint(f"origem IN ({ORIGENS})", name="ck_registros_origem"),
        sa.CheckConstraint(f"prioridade_sugerida IN ({PRIORIDADES})", name="ck_registros_prioridade_sugerida"),
        sa.CheckConstraint(f"prioridade_final IN ({PRIORIDADES})", name="ck_registros_prioridade_final"),
        sa.CheckConstraint("acao IN ('delegar', 'agendar', 'eu_mesmo')", name="ck_registros_acao"),
        sa.CheckConstraint(f"responsavel IN ({RESPONSAVEIS})", name="ck_registros_responsavel"),
    )
    op.create_index("ix_registros_ocorrencia_data", "registros_decisao", ["ocorrencia_id", "data_hora", "id"])

    # SQU-64/H14: mesma regra de imutabilidade existente no schema de testes.
    op.execute("""
        CREATE FUNCTION recusar_alteracao_registro() RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Registros de decisão não podem ser alterados ou apagados';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER registros_decisao_imutavel
            BEFORE UPDATE OR DELETE ON registros_decisao
            FOR EACH ROW EXECUTE FUNCTION recusar_alteracao_registro();
    """)


def downgrade() -> None:
    # Apenas para banco local descartavel: removendo as tabelas, todos os dados sao perdidos.
    op.execute("DROP TRIGGER registros_decisao_imutavel ON registros_decisao")
    op.execute("DROP FUNCTION recusar_alteracao_registro()")
    op.drop_index("ix_registros_ocorrencia_data", table_name="registros_decisao")
    op.drop_table("registros_decisao")
    op.drop_index("ix_ocorrencias_condominio_concluida", table_name="ocorrencias")
    op.drop_index("ix_ocorrencias_condominio_status_criada", table_name="ocorrencias")
    op.drop_table("ocorrencias")
    op.drop_table("palavras_risco")
    op.drop_table("responsaveis")
    op.drop_table("condominios")
    op.drop_table("sindicos")

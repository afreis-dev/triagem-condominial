"""adiciona desfazer_aprovacao_lote na ck_registros_tipo

Revision ID: a1b2c3d4e5f6
Revises: cc7a8380c9d9
Create Date: 2026-11-26
"""
from alembic import op

revision = 'a1b2c3d4e5f6'
down_revision = 'cc7a8380c9d9'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("ALTER TABLE registros_decisao DROP CONSTRAINT ck_registros_tipo")
    op.execute(
        "ALTER TABLE registros_decisao ADD CONSTRAINT ck_registros_tipo "
        "CHECK (tipo IN ('entrada', 'prioridade_confirmada', 'prioridade_alterada', 'acao', 'conclusao', 'aprovacao_lote', 'desfazer_aprovacao_lote'))"
    )

def downgrade():
    op.execute("ALTER TABLE registros_decisao DROP CONSTRAINT ck_registros_tipo")
    op.execute(
        "ALTER TABLE registros_decisao ADD CONSTRAINT ck_registros_tipo "
        "CHECK (tipo IN ('entrada', 'prioridade_confirmada', 'prioridade_alterada', 'acao', 'conclusao', 'aprovacao_lote'))"
    )
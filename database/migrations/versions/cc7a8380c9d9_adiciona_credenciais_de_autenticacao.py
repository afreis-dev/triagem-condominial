"""adiciona credenciais de autenticacao

Revision ID: cc7a8380c9d9
Revises: dc53387e1802
Create Date: 2026-11-21 18:26:26.440619

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc7a8380c9d9'
down_revision: Union[str, Sequence[str], None] = 'dc53387e1802'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sindicos",
        sa.Column("senha_hash", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sindicos", "senha_hash")

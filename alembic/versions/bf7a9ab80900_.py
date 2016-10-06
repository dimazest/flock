"""empty message

Revision ID: bf7a9ab80900
Revises: cff456e0528a
Create Date: 2016-10-06 13:13:31.438750

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'bf7a9ab80900'
down_revision = 'cff456e0528a'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'tweet', 'id',
        type_=sa.BigInteger,
    )


def downgrade():
    op.alter_column(
        'tweet', 'id',
        type_=sa.Integer,
    )

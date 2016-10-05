"""create tweet table

Revision ID: cff456e0528a
Revises:
Create Date: 2016-10-04 18:08:50.929555

"""
from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'cff456e0528a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'tweet',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tweet', postgresql.JSONB, nullable=False),
    )


def downgrade():
    op.drop_table('tweet')

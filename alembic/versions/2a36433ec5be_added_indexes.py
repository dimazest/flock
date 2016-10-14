"""Added indexes.

Revision ID: 2a36433ec5be
Revises:
Create Date: 2016-10-14 13:01:43.260712

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '2a36433ec5be'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('idx_tweet_created_at', 'tweet', ['created_at'], unique=False)


def downgrade():
    op.drop_index('idx_tweet_created_at', table_name='tweet')

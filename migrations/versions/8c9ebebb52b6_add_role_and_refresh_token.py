"""add role and refresh_token

Revision ID: 8c9ebebb52b6
Revises: d24c1fd9c6d7
Create Date: 2026-06-22 22:10:43.863432

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c9ebebb52b6'
down_revision: Union[str, Sequence[str], None] = 'd24c1fd9c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('refresh_token', sa.String(length=255), nullable=True))
    role_enum = sa.Enum('user', 'admin', name='role')
    role_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'users',
        sa.Column('role', role_enum, nullable=False, server_default='user'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'role')
    op.drop_column('users', 'refresh_token')
    sa.Enum(name='role').drop(op.get_bind(), checkfirst=True)

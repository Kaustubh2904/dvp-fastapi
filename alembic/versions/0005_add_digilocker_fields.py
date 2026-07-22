"""add_digilocker_fields_to_employees

Revision ID: 0005
Revises: 319211993900
Create Date: 2026-07-23 02:19:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, None] = '319211993900'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('employees', sa.Column('digilocker_id', sa.String(length=500), nullable=True))
    op.add_column('employees', sa.Column('digilocker_access_token', sa.String(length=1000), nullable=True))
    op.add_column('employees', sa.Column('digilocker_refresh_token', sa.String(length=1000), nullable=True))
    op.add_column('employees', sa.Column('digilocker_token_expiry', sa.DateTime(), nullable=True))
    op.add_column('employees', sa.Column('digilocker_status', sa.String(length=20), nullable=True))
    op.add_column('employees', sa.Column('digilocker_linked_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('employees', 'digilocker_linked_at')
    op.drop_column('employees', 'digilocker_status')
    op.drop_column('employees', 'digilocker_token_expiry')
    op.drop_column('employees', 'digilocker_refresh_token')
    op.drop_column('employees', 'digilocker_access_token')
    op.drop_column('employees', 'digilocker_id')

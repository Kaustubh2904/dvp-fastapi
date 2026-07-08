"""Add HR user role

Revision ID: 0004_add_hr_role
Revises: 0003_subscription_module_upgrade
Create Date: 2026-07-08
"""

from alembic import op


revision = "0004_add_hr_role"
down_revision = "0003_subscription_module_upgrade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'HR';")


def downgrade() -> None:
    # PostgreSQL enum values are not removed in place.
    pass
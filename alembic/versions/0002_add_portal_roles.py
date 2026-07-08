"""Add portal RBAC roles

Revision ID: 0002_add_portal_roles
Revises: 0001_initial_schema
Create Date: 2026-07-08
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_add_portal_roles"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'MARKETING';")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'TECHNICAL_TEAM';")


def downgrade() -> None:
    # PostgreSQL enum values are not removed in place.
    pass
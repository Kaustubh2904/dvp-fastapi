"""initial_migration

Revision ID: 001
Revises:
Create Date: 2026-06-23 02:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE userrole AS ENUM ('SUPERADMIN', 'ADMIN', 'EMPLOYEE')")
    op.execute("CREATE TYPE billingstatus AS ENUM ('ACTIVE', 'EXPIRED', 'PENDING', 'SUSPENDED')")
    op.execute("CREATE TYPE employeestatus AS ENUM ('PENDING_INVITE', 'INVITED', 'REGISTERED', 'ACTIVE', 'INACTIVE', 'SUSPENDED', 'TERMINATED')")
    op.execute("CREATE TYPE documenttype AS ENUM ('AADHAR', 'PAN', 'PASSPORT', 'RESUME', 'DEGREE', 'OTHER')")
    op.execute("CREATE TYPE verificationstatus AS ENUM ('NOT_SUBMITTED', 'PENDING', 'VERIFIED', 'REJECTED')")

    # --- companies ---
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("gst_number", sa.String(length=50), nullable=True),
        sa.Column("subscription_plan", sa.String(length=100), nullable=False, server_default="FREE"),
        sa.Column("subscription_start", sa.DateTime(), nullable=False),
        sa.Column("subscription_end", sa.DateTime(), nullable=False),
        sa.Column("employee_limit", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("current_employee_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("billing_status", postgresql.ENUM("ACTIVE", "EXPIRED", "PENDING", "SUSPENDED", name="billingstatus"), nullable=False, server_default="PENDING"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    # --- roles ---
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", postgresql.ENUM("SUPERADMIN", "ADMIN", "EMPLOYEE", name="userrole"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # --- departments ---
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- employees ---
    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("employee_code", sa.String(length=50), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("gender", sa.String(length=20), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("profile_photo", sa.String(length=500), nullable=True),
        sa.Column("joining_date", sa.Date(), nullable=True),
        sa.Column("registration_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", postgresql.ENUM("PENDING_INVITE", "INVITED", "REGISTERED", "ACTIVE", "INACTIVE", "SUSPENDED", "TERMINATED", name="employeestatus"), nullable=False, server_default="PENDING_INVITE"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- subscriptions ---
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_name", sa.String(length=100), nullable=False, server_default="FREE"),
        sa.Column("employee_limit", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=False),
        sa.Column("billing_status", postgresql.ENUM("ACTIVE", "EXPIRED", "PENDING", "SUSPENDED", name="billingstatus"), nullable=False, server_default="PENDING"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- notifications ---
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.String(length=1000), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- otp_records ---
    op.create_table(
        "otp_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_otp_records_email"), "otp_records", ["email"])

    # --- password_reset_tokens ---
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(op.f("ix_password_reset_tokens_token"), "password_reset_tokens", ["token"], unique=True)

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_type", postgresql.ENUM("AADHAR", "PAN", "PASSPORT", "RESUME", "DEGREE", "OTHER", name="documenttype"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.String(length=500), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("verification_status", postgresql.ENUM("NOT_SUBMITTED", "PENDING", "VERIFIED", "REJECTED", name="verificationstatus"), nullable=False, server_default="PENDING"),
        sa.Column("remarks", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("old_value", postgresql.JSON(), nullable=True),
        sa.Column("new_value", postgresql.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("documents")
    op.drop_table("password_reset_tokens")
    op.drop_index(op.f("ix_password_reset_tokens_token"), table_name="password_reset_tokens")
    op.drop_table("otp_records")
    op.drop_index(op.f("ix_otp_records_email"), table_name="otp_records")
    op.drop_table("notifications")
    op.drop_table("subscriptions")
    op.drop_table("employees")
    op.drop_table("departments")
    op.drop_table("users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("roles")
    op.drop_table("companies")

    op.execute("DROP TYPE IF EXISTS verificationstatus")
    op.execute("DROP TYPE IF EXISTS documenttype")
    op.execute("DROP TYPE IF EXISTS employeestatus")
    op.execute("DROP TYPE IF EXISTS billingstatus")
    op.execute("DROP TYPE IF EXISTS userrole")
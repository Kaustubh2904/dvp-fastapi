"""Expand subscription module

Revision ID: 0003_subscription_module_upgrade
Revises: 0002_add_portal_roles
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_subscription_module_upgrade"
down_revision = "0002_add_portal_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE billingstatus ADD VALUE IF NOT EXISTS 'TRIAL';")
    op.execute("ALTER TYPE billingstatus ADD VALUE IF NOT EXISTS 'PENDING_APPROVAL';")
    op.execute("ALTER TYPE billingstatus ADD VALUE IF NOT EXISTS 'SCHEDULED_CHANGE';")
    op.execute("ALTER TYPE billingstatus ADD VALUE IF NOT EXISTS 'CANCELLED';")

    op.add_column("users", sa.Column("first_name", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=100), nullable=True))

    op.add_column("companies", sa.Column("trial_used", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("companies", sa.Column("last_quota_reset_at", sa.DateTime(), nullable=True))

    op.add_column("subscriptions", sa.Column("scheduled_plan_name", sa.String(length=100), nullable=True))
    op.add_column("subscriptions", sa.Column("scheduled_effective_at", sa.DateTime(), nullable=True))
    op.add_column("subscriptions", sa.Column("trial_used", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("max_admins", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_employees", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("monthly_document_uploads", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("storage_mb", sa.Integer(), nullable=False, server_default="1024"),
        sa.Column("chat_access", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("api_access", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("analytics_access", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ticket_priority", sa.String(length=20), nullable=False, server_default="LOW"),
        sa.Column("white_label_support", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("audit_log_retention_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("billing_cycle_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("trial_days", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_custom", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_subscription_plans_code", "subscription_plans", ["code"], unique=True)

    op.create_table(
        "subscription_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("requested_by_id", sa.Integer(), nullable=False),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("request_type", sa.Enum("UPGRADE", "DOWNGRADE", "RENEWAL", "TRIAL_CONVERSION", name="subscriptionrequesttype"), nullable=False),
        sa.Column("current_plan_code", sa.String(length=50), nullable=True),
        sa.Column("requested_plan_code", sa.String(length=50), nullable=False),
        sa.Column("status", sa.Enum("PENDING_APPROVAL", "APPROVED", "REJECTED", "CANCELLED", name="subscriptionrequeststatus"), nullable=False),
        sa.Column("immediate_effect", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("prorated_value_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("review_notes", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscription_requests_company_id", "subscription_requests", ["company_id"], unique=False)

    op.create_table(
        "subscription_usage",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("month_key", sa.String(length=7), nullable=False),
        sa.Column("employee_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monthly_document_uploads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("storage_used_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_reset_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "month_key", name="uq_subscription_usage_company_month"),
    )
    op.create_index("ix_subscription_usage_month_key", "subscription_usage", ["month_key"], unique=False)

    op.create_table(
        "email_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("template_name", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="smtp"),
        sa.Column("status", sa.Enum("QUEUED", "SENT", "FAILED", "RETRYING", name="emailstatus"), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("queued_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_logs_recipient_email", "email_logs", ["recipient_email"], unique=False)

    conn = op.get_bind()
    conn.execute(sa.text("INSERT INTO subscription_plans (code, name, description, max_admins, max_employees, monthly_document_uploads, storage_mb, chat_access, api_access, analytics_access, ticket_priority, white_label_support, audit_log_retention_days, billing_cycle_days, trial_days, price_cents, is_active, is_custom, created_at, updated_at) VALUES ('FREE', 'Free', 'Trial plan for new companies', 1, 10, 100, 1024, false, false, false, 'LOW', false, 90, 30, 14, 0, true, false, NOW(), NOW()) ON CONFLICT (code) DO NOTHING"))
    conn.execute(sa.text("INSERT INTO subscription_plans (code, name, description, max_admins, max_employees, monthly_document_uploads, storage_mb, chat_access, api_access, analytics_access, ticket_priority, white_label_support, audit_log_retention_days, billing_cycle_days, trial_days, price_cents, is_active, is_custom, created_at, updated_at) VALUES ('BASIC', 'Basic', 'Entry subscription plan', 1, 50, 500, 5120, true, false, false, 'LOW', false, 180, 30, 14, 9900, true, false, NOW(), NOW()) ON CONFLICT (code) DO NOTHING"))
    conn.execute(sa.text("INSERT INTO subscription_plans (code, name, description, max_admins, max_employees, monthly_document_uploads, storage_mb, chat_access, api_access, analytics_access, ticket_priority, white_label_support, audit_log_retention_days, billing_cycle_days, trial_days, price_cents, is_active, is_custom, created_at, updated_at) VALUES ('PRO', 'Pro', 'Advanced subscription plan', 2, 200, 2500, 20480, true, true, true, 'MEDIUM', true, 365, 30, 14, 29900, true, false, NOW(), NOW()) ON CONFLICT (code) DO NOTHING"))
    conn.execute(sa.text("INSERT INTO subscription_plans (code, name, description, max_admins, max_employees, monthly_document_uploads, storage_mb, chat_access, api_access, analytics_access, ticket_priority, white_label_support, audit_log_retention_days, billing_cycle_days, trial_days, price_cents, is_active, is_custom, created_at, updated_at) VALUES ('PREMIUM', 'Premium', 'Premium subscription plan', 5, 1000, 10000, 102400, true, true, true, 'HIGH', true, 730, 30, 14, 99900, true, false, NOW(), NOW()) ON CONFLICT (code) DO NOTHING"))
    conn.execute(sa.text("INSERT INTO subscription_plans (code, name, description, max_admins, max_employees, monthly_document_uploads, storage_mb, chat_access, api_access, analytics_access, ticket_priority, white_label_support, audit_log_retention_days, billing_cycle_days, trial_days, price_cents, is_active, is_custom, created_at, updated_at) VALUES ('CUSTOM', 'Custom', 'SuperAdmin-assigned custom plan', 10, 5000, 50000, 204800, true, true, true, 'HIGH', true, 730, 30, 0, 0, true, true, NOW(), NOW()) ON CONFLICT (code) DO NOTHING"))


def downgrade() -> None:
    op.drop_index("ix_email_logs_recipient_email", table_name="email_logs")
    op.drop_table("email_logs")
    op.drop_index("ix_subscription_usage_month_key", table_name="subscription_usage")
    op.drop_table("subscription_usage")
    op.drop_index("ix_subscription_requests_company_id", table_name="subscription_requests")
    op.drop_table("subscription_requests")
    op.drop_index("ix_subscription_plans_code", table_name="subscription_plans")
    op.drop_table("subscription_plans")
    op.drop_column("subscriptions", "trial_used")
    op.drop_column("subscriptions", "scheduled_effective_at")
    op.drop_column("subscriptions", "scheduled_plan_name")
    op.drop_column("companies", "last_quota_reset_at")
    op.drop_column("companies", "trial_used")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
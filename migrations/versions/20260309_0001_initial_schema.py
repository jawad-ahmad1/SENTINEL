"""Initial schema for Sentinel attendance system.

Revision ID: 20260309_0001
Revises:
Create Date: 2026-03-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260309_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=128), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=True),
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            server_default="readonly",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("true"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("rfid_uid", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("position", sa.String(length=100), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("true"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rfid_uid"),
    )
    op.create_index("ix_employees_id", "employees", ["id"], unique=False)
    op.create_index("ix_employees_rfid_uid", "employees", ["rfid_uid"], unique=False)

    op.create_table(
        "attendance_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("work_start", sa.String(length=5), nullable=False),
        sa.Column("work_end", sa.String(length=5), nullable=False),
        sa.Column("grace_minutes", sa.Integer(), nullable=False),
        sa.Column("allowed_absent", sa.Integer(), nullable=False),
        sa.Column("allowed_leave", sa.Integer(), nullable=False),
        sa.Column("allowed_half_day", sa.Integer(), nullable=False),
        sa.Column("timezone_offset", sa.String(length=6), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "attendance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("rfid_uid", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date", sa.String(length=10), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "event_type IN ('IN', 'OUT', 'BREAK_START', 'BREAK_END')",
            name="ck_attendance_event_type",
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attendance_id", "attendance", ["id"], unique=False)
    op.create_index("ix_attendance_timestamp", "attendance", ["timestamp"], unique=False)
    op.create_index("ix_attendance_date", "attendance", ["date"], unique=False)
    op.create_index(
        "ix_attendance_employee_date",
        "attendance",
        ["employee_id", "date"],
        unique=False,
    )

    op.create_table(
        "absence_overrides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('LEAVE', 'BUSINESS_TRIP', 'WORK_FROM_HOME', 'HALF_DAY', 'SUPPLIER_VISIT')",
            name="ck_override_status",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "date", name="uq_override_emp_date"),
    )
    op.create_index("ix_absence_overrides_id", "absence_overrides", ["id"], unique=False)
    op.create_index(
        "ix_override_employee_date",
        "absence_overrides",
        ["employee_id", "date"],
        unique=False,
    )
    op.create_index("ix_override_date", "absence_overrides", ["date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_override_date", table_name="absence_overrides")
    op.drop_index("ix_override_employee_date", table_name="absence_overrides")
    op.drop_index("ix_absence_overrides_id", table_name="absence_overrides")
    op.drop_table("absence_overrides")

    op.drop_index("ix_attendance_employee_date", table_name="attendance")
    op.drop_index("ix_attendance_date", table_name="attendance")
    op.drop_index("ix_attendance_timestamp", table_name="attendance")
    op.drop_index("ix_attendance_id", table_name="attendance")
    op.drop_table("attendance")

    op.drop_table("attendance_settings")

    op.drop_index("ix_employees_rfid_uid", table_name="employees")
    op.drop_index("ix_employees_id", table_name="employees")
    op.drop_table("employees")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

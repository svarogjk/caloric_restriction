"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=True, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=True),
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("context_type", sa.String(50), nullable=False, server_default="general"),
        sa.Column("analysis_query", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_conversations_created_at", "conversations", ["created_at"])
    op.create_index("ix_conversations_updated_at", "conversations", ["updated_at"])
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "query_estimations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("original_query", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("estimated_datasets", sa.Integer(), nullable=True),
        sa.Column("estimated_time_seconds", sa.Float(), nullable=True),
        sa.Column("can_proceed", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("improved_query", sa.Text(), nullable=True),
        sa.Column("suggestions", sa.JSON(), nullable=True),
        sa.Column("has_survival_keywords", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("has_cancer_type", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("has_organism", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("has_gene_focus", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_query_estimations_created_at", "query_estimations", ["created_at"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.String(36),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("model_used", sa.String(50), nullable=True),
        sa.Column("is_complete", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("tool_calls", sa.JSON(), nullable=True),
        sa.Column(
            "estimation_id",
            sa.String(36),
            sa.ForeignKey("query_estimations.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])

    op.create_table(
        "analysis_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("n_datasets_analyzed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_datasets_with_survival", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_genes_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processing_time_seconds", sa.Float(), nullable=True),
        sa.Column("result_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_analysis_results_user_id", "analysis_results", ["user_id"])
    op.create_index("ix_analysis_results_created_at", "analysis_results", ["created_at"])


def downgrade() -> None:
    op.drop_table("analysis_results")
    op.drop_table("messages")
    op.drop_table("query_estimations")
    op.drop_table("conversations")
    op.drop_table("users")

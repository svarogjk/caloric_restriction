"""add_pgvector_extension_and_rag_embedding_table

Revision ID: adf02cf273dd
Revises: 2fe3cdda78aa
Create Date: 2026-03-04 12:35:38.001908

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'adf02cf273dd'
down_revision: Union[str, Sequence[str], None] = '2fe3cdda78aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mistral mistral-embed produces 1024-dim vectors
EMBEDDING_DIM = 1024


def upgrade() -> None:
    """Upgrade schema."""
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # langchain-postgres PGVector collection registry
    op.create_table(
        "langchain_pg_collection",
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("cmetadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("name"),
    )

    # langchain-postgres PGVector embedding store
    op.create_table(
        "langchain_pg_embedding",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "collection_id",
            sa.UUID(),
            sa.ForeignKey("langchain_pg_collection.uuid", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("document", sa.String(), nullable=True),
        sa.Column("cmetadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Index for fast cosine similarity search
    op.execute(
        "CREATE INDEX ix_langchain_pg_embedding_vector "
        "ON langchain_pg_embedding "
        "USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_langchain_pg_embedding_vector")
    op.drop_table("langchain_pg_embedding")
    op.drop_table("langchain_pg_collection")
    # Leave vector extension in place — other tools may use it

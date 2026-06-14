"""add book_metadata table

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "book_metadata",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE"), unique=True, index=True, nullable=False),
        # Source (parsed from file)
        sa.Column("source_title", sa.String(500)),
        sa.Column("source_author", sa.String(500)),
        sa.Column("source_description", sa.Text),
        sa.Column("source_publisher", sa.String(255)),
        sa.Column("source_language", sa.String(10)),
        sa.Column("source_isbn", sa.String(20)),
        sa.Column("source_publish_date", sa.String(50)),
        # Calibrated (admin override)
        sa.Column("calibrated_title", sa.String(500)),
        sa.Column("calibrated_author", sa.String(500)),
        sa.Column("calibrated_description", sa.Text),
        sa.Column("calibrated_publisher", sa.String(255)),
        sa.Column("calibrated_language", sa.String(10)),
        sa.Column("calibrated_isbn", sa.String(20)),
        # Additional
        sa.Column("series_name", sa.String(255)),
        sa.Column("series_index", sa.String(20)),
        sa.Column("subjects", JSONB),
        sa.Column("identifiers", JSONB),
        # Provenance
        sa.Column("metadata_source", sa.String(50)),
        sa.Column("last_calibrated_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("last_calibrated_at", sa.DateTime(timezone=True)),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("book_metadata")

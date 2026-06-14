"""add reviews, collections, metadata_cache, thumbnails, dead_letter_tasks

Revision ID: 003
Revises: 002
Create Date: 2024-01-03 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add rating columns to books
    op.add_column("books", sa.Column("avg_rating", sa.Numeric(3, 2)))
    op.add_column("books", sa.Column("rating_count", sa.Integer, server_default="0"))

    # Reviews table
    op.create_table(
        "reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("rating", sa.SmallInteger, nullable=False),
        sa.Column("review_text", sa.Text),
        sa.Column("is_visible", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "book_id", name="uq_review_user_book"),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
    )

    # Collections table
    op.create_table(
        "collections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("collection_type", sa.String(20), server_default="custom"),
        sa.Column("is_system", sa.Boolean, server_default="false"),
        sa.Column("vector_clock", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "name", name="uq_collection_user_name"),
    )

    # Collection items table
    op.create_table(
        "collection_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("collection_id", UUID(as_uuid=True), sa.ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("position", sa.Integer, server_default="0"),
        sa.Column("device_id", sa.String(100)),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("collection_id", "book_id", name="uq_collection_item_book"),
    )

    # Metadata cache table
    op.create_table(
        "metadata_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("external_id", sa.String(255)),
        sa.Column("query_key", sa.String(512), nullable=False),
        sa.Column("response_data", JSONB, nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "query_key", name="uq_metadata_cache_provider_query"),
    )
    op.create_index("idx_metadata_cache_expires", "metadata_cache", ["expires_at"])

    # Thumbnails table
    op.create_table(
        "thumbnails",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("size_variant", sa.String(20), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("width", sa.Integer),
        sa.Column("height", sa.Integer),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("book_id", "size_variant", name="uq_thumbnail_book_size"),
    )

    # Dead letter tasks table
    op.create_table(
        "dead_letter_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_type", sa.String(50), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("error_message", sa.Text),
        sa.Column("attempts", sa.Integer, server_default="0"),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Trigram indexes for fuzzy search (pg_trgm extension already enabled in 001)
    op.create_index("idx_books_title_trgm", "books", ["title"], postgresql_using="gin",
                    postgresql_ops={"title": "gin_trgm_ops"})
    op.create_index("idx_books_author_trgm", "books", ["author"], postgresql_using="gin",
                    postgresql_ops={"author": "gin_trgm_ops"})


def downgrade() -> None:
    op.drop_index("idx_books_author_trgm")
    op.drop_index("idx_books_title_trgm")
    op.drop_table("dead_letter_tasks")
    op.drop_table("thumbnails")
    op.drop_index("idx_metadata_cache_expires")
    op.drop_table("metadata_cache")
    op.drop_table("collection_items")
    op.drop_table("collections")
    op.drop_table("reviews")
    op.drop_column("books", "rating_count")
    op.drop_column("books", "avg_rating")

"""Add meta_data column to steps

Revision ID: 1c132ba2ff9d
Revises: aa23c724e360
Create Date: 2025-04-09 15:25:33.628196

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import enum
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic
revision = '1c132ba2ff9d'
down_revision = 'aa23c724e360'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add meta_data column to steps table
    op.execute("""
    ALTER TABLE steps 
    ADD COLUMN meta_data JSONB 
    DEFAULT '{}' NOT NULL;
    """)

    # Optional: Add an index for potential queries on metadata
    op.execute("""
    CREATE INDEX idx_steps_meta_data 
    ON steps USING GIN (meta_data);
    """)


def downgrade() -> None:
    # Drop the index first
    op.execute("""
    DROP INDEX IF EXISTS idx_steps_meta_data;
    """)

    # Drop the meta_data column
    op.execute("""
    ALTER TABLE steps 
    DROP COLUMN IF EXISTS meta_data;
    """)
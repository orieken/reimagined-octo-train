"""add_scenario_tags_table

Revision ID: aa23c724e360
Revises: 0001_initial_schema
Create Date: 2025-04-08 14:39:17.962432

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import enum
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = 'aa23c724e360'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create scenario_tags table
    op.execute("""
    CREATE TABLE scenario_tags (
        scenario_id INTEGER NOT NULL REFERENCES scenarios(id),
        tag VARCHAR(255) NOT NULL,
        PRIMARY KEY (scenario_id, tag)
    )
    """)

    # Add index for performance
    op.execute("CREATE INDEX idx_scenario_tags_scenario_id ON scenario_tags (scenario_id)")
    op.execute("CREATE INDEX idx_scenario_tags_tag ON scenario_tags (tag)")

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_scenario_tags_tag")
    op.execute("DROP INDEX IF EXISTS idx_scenario_tags_scenario_id")
    op.execute("DROP TABLE IF EXISTS scenario_tags")
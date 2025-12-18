"""change t_transaction.was_send to smallint

Revision ID: fdbd5d0bbfcb
Revises: 84f9468b5610
Create Date: 2025-11-07 01:03:35.851941

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fdbd5d0bbfcb'
down_revision: Union[str, Sequence[str], None] = '84f9468b5610'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert t_transaction.was_send from boolean to smallint."""
    op.execute(
        """
        ALTER TABLE t_transaction
        ALTER COLUMN was_send TYPE SMALLINT
        USING CASE
            WHEN was_send IS NULL THEN 0
            WHEN was_send IS TRUE THEN 1
            ELSE 0
        END
        """
    )
    op.alter_column(
        't_transaction',
        'was_send',
        existing_type=sa.SmallInteger(),
        server_default=sa.text('0'),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Convert t_transaction.was_send back to boolean."""
    op.execute(
        """
        ALTER TABLE t_transaction
        ALTER COLUMN was_send TYPE BOOLEAN
        USING CASE
            WHEN was_send IS NULL THEN FALSE
            ELSE was_send <> 0
        END
        """
    )
    op.alter_column(
        't_transaction',
        'was_send',
        existing_type=sa.Boolean(),
        server_default=sa.false(),
        existing_nullable=True,
    )

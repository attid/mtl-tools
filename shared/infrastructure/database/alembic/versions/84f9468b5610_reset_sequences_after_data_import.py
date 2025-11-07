"""reset sequences after data import

Revision ID: 84f9468b5610
Revises: b5af93f1af86
Create Date: 2025-11-07 00:45:52.086764

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '84f9468b5610'
down_revision: Union[str, Sequence[str], None] = 'b5af93f1af86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEQUENCES_TO_RESET = (
    ("bot_table", "id"),
    ("t_message", "id"),
    ("t_div_list", "id"),
    ("t_payments", "id"),
    ("t_transaction", "id"),
    ("mymtlwalletbot", "id"),
    ("mymtlwalletbot_log", "log_id"),
    ("t_summary", "id"),
    ("t_saved_messages", "id"),
)


def _build_setval_sql(table: str, column: str) -> str:
    return f"""
        WITH seq AS (
            SELECT pg_get_serial_sequence('{table}', '{column}') AS name
        ),
        max_id AS (
            SELECT COALESCE(MAX({column}), 0) AS value FROM {table}
        )
        SELECT CASE
            WHEN seq.name IS NULL THEN NULL
            ELSE setval(
                seq.name,
                GREATEST(max_id.value, 1),
                true
            )
        END
        FROM seq CROSS JOIN max_id;
    """


def upgrade() -> None:
    """Align auto-increment sequences with existing data."""
    for table, column in SEQUENCES_TO_RESET:
        op.execute(sa.text(_build_setval_sql(table, column)))


def downgrade() -> None:
    """No-op downgrade (sequence alignment is idempotent)."""
    pass

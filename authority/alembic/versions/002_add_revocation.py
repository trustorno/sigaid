"""Add token and key revocation tables.

Security enhancement: Allows invalidating tokens before their natural expiry
and tracking revoked keys for key rotation.

Revision ID: 002_revocation
Revises: 001_initial
Create Date: 2026-02-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '002_revocation'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create revoked_tokens table
    op.execute("""
        CREATE TABLE IF NOT EXISTS revoked_tokens (
            id SERIAL PRIMARY KEY,
            token_jti VARCHAR(64) NOT NULL UNIQUE,
            agent_id VARCHAR(64) NOT NULL,
            original_expiry TIMESTAMPTZ NOT NULL,
            revoked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            revoked_by VARCHAR(255),
            revocation_reason TEXT
        )
    """)

    # Indexes for revoked_tokens
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_revoked_tokens_jti
        ON revoked_tokens(token_jti)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expiry
        ON revoked_tokens(original_expiry)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_revoked_tokens_agent
        ON revoked_tokens(agent_id, revoked_at)
    """)

    # Create revoked_keys table for key rotation
    op.execute("""
        CREATE TABLE IF NOT EXISTS revoked_keys (
            id SERIAL PRIMARY KEY,
            key_id VARCHAR(16) NOT NULL UNIQUE,
            revoked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            revoked_by VARCHAR(255),
            revocation_reason TEXT,
            grace_period_end TIMESTAMPTZ
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_revoked_keys_key_id
        ON revoked_keys(key_id)
    """)

    # Create function to clean up expired revoked tokens
    op.execute("""
        CREATE OR REPLACE FUNCTION sigaid_cleanup_revoked_tokens(retention_hours INTEGER DEFAULT 24)
        RETURNS INTEGER AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            DELETE FROM revoked_tokens
            WHERE original_expiry < NOW() - (retention_hours || ' hours')::INTERVAL;

            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS sigaid_cleanup_revoked_tokens(INTEGER);")
    op.execute("DROP TABLE IF EXISTS revoked_keys;")
    op.execute("DROP TABLE IF EXISTS revoked_tokens;")

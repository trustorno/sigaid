"""Initial schema for SigAid Authority Service.

Creates tables:
- agents: Agent registry with Ed25519 public keys
- leases: Exclusive lease management
- state_entries: Tamper-evident state chain
- reputation: Cached reputation metrics
- api_keys: API keys for verification

Revision ID: 001_initial
Revises:
Create Date: 2026-02-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types first using raw SQL
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE agent_status AS ENUM ('active', 'suspended', 'revoked');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE action_type AS ENUM ('transaction', 'attestation', 'upgrade', 'reset', 'custom');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create agents table using raw SQL to properly use existing enum
    op.execute("""
        CREATE TABLE agents (
            id SERIAL PRIMARY KEY,
            agent_id VARCHAR(64) NOT NULL UNIQUE,
            public_key BYTEA NOT NULL,
            status agent_status NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            revoked_at TIMESTAMPTZ,
            metadata JSONB DEFAULT '{}'
        )
    """)
    op.create_index('idx_agents_agent_id', 'agents', ['agent_id'])
    op.create_index('idx_agents_public_key', 'agents', ['public_key'])

    # Create leases table
    op.execute("""
        CREATE TABLE leases (
            id SERIAL PRIMARY KEY,
            agent_id VARCHAR(64) NOT NULL UNIQUE REFERENCES agents(agent_id) ON DELETE CASCADE,
            session_id VARCHAR(64) NOT NULL,
            token_jti VARCHAR(64) NOT NULL,
            sequence INTEGER DEFAULT 0,
            acquired_at TIMESTAMPTZ NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            last_renewed_at TIMESTAMPTZ
        )
    """)
    op.create_index('idx_leases_expires', 'leases', ['expires_at'])

    # Create state_entries table
    op.execute("""
        CREATE TABLE state_entries (
            id BIGSERIAL PRIMARY KEY,
            agent_id VARCHAR(64) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
            sequence BIGINT NOT NULL,
            prev_hash BYTEA NOT NULL,
            entry_hash BYTEA NOT NULL UNIQUE,
            action_type action_type NOT NULL,
            action_summary TEXT,
            action_data_hash BYTEA,
            signature BYTEA NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(agent_id, sequence)
        )
    """)
    op.create_index('idx_state_agent_seq', 'state_entries', ['agent_id', 'sequence'])
    op.create_index('idx_state_entry_hash', 'state_entries', ['entry_hash'])

    # Create reputation table
    op.execute("""
        CREATE TABLE reputation (
            id SERIAL PRIMARY KEY,
            agent_id VARCHAR(64) NOT NULL UNIQUE REFERENCES agents(agent_id) ON DELETE CASCADE,
            total_transactions BIGINT DEFAULT 0,
            successful_transactions BIGINT DEFAULT 0,
            age_days INTEGER DEFAULT 0,
            last_activity_at TIMESTAMPTZ,
            score FLOAT DEFAULT 0.0,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Create api_keys table
    op.execute("""
        CREATE TABLE api_keys (
            id SERIAL PRIMARY KEY,
            key_hash BYTEA NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            rate_limit_per_minute INTEGER DEFAULT 1000,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            last_used_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ
        )
    """)
    op.create_index('idx_api_keys_hash', 'api_keys', ['key_hash'])

    # Create helper functions for PostgreSQL advisory locks
    op.execute("""
        CREATE OR REPLACE FUNCTION sigaid_try_acquire_lease(p_agent_id VARCHAR(64))
        RETURNS BOOLEAN AS $$
        BEGIN
            RETURN pg_try_advisory_lock(hashtext(p_agent_id));
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION sigaid_release_lease(p_agent_id VARCHAR(64))
        RETURNS BOOLEAN AS $$
        BEGIN
            RETURN pg_advisory_unlock(hashtext(p_agent_id));
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS sigaid_release_lease(VARCHAR) CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS sigaid_try_acquire_lease(VARCHAR) CASCADE;")

    # Drop tables
    op.drop_table('api_keys')
    op.drop_table('reputation')
    op.drop_table('state_entries')
    op.drop_table('leases')
    op.drop_table('agents')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS action_type;")
    op.execute("DROP TYPE IF EXISTS agent_status;")

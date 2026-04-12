"""Add knowledge module tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])

    op.create_table(
        'conversation_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sources', postgresql.JSONB(), nullable=True),
        sa.Column('query_type', sa.String(32), nullable=True),
        sa.Column('brand', sa.String(32), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conversation_messages_conversation_id', 'conversation_messages', ['conversation_id'])

    op.create_table(
        'knowledge_favorites',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source_type', sa.String(32), nullable=False),
        sa.Column('brand', sa.String(32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['conversation_messages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_knowledge_favorites_user_id', 'knowledge_favorites', ['user_id'])

    op.create_table(
        'sel_event_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('brand', sa.String(32), nullable=False),
        sa.Column('event_code', sa.String(16), nullable=False),
        sa.Column('sensor_type', sa.String(64), nullable=True),
        sa.Column('severity', sa.String(16), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('recommended_action', sa.Text(), nullable=True),
        sa.Column('source_document_id', sa.String(128), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sel_event_codes_brand', 'sel_event_codes', ['brand'])
    op.create_index('ix_sel_event_codes_brand_code', 'sel_event_codes', ['brand', 'event_code'])

    op.create_table(
        'firmware_compatibility',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('brand', sa.String(32), nullable=False),
        sa.Column('model', sa.String(128), nullable=False),
        sa.Column('component', sa.String(64), nullable=False),
        sa.Column('version', sa.String(64), nullable=False),
        sa.Column('release_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('criticality', sa.String(16), nullable=False, server_default='optional'),
        sa.Column('release_notes', sa.Text(), nullable=True),
        sa.Column('download_url', sa.String(512), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_firmware_compatibility_brand', 'firmware_compatibility', ['brand'])
    op.create_index('ix_firmware_compatibility_brand_model', 'firmware_compatibility', ['brand', 'model'])


def downgrade() -> None:
    op.drop_table('firmware_compatibility')
    op.drop_table('sel_event_codes')
    op.drop_table('knowledge_favorites')
    op.drop_table('conversation_messages')
    op.drop_table('conversations')

"""Initial chat tables.

Revision ID: 001_initial
Revises:
Create Date: 2024-12-17 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  # Create chats table
  op.create_table(
    'chats',
    sa.Column('id', sa.String(50), primary_key=True),
    sa.Column('user_email', sa.String(255), nullable=False, index=True),
    sa.Column('title', sa.String(255), server_default='New Chat'),
    sa.Column('agent_id', sa.String(100), nullable=True),
    sa.Column(
      'created_at',
      sa.DateTime(timezone=True),
      server_default=sa.func.now(),
      nullable=False,
    ),
    sa.Column(
      'updated_at',
      sa.DateTime(timezone=True),
      server_default=sa.func.now(),
      onupdate=sa.func.now(),
      nullable=False,
    ),
  )

  # Create composite index for user + updated_at queries
  op.create_index(
    'ix_chats_user_updated',
    'chats',
    ['user_email', 'updated_at'],
  )

  # Create messages table
  op.create_table(
    'messages',
    sa.Column('id', sa.String(50), primary_key=True),
    sa.Column(
      'chat_id',
      sa.String(50),
      sa.ForeignKey('chats.id', ondelete='CASCADE'),
      nullable=False,
      index=True,
    ),
    sa.Column('role', sa.String(20), nullable=False),
    sa.Column('content', sa.Text, nullable=False),
    sa.Column(
      'timestamp',
      sa.DateTime(timezone=True),
      server_default=sa.func.now(),
      nullable=False,
    ),
    sa.Column('trace_id', sa.String(100), nullable=True),
    sa.Column('trace_summary', postgresql.JSONB, nullable=True),
    sa.Column('is_error', sa.Boolean(), nullable=False, server_default='false'),
  )

  # Create composite index for chat + timestamp queries
  op.create_index(
    'ix_messages_chat_timestamp',
    'messages',
    ['chat_id', 'timestamp'],
  )


def downgrade() -> None:
  op.drop_index('ix_messages_chat_timestamp', table_name='messages')
  op.drop_table('messages')
  op.drop_index('ix_chats_user_updated', table_name='chats')
  op.drop_index('ix_chats_user_email', table_name='chats')
  op.drop_table('chats')

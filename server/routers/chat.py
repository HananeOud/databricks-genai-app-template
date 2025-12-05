"""Chat management endpoints for creating and managing chat sessions."""

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

from ..chat_storage import Message, storage

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateChatRequest(BaseModel):
  """Request to create a new chat."""

  title: Optional[str] = 'New Chat'
  agent_id: Optional[str] = None


class AddMessageRequest(BaseModel):
  """Request to add messages to a chat."""

  messages: list[dict]  # List of {role, content}


@router.get('/chats')
async def get_all_chats():
  """Get all chats sorted by updated_at (newest first).

  Returns list of chat objects with messages.
  """
  logger.info('Fetching all chats')
  chats = storage.get_all()
  logger.info(f'Retrieved {len(chats)} chats')

  # Convert to dict for JSON serialization
  return [chat.dict() for chat in chats]


@router.post('/chats')
async def create_new_chat(request: CreateChatRequest):
  """Create a new chat session.

  If 10 chats already exist, deletes the oldest chat.
  """
  logger.info(f'Creating new chat: title="{request.title}", agent_id={request.agent_id}')

  chat = storage.create(title=request.title, agent_id=request.agent_id)

  logger.info(f'Chat created: {chat.id}')
  return chat.dict()


@router.get('/chats/{chat_id}')
async def get_chat_by_id(chat_id: str):
  """Get specific chat by ID with all messages."""
  logger.info(f'Fetching chat: {chat_id}')

  chat = storage.get(chat_id)
  if not chat:
    logger.warning(f'Chat not found: {chat_id}')
    return Response(content=f'Chat {chat_id} not found', status_code=404)

  logger.info(f'Retrieved chat {chat_id} with {len(chat.messages)} messages')
  return chat.dict()


@router.post('/chats/{chat_id}/messages')
async def add_messages_to_chat(chat_id: str, request: AddMessageRequest):
  """Add messages to an existing chat."""
  logger.info(f'Adding {len(request.messages)} messages to chat: {chat_id}')

  chat = storage.get(chat_id)
  if not chat:
    logger.warning(f'Chat not found: {chat_id}')
    return Response(content=f'Chat {chat_id} not found', status_code=404)

  # Add each message
  for msg_data in request.messages:
    message = Message(
      id=f'msg_{uuid.uuid4().hex[:12]}',
      role=msg_data['role'],
      content=msg_data['content'],
      timestamp=datetime.now(),
      trace_id=msg_data.get('trace_id'),  # Optional trace ID from MLflow
      trace_summary=msg_data.get('trace_summary'),  # Optional trace summary data
    )
    storage.add_message(chat_id, message)

  logger.info(f'Added messages to chat {chat_id}, now has {len(chat.messages)} total messages')
  return {'success': True, 'message_count': len(chat.messages)}


@router.delete('/chats/{chat_id}')
async def delete_chat_by_id(chat_id: str):
  """Delete specific chat by ID."""
  logger.info(f'Deleting chat: {chat_id}')

  success = storage.delete(chat_id)
  if not success:
    logger.warning(f'Chat not found for deletion: {chat_id}')
    return Response(content=f'Chat {chat_id} not found', status_code=404)

  logger.info(f'Chat deleted: {chat_id}')
  return {'success': True, 'deleted_chat_id': chat_id}


@router.delete('/chats')
async def clear_all_chats():
  """Delete all chats."""
  logger.info('Clearing all chats')

  count = storage.clear_all()

  logger.info(f'Cleared {count} chats')
  return {'success': True, 'deleted_count': count}

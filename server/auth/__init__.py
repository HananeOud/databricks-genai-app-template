"""Authentication module for Databricks Apps.

Provides centralized authentication utilities and strategies for different
deployment scenarios (calling endpoints vs running local agents).
"""

from .databricks_auth import (
  get_databricks_host,
  get_user_token_from_request,
  is_local_development,
)
from .strategies import AuthStrategy, HttpTokenAuth, WorkspaceClientAuth

__all__ = [
  'get_databricks_host',
  'get_user_token_from_request',
  'is_local_development',
  'AuthStrategy',
  'HttpTokenAuth',
  'WorkspaceClientAuth',
]

"""Authentication strategy classes for different deployment scenarios.

Each strategy encapsulates the credential retrieval logic for a specific
deployment type (calling external endpoints vs running local agents).
"""

import logging
from abc import ABC, abstractmethod
from typing import Tuple

from databricks.sdk import WorkspaceClient
from fastapi import Request

from .databricks_auth import (
  get_databricks_host,
  get_dev_token,
  get_user_token_from_request,
  is_local_development,
)

logger = logging.getLogger(__name__)


class AuthStrategy(ABC):
  """Base class for authentication strategies.

  Each deployment type requires different credential formats:
  - HTTP endpoints need (host, token) for Authorization headers
  - Local agents need WorkspaceClient for SDK operations
  """

  @abstractmethod
  def get_credentials(self, request: Request):
    """Get credentials for this deployment type.

    Args:
      request: FastAPI Request object (provides access to headers)

    Returns:
      Credentials in the format needed by the deployment type
    """
    pass


class HttpTokenAuth(AuthStrategy):
  """Authentication strategy for calling external HTTP endpoints.

  Used when calling Databricks Model Serving endpoints or other HTTP APIs.
  Returns (host, token) tuple for use in Authorization: Bearer headers.

  Dev mode: Uses PAT token from DATABRICKS_TOKEN environment variable
  Prod mode: Uses user's forwarded access token from request headers
  """

  def get_credentials(self, request: Request) -> Tuple[str, str]:
    """Get (host, token) for HTTP Authorization header.

    Args:
      request: FastAPI Request object

    Returns:
      Tuple of (databricks_host, access_token)

    Raises:
      ValueError: If required environment variables or headers are missing
    """
    host = get_databricks_host()

    if is_local_development():
      # Local development: Use PAT from environment
      logger.info('🔧 Development mode - using PAT token from environment')
      token = get_dev_token()
      logger.info(f'✅ Using Databricks credentials from environment: {host}')
    else:
      # Production: Use user's forwarded token from Databricks Apps
      logger.info('🚀 Production mode - using user forwarded token')
      token = get_user_token_from_request(request)
      user_email = request.headers.get('x-forwarded-email', 'unknown')
      logger.info(f'✅ Using user token for: {user_email} @ {host}')

    return host, token


class WorkspaceClientAuth(AuthStrategy):
  """Authentication strategy for local agents using Databricks SDK.

  Used when running agents locally within the FastAPI server that need to
  access Databricks resources (Vector Search, SQL, Model Serving, etc.)
  Returns configured WorkspaceClient instance.

  Dev mode: Creates WorkspaceClient with PAT token
  Prod mode: Creates WorkspaceClient with user's forwarded token

  This allows agents to use the Databricks SDK's high-level APIs while
  maintaining user-level permissions and audit trails.
  """

  def get_credentials(self, request: Request) -> WorkspaceClient:
    """Get configured WorkspaceClient for SDK operations.

    Args:
      request: FastAPI Request object

    Returns:
      Configured WorkspaceClient instance

    Raises:
      ValueError: If required environment variables or headers are missing
    """
    host = get_databricks_host()

    if is_local_development():
      # Local development: Use PAT from environment
      logger.info('🔧 Development mode - creating WorkspaceClient with PAT')
      token = get_dev_token()
      workspace_client = WorkspaceClient(host=host, token=token, auth_type='pat')
      logger.info(f'✅ Created WorkspaceClient for: {host}')
    else:
      # Production: Use user's forwarded token
      logger.info('🚀 Production mode - creating WorkspaceClient with user token')
      token = get_user_token_from_request(request)
      user_email = request.headers.get('x-forwarded-email', 'unknown')
      workspace_client = WorkspaceClient(host=host, token=token, auth_type='pat')
      logger.info(f'✅ Created WorkspaceClient for user: {user_email} @ {host}')

    return workspace_client

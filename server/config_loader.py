"""Configuration loader for the application.

Loads unified configuration from config/app.json at startup.
All config (branding, agents, home, dashboard, about) is in one file.

Agent configuration supports two formats (mutually exclusive):
1. endpoint_name: Direct endpoint name (e.g., "mas-45eb36c4-endpoint")
2. mas_id: MAS tile UUID (e.g., "45eb36c4-0e8a-4094-aa86-67df6e0b455d")
   - Resolved to endpoint_name via API at startup

In development mode, config is re-read from disk on every access (no caching).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .services.user import _is_local_development

logger = logging.getLogger(__name__)


class ConfigLoader:
  """Loads and caches application configuration from app.json."""

  def __init__(self, config_dir: Optional[Path] = None):
    """Initialize the config loader.

    Args:
        config_dir: Path to config directory. Defaults to /config in project root.
    """
    if config_dir is None:
      # Default to /config directory at project root
      config_dir = Path(__file__).parent.parent / 'config'

    self.config_dir = config_dir
    self._app_config: Optional[Dict[str, Any]] = None

    # Load config at initialization
    self._load_all()

  def _load_json_file(self, filename: str) -> Dict[str, Any]:
    """Load a JSON file from the config directory.

    Args:
        filename: Name of the JSON file to load

    Returns:
        Dictionary with file contents, or empty dict if file not found
    """
    file_path = self.config_dir / filename

    if not file_path.exists():
      logger.warning(f'Config file not found: {file_path}')
      return {}

    try:
      with open(file_path, 'r') as f:
        data = json.load(f)
        logger.info(f'✅ Loaded config: {filename}')
        return data
    except json.JSONDecodeError as e:
      logger.error(f'Failed to parse {filename}: {e}')
      return {}
    except Exception as e:
      logger.error(f'Error loading {filename}: {e}')
      return {}

  def _load_all(self):
    """Load configuration from app.json."""
    logger.info('Loading application configuration...')

    self._app_config = self._load_json_file('app.json')

    # Resolve mas_id to endpoint_name for agents that use it
    self._resolve_mas_ids()

    # Log summary
    agent_count = len(self._app_config.get('agents', []))
    logger.info(f'✅ Configuration loaded: {agent_count} agents configured')

  def _resolve_mas_ids(self):
    """Resolve mas_id to endpoint_name for agents that use mas_id.

    This queries the Databricks API to get the serving_endpoint_name for each mas_id.
    """
    agents = self._app_config.get('agents', [])
    if not agents:
      return

    # Check if any agents use mas_id
    agents_with_mas_id = [
      (i, agent) for i, agent in enumerate(agents)
      if isinstance(agent, dict) and agent.get('mas_id')
    ]

    if not agents_with_mas_id:
      return

    # Validate: mas_id and endpoint_name are mutually exclusive
    for i, agent in agents_with_mas_id:
      if agent.get('endpoint_name'):
        raise ValueError(
          f"Agent at index {i} has both 'mas_id' and 'endpoint_name'. "
          "These are mutually exclusive - use only one."
        )

    # Import here to avoid circular imports
    from .services.agents.agent_bricks_service import get_agent_bricks_service

    try:
      service = get_agent_bricks_service()
    except Exception as e:
      logger.warning(f"Could not initialize AgentBricksService to resolve mas_ids: {e}")
      logger.warning("Agents with mas_id will not be resolved. Check Databricks credentials.")
      return

    for i, agent in agents_with_mas_id:
      mas_id = agent['mas_id']
      logger.info(f"Attempting to resolve mas_id '{mas_id}'...")
      try:
        endpoint_name = service.get_endpoint_name_from_mas_id(mas_id)
        agent['endpoint_name'] = endpoint_name
        logger.info(f"✅ Resolved mas_id '{mas_id}' -> endpoint '{endpoint_name}'")
      except Exception as e:
        logger.error(f"❌ Failed to resolve mas_id '{mas_id}': {e}")
        import traceback
        logger.error(traceback.format_exc())
        agent['_error'] = f"Failed to resolve mas_id: {e}"

  @property
  def app_config(self) -> Dict[str, Any]:
    """Get full application configuration.

    In dev mode, re-reads from disk on every access for hot-reload.
    In production, uses cached value for performance.
    """
    if _is_local_development():
      # Dev mode: always re-read from disk
      return self._load_json_file('app.json')

    # Production: use cached value
    if self._app_config is None:
      self._app_config = self._load_json_file('app.json')
    return self._app_config

  @property
  def agents_config(self) -> Dict[str, Any]:
    """Get agents configuration (from app_config.agents)."""
    return {'agents': self.app_config.get('agents', [])}

  def get_agent_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific agent configuration by ID, endpoint_name, or mas_id.

    Supports these formats:
    - endpoint_name: {"endpoint_name": "mas-xxx-endpoint", ...}
    - mas_id: {"mas_id": "uuid-...", ...} (resolved to endpoint_name at startup)
    - Legacy: {"id": "agent-id", ...}

    Also handles lookup by resolved endpoint_name when config only has mas_id.

    Args:
        agent_id: The agent ID, endpoint_name, or mas_id to look up

    Returns:
        Agent configuration dict with endpoint_name, or None if not found
    """
    agents = self.app_config.get('agents', [])
    for agent in agents:
      # Handle string format (legacy - just endpoint name)
      if isinstance(agent, str):
        if agent == agent_id:
          return {'endpoint_name': agent}
        continue

      # Handle object format
      # Match by endpoint_name, mas_id, or id (legacy)
      if (
        agent.get('endpoint_name') == agent_id
        or agent.get('mas_id') == agent_id
        or agent.get('id') == agent_id
      ):
        # Ensure endpoint_name is always set
        result = dict(agent)
        if 'endpoint_name' not in result and 'id' in result:
          result['endpoint_name'] = result['id']
        return result

      # Also check if agent_id matches the expected endpoint pattern for a mas_id
      # This handles the case where frontend sends endpoint_name but config only has mas_id
      mas_id = agent.get('mas_id')
      if mas_id and not agent.get('endpoint_name'):
        # Check if agent_id matches the pattern mas-{first_8_chars}-endpoint
        expected_endpoint = f"mas-{mas_id.split('-')[0]}-endpoint"
        if agent_id == expected_endpoint:
          result = dict(agent)
          result['endpoint_name'] = expected_endpoint
          return result

    return None

  def reload(self):
    """Reload configuration from disk."""
    logger.info('Reloading configuration...')
    self._app_config = None
    self._load_all()


# Global config loader instance
config_loader = ConfigLoader()

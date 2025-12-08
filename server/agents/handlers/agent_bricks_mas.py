"""Handler for Agent Bricks Multi-Agent Supervisor (MAS) endpoints.

This handler is specialized for MAS endpoints that orchestrate multiple agents
in a supervisor-specialist pattern. It tracks agent handoffs, collects messages
per agent, and builds hierarchical trace structures showing the full flow.
"""

import json
import logging
import re
from typing import Any, AsyncGenerator, Dict, List

import httpx
from fastapi import Request

from ...auth.strategies import HttpTokenAuth
from .base import BaseDeploymentHandler

logger = logging.getLogger(__name__)


class AgentBricksMASHandler(BaseDeploymentHandler):
  """Handler for Agent Bricks Multi-Agent Supervisor endpoints.

  Key differences from standard Databricks endpoints:
  1. Multi-agent orchestration with supervisor/specialist pattern
  2. Agent name tags (<name>agent-X</name>) indicate agent switches
  3. Plain string outputs for handoff messages (not JSON)
  4. Builds hierarchical trace showing supervisor → specialist → synthesis

  Uses HttpTokenAuth strategy for authentication (user token forwarding).
  """

  def __init__(self, agent_config: Dict[str, Any]):
    """Initialize handler with agent configuration.

    Args:
      agent_config: Agent config containing 'endpoint_name'
    """
    # Initialize with HttpTokenAuth strategy for calling HTTP endpoints
    super().__init__(agent_config, auth_strategy=HttpTokenAuth())
    self.endpoint_name = agent_config.get('endpoint_name')

    if not self.endpoint_name:
      raise ValueError(f'Agent {agent_config.get("id")} has no endpoint_name configured')

  async def invoke_stream(
    self, messages: List[Dict[str, str]], client_request_id: str, request: Request
  ) -> AsyncGenerator[str, None]:
    """Stream response from MAS endpoint with supervisor/specialist flow tracking.

    Parses SSE events during streaming to:
    - Track agent name switches (<name>agent-X</name>)
    - Collect messages per agent (supervisor vs specialists)
    - Capture handoff requests and responses
    - Build hierarchical trace structure

    Args:
      messages: List of messages with 'role' and 'content' keys
      client_request_id: Unique ID for trace linking (from endpoint)
      request: FastAPI Request object (for auth headers)

    Yields:
      Server-Sent Events (SSE) formatted strings with JSON data
    """
    # Emit client_request_id as first event for frontend to capture
    logger.info(f'Emitting client_request_id to frontend: {client_request_id}')
    trace_event = {'type': 'trace.client_request_id', 'client_request_id': client_request_id}
    yield f'data: {json.dumps(trace_event)}\n\n'

    # Get Databricks credentials using auth strategy
    host, token = self.auth_strategy.get_credentials(request)

    # Build request payload (Databricks Agent API format with streaming enabled)
    payload = {
      'input': messages,
      'stream': True,  # CRITICAL: Tell Databricks to stream the response
    }
    url = f'{host}/serving-endpoints/{self.endpoint_name}/invocations'
    headers = {
      'Authorization': f'Bearer {token}',
      'Content-Type': 'application/json',
    }

    logger.info(f'Calling MAS endpoint (streaming): {self.endpoint_name}')

    # State tracking for multi-agent flow
    current_agent = None  # Track which agent is currently speaking
    supervisor_name = None  # Will be set from first agent name tag
    handoffs = []  # List of {specialist, request, response, messages}
    current_handoff = None  # Current specialist interaction being built
    function_calls = []  # All function calls for backward compat

    # Use async httpx client for proper async streaming
    async with httpx.AsyncClient(timeout=300.0) as client:
      async with client.stream('POST', url, json=payload, headers=headers) as response:
        response.raise_for_status()

        # Stream response chunks line by line
        async for line in response.aiter_lines():
          if not line:
            continue

          # Skip empty lines
          if not line.strip():
            continue

          # Handle [DONE] marker
          if line.strip() == 'data: [DONE]' or line.strip() == '[DONE]':
            # Build and emit final trace summary before [DONE]
            if handoffs:
              trace_summary = self._build_trace_summary(
                supervisor_name, handoffs, function_calls, client_request_id
              )
              trace_event = {'type': 'trace.summary', 'traceSummary': trace_summary}
              logger.info('📊 Emitting MAS trace summary with supervisor/specialist flow')
              yield f'data: {json.dumps(trace_event)}\n\n'

            yield 'data: [DONE]\n\n'
            continue

          # Extract JSON from SSE format
          json_str = line.strip()
          if json_str.startswith('data: '):
            json_str = json_str[6:].strip()
          elif json_str.startswith('data:'):
            json_str = json_str[5:].strip()

          if not json_str:
            continue

          try:
            # Parse the JSON event
            event = json.loads(json_str)

            # Track agent switches via <name>agent-X</name> tags
            if event.get('type') == 'response.output_item.done':
              item = event.get('item', {})

              # Check for agent name tag in message content
              if item.get('type') == 'message':
                content_items = item.get('content', [])
                for content in content_items:
                  if content.get('type') == 'output_text':
                    text = content.get('text', '')
                    # Look for <name>agent-X</name> pattern
                    name_match = re.search(r'<name>([^<]+)</name>', text)
                    if name_match:
                      agent_name = name_match.group(1)
                      logger.info(f'🔄 Agent switch detected: {current_agent} → {agent_name}')

                      # First agent we see is the supervisor
                      if supervisor_name is None:
                        supervisor_name = agent_name
                        logger.info(f'👔 Supervisor identified: {supervisor_name}')

                      # Switching to a different agent means handoff
                      if current_agent and current_agent != agent_name:
                        if agent_name == supervisor_name and current_handoff:
                          # Returning to supervisor, finalize current handoff
                          handoffs.append(current_handoff)
                          logger.info(f'✅ Handoff complete: {current_handoff["specialist"]}')
                          current_handoff = None

                      current_agent = agent_name
                      # Don't forward name tags to frontend (internal markers)
                      continue

              # Track function calls (handoff requests)
              if item.get('type') == 'function_call':
                fc_name = item.get('name', '')
                fc_args = item.get('arguments', '{}')
                fc_call_id = item.get('call_id', '')

                # Parse arguments
                try:
                  args = json.loads(fc_args) if isinstance(fc_args, str) else fc_args
                except json.JSONDecodeError:
                  args = {'raw': fc_args}

                # Create function call record
                function_call = {
                  'call_id': fc_call_id,
                  'name': fc_name,
                  'arguments': args,
                }
                function_calls.append(function_call)

                # Start new handoff tracking
                current_handoff = {
                  'specialist': fc_name,
                  'request': args,
                  'response': None,
                  'messages': [],
                  'call_id': fc_call_id,
                }
                logger.info(f'🤝 Handoff initiated to specialist: {fc_name}')

              # Track function call outputs (handoff confirmations)
              if item.get('type') == 'function_call_output':
                fc_output = item.get('output', '')
                fc_call_id = item.get('call_id', '')

                # Parse output (may be plain string for MAS)
                output_data = fc_output
                if isinstance(fc_output, str):
                  # Try JSON first
                  if fc_output.strip().startswith('{') or fc_output.strip().startswith('['):
                    try:
                      output_data = json.loads(fc_output)
                    except json.JSONDecodeError:
                      output_data = {'message': fc_output}
                  else:
                    # Plain string (handoff message)
                    output_data = {'message': fc_output}

                # Update function call record
                for fc in function_calls:
                  if fc['call_id'] == fc_call_id:
                    fc['output'] = output_data
                    break

                logger.info(f'📥 Handoff confirmation received: {fc_call_id}')

              # Collect messages from specialist
              if item.get('type') == 'message' and current_handoff:
                content_items = item.get('content', [])
                for content in content_items:
                  if content.get('type') == 'output_text':
                    text = content.get('text', '')
                    # Skip agent name tags
                    if not re.search(r'<name>[^<]+</name>', text):
                      current_handoff['messages'].append(text)
                      logger.info(f'📝 Specialist message collected ({len(text)} chars)')

            # Forward all events to the client (frontend still processes normally)
            yield f'data: {json_str}\n\n'

          except json.JSONDecodeError as e:
            logger.warning(f'Failed to parse JSON from stream: {e}, line: {json_str[:200]}')
            continue

  def _build_trace_summary(
    self,
    supervisor_name: str,
    handoffs: List[Dict[str, Any]],
    function_calls: List[Dict[str, Any]],
    trace_id: str,
  ) -> Dict[str, Any]:
    """Build hierarchical trace summary showing supervisor/specialist flow.

    Args:
      supervisor_name: Name of the supervisor agent
      handoffs: List of specialist interactions
      function_calls: List of all function calls (for backward compat)
      trace_id: Trace ID for linking

    Returns:
      Trace summary with hierarchical structure
    """
    # Build MAS-specific hierarchical structure
    mas_flow = {
      'supervisor': supervisor_name,
      'total_handoffs': len(handoffs),
      'handoffs': [
        {
          'specialist': h['specialist'],
          'request': h['request'],
          'response': h.get('response'),
          'message_count': len(h.get('messages', [])),
          'messages': h.get('messages', []),
        }
        for h in handoffs
      ],
    }

    return {
      'trace_id': trace_id,
      'deployment_type': 'agent-bricks-mas',
      'duration_ms': 0,  # Not available from stream
      'status': 'completed',
      'function_calls': function_calls,  # Backward compat with existing trace display
      'mas_flow': mas_flow,  # MAS-specific hierarchical structure
      'tools_called': [],
      'retrieval_calls': [],
      'llm_calls': [],
    }

  def invoke(
    self, messages: List[Dict[str, str]], client_request_id: str, request: Request
  ) -> Dict[str, Any]:
    """Non-streaming invocation not yet implemented for MAS.

    Args:
      messages: List of messages with 'role' and 'content' keys
      client_request_id: Unique ID for trace linking
      request: FastAPI Request object (for auth headers)

    Returns:
      Error message indicating streaming is required

    Raises:
      NotImplementedError: MAS requires streaming mode
    """
    raise NotImplementedError(
      'Agent Bricks MAS requires streaming mode. '
      'Please use invoke_stream() or enable streaming on the frontend.'
    )

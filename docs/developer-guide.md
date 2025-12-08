# Developer Guide

Architecture deep dive and extension guide for the Databricks GenAI App Template.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Handler Pattern](#handler-pattern)
- [Authentication Strategies](#authentication-strategies)
- [Adding a New Deployment Type](#adding-a-new-deployment-type)
- [Customizing the Agent](#customizing-the-agent)
- [Frontend Customization](#frontend-customization)
- [Code Organization](#code-organization)
- [Development Best Practices](#development-best-practices)

## Architecture Overview

### Core Design Principles

The template is built around these principles:

1. **Extensibility** - Support multiple agent deployment types via handler pattern
2. **Separation of Concerns** - Auth, routing, and deployment logic cleanly separated
3. **Type Safety** - TypeScript frontend, Python type hints, auto-generated API client
4. **Developer Experience** - Hot reload, clear error messages, comprehensive logging
5. **Production Ready** - User authentication, tracing, feedback collection built-in

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                           │
│                                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Components  │  │   Contexts   │  │  Auto-generated API    │ │
│  │ (React)     │  │   (State)    │  │  Client (TypeScript)   │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
│         │                  │                      │              │
└─────────┼──────────────────┼──────────────────────┼──────────────┘
          │                  │                      │
          └──────────────────▼──────────────────────┘
                             │ HTTP/SSE
┌────────────────────────────▼─────────────────────────────────────┐
│                         Backend Layer                             │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                     Router Layer                            │ │
│  │  • Request validation (Pydantic)                           │ │
│  │  • MLflow trace creation                                   │ │
│  │  • Handler selection                                       │ │
│  │  • Response streaming                                      │ │
│  └──────────────────┬─────────────────────────────────────────┘ │
│                     │                                            │
│  ┌──────────────────▼──────────────────────────────────────────┐ │
│  │                Authentication Layer                          │ │
│  │  Strategy Pattern:                                          │ │
│  │  • HttpTokenAuth      → (host, token) for HTTP calls       │ │
│  │  • WorkspaceClientAuth → WorkspaceClient for SDK           │ │
│  └──────────────────┬──────────────────────────────────────────┘ │
│                     │                                            │
│  ┌──────────────────▼──────────────────────────────────────────┐ │
│  │                  Handler Layer                               │ │
│  │  Pluggable handlers (registry pattern):                    │ │
│  │  • DatabricksEndpointHandler (current)                     │ │
│  │  • LocalAgentHandler (future)                              │ │
│  │  • OpenAIHandler (future)                                  │ │
│  └──────────────────┬──────────────────────────────────────────┘ │
│                     │                                            │
└─────────────────────┼────────────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────────────┐
│                    External Services                              │
│  • Databricks Model Serving                                      │
│  • Unity Catalog                                                 │
│  • MLflow Experiments                                            │
│  • Vector Search (future)                                        │
└───────────────────────────────────────────────────────────────────┘
```

### Request Lifecycle

**Detailed flow for a user message:**

```
1. User types message in ChatInput component
   ↓
2. Frontend: sendMessage() in ChatView.tsx
   ↓
3. Frontend: Create AbortController for stream cancellation
   ↓
4. Frontend: POST /api/invoke_endpoint
   {
     "agent_id": "databricks-agent-01",
     "messages": [{"role": "user", "content": "..."}],
     "stream": true
   }
   ↓
5. Backend: FastAPI router receives request (agent.py:271)
   ↓
6. Backend: Generate client_request_id = "req-abc123def456"
   ↓
7. Backend: Create MLflow trace with client_request_id tag (agent.py:306-326)
   ↓
8. Backend: Load agent config from agents.json
   ↓
9. Backend: Select handler based on deployment_type (agent.py:332)
   ↓
10. Backend: Instantiate handler with auth strategy (agent.py:346)
    ↓
11. Backend: Call handler.invoke_stream() (agent.py:351)
    ↓
12. Handler: Get credentials via auth_strategy.get_credentials(request)
    ↓
13. Handler: Call agent endpoint with streaming (databricks_endpoint.py:76)
    ↓
14. Handler: Emit client_request_id as first SSE event (databricks_endpoint.py:56)
    ↓
15. Handler: Stream response chunks as SSE events
    ↓
16. Frontend: Receive SSE events in stream reader (ChatView.tsx:334-706)
    ↓
17. Frontend: Parse events and update UI:
    - text deltas → append to message content
    - function_call → add to activeFunctionCalls
    - function_call_output → merge with matching call
    - trace.summary → store trace metadata
    ↓
18. Frontend: Display final message with trace data
    ↓
19. Backend: Save messages to chat storage (chat.py:84-94)
    ↓
20. MLflow: Trace and feedback available for later retrieval
```

## Handler Pattern

The handler pattern enables support for different agent deployment types without changing core routing logic.

### Handler Interface

All handlers implement `BaseDeploymentHandler`:

```python
# server/agents/handlers/base.py

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List
from fastapi import Request
from ...auth.strategies import AuthStrategy

class BaseDeploymentHandler(ABC):
    """Base class for agent deployment handlers.

    Each deployment type (databricks-endpoint, local-agent, etc.) implements
    this interface with deployment-specific logic.
    """

    def __init__(self, agent_config: Dict[str, Any], auth_strategy: AuthStrategy):
        """Initialize handler with config and auth strategy.

        Args:
            agent_config: Agent configuration from agents.json
            auth_strategy: Authentication strategy for this deployment type
        """
        self.agent_config = agent_config
        self.auth_strategy = auth_strategy

    @abstractmethod
    async def invoke_stream(
        self,
        messages: List[Dict[str, str]],
        client_request_id: str,
        request: Request
    ) -> AsyncGenerator[str, None]:
        """Stream response from agent.

        Args:
            messages: Conversation history
            client_request_id: Unique ID for trace linking
            request: FastAPI Request (for auth headers)

        Yields:
            SSE-formatted strings with JSON data
        """
        pass

    @abstractmethod
    def invoke(
        self,
        messages: List[Dict[str, str]],
        client_request_id: str,
        request: Request
    ) -> Dict[str, Any]:
        """Non-streaming invocation.

        Args:
            messages: Conversation history
            client_request_id: Unique ID for trace linking
            request: FastAPI Request (for auth headers)

        Returns:
            OpenAI-compatible response format
        """
        pass
```

### Handler Registry

Handlers are registered in a central dictionary:

```python
# server/routers/agent.py

from ..agents.handlers import BaseDeploymentHandler, DatabricksEndpointHandler

DEPLOYMENT_HANDLERS: dict[str, Type[BaseDeploymentHandler]] = {
    'databricks-endpoint': DatabricksEndpointHandler,
    # Future handlers:
    # 'local-agent': LocalAgentHandler,
    # 'openai-compatible': OpenAIHandler,
    # 'custom-api': CustomAPIHandler,
}
```

### Current Implementation: DatabricksEndpointHandler

Handles Databricks Model Serving endpoints:

```python
# server/agents/handlers/databricks_endpoint.py

class DatabricksEndpointHandler(BaseDeploymentHandler):
    """Handler for Databricks model serving endpoints."""

    def __init__(self, agent_config: Dict[str, Any]):
        # Use HttpTokenAuth for calling HTTP endpoints
        super().__init__(agent_config, auth_strategy=HttpTokenAuth())
        self.endpoint_name = agent_config.get('endpoint_name')

    async def invoke_stream(self, messages, client_request_id, request):
        # Get credentials: (host, token)
        host, token = self.auth_strategy.get_credentials(request)

        # Build request
        url = f'{host}/serving-endpoints/{self.endpoint_name}/invocations'
        headers = {'Authorization': f'Bearer {token}'}
        payload = {'input': messages, 'stream': True}

        # Emit client_request_id first
        yield f'data: {json.dumps({"type": "trace.client_request_id", "client_request_id": client_request_id})}\\n\\n'

        # Stream from Databricks
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream('POST', url, json=payload, headers=headers) as response:
                async for line in response.aiter_lines():
                    # Forward SSE events to frontend
                    yield f'data: {line}\\n\\n'
```

**Key aspects:**
- Uses `HttpTokenAuth` strategy (returns host and token)
- Formats requests in Databricks Agent API format
- Handles SSE streaming protocol
- Emits `client_request_id` first for frontend to capture
- Forwards events from Databricks to frontend

## Authentication Strategies

Authentication uses the Strategy Pattern to handle different credential types.

### Strategy Interface

```python
# server/auth/strategies.py

from abc import ABC, abstractmethod
from fastapi import Request

class AuthStrategy(ABC):
    """Base class for authentication strategies."""

    @abstractmethod
    def get_credentials(self, request: Request):
        """Get credentials for this deployment type.

        Args:
            request: FastAPI Request object (provides access to headers)

        Returns:
            Credentials in the format needed by the deployment type
        """
        pass
```

### HttpTokenAuth Strategy

For calling external HTTP endpoints:

```python
class HttpTokenAuth(AuthStrategy):
    """Authentication for external HTTP endpoints.

    Returns (host, token) tuple for use in Authorization: Bearer headers.
    """

    def get_credentials(self, request: Request) -> Tuple[str, str]:
        host = get_databricks_host()

        if is_local_development():
            # Dev: Use PAT from environment
            token = get_dev_token()  # Reads DATABRICKS_TOKEN
        else:
            # Prod: Use user's forwarded token
            token = get_user_token_from_request(request)  # x-forwarded-access-token header

        return host, token
```

**Use cases:**
- Calling Databricks Model Serving endpoints
- Calling external APIs
- Any HTTP-based agent invocation

### WorkspaceClientAuth Strategy

For local agents using Databricks SDK:

```python
from databricks.sdk import WorkspaceClient

class WorkspaceClientAuth(AuthStrategy):
    """Authentication for local agents using Databricks SDK.

    Returns configured WorkspaceClient instance.
    """

    def get_credentials(self, request: Request) -> WorkspaceClient:
        host = get_databricks_host()

        if is_local_development():
            # Dev: Create client with PAT
            token = get_dev_token()
            workspace_client = WorkspaceClient(host=host, token=token, auth_type='pat')
        else:
            # Prod: Create client with user's token
            token = get_user_token_from_request(request)
            workspace_client = WorkspaceClient(host=host, token=token, auth_type='pat')

        return workspace_client
```

**Use cases:**
- Running agents in-process (not via HTTP endpoint)
- Accessing Unity Catalog directly
- Vector Search operations
- SQL queries via SDK
- Any operation requiring Databricks SDK

### Core Authentication Utilities

Located in `server/auth/databricks_auth.py`:

```python
def is_local_development() -> bool:
    """Check if running in local dev mode."""
    return os.getenv('ENV', 'production') == 'development'

def get_databricks_host() -> str:
    """Get Databricks workspace host from environment."""
    host = os.getenv('DATABRICKS_HOST', '')
    if not host:
        raise ValueError('DATABRICKS_HOST must be set')
    if not host.startswith('https://'):
        host = f'https://{host}'
    return host

def get_user_token_from_request(request: Request) -> str:
    """Extract user token from Databricks Apps headers."""
    token = request.headers.get('x-forwarded-access-token')
    if not token:
        raise ValueError('No X-Forwarded-Access-Token header found')
    return token

def get_dev_token() -> str:
    """Get PAT token for local development."""
    token = os.getenv('DATABRICKS_TOKEN', '')
    if not token:
        raise ValueError('DATABRICKS_TOKEN must be set for development')
    return token
```

## Adding a New Deployment Type

Let's walk through adding support for OpenAI-compatible endpoints.

### Step 1: Create Handler Class

Create `server/agents/handlers/openai_handler.py`:

```python
"""Handler for OpenAI-compatible chat completion endpoints."""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List

import httpx
from fastapi import Request

from ...auth.strategies import AuthStrategy
from .base import BaseDeploymentHandler

logger = logging.getLogger(__name__)


class OpenAIHandler(BaseDeploymentHandler):
    """Handler for OpenAI-compatible endpoints (OpenAI, Azure OpenAI, etc.)."""

    def __init__(self, agent_config: Dict[str, Any]):
        # Create custom auth strategy for API key
        auth_strategy = OpenAIAuthStrategy(agent_config)
        super().__init__(agent_config, auth_strategy=auth_strategy)

        self.api_base = agent_config.get('api_base', 'https://api.openai.com/v1')
        self.model = agent_config.get('model', 'gpt-4')
        self.max_tokens = agent_config.get('max_tokens', 4096)

    async def invoke_stream(
        self,
        messages: List[Dict[str, str]],
        client_request_id: str,
        request: Request
    ) -> AsyncGenerator[str, None]:
        """Stream response from OpenAI-compatible endpoint."""

        # Emit client_request_id first
        logger.info(f'Emitting client_request_id: {client_request_id}')
        trace_event = {
            'type': 'trace.client_request_id',
            'client_request_id': client_request_id
        }
        yield f'data: {json.dumps(trace_event)}\\n\\n'

        # Get API key via auth strategy
        api_key = self.auth_strategy.get_credentials(request)

        # Build OpenAI API request
        url = f'{self.api_base}/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            'model': self.model,
            'messages': messages,
            'max_tokens': self.max_tokens,
            'stream': True
        }

        logger.info(f'Calling OpenAI API: {url}')

        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream('POST', url, json=payload, headers=headers) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line or not line.strip():
                        continue

                    # OpenAI SSE format: "data: {...}"
                    if line.startswith('data: '):
                        data_str = line[6:]

                        if data_str == '[DONE]':
                            yield 'data: [DONE]\\n\\n'
                            continue

                        try:
                            chunk = json.loads(data_str)

                            # Convert OpenAI format to our format
                            if 'choices' in chunk and len(chunk['choices']) > 0:
                                delta = chunk['choices'][0].get('delta', {})
                                content = delta.get('content', '')

                                if content:
                                    our_event = {
                                        'type': 'response.output_item.content_part.delta',
                                        'delta': {'text': content}
                                    }
                                    yield f'data: {json.dumps(our_event)}\\n\\n'

                        except json.JSONDecodeError as e:
                            logger.warning(f'Failed to parse OpenAI response: {e}')
                            continue

    def invoke(
        self,
        messages: List[Dict[str, str]],
        client_request_id: str,
        request: Request
    ) -> Dict[str, Any]:
        """Non-streaming invocation."""
        # Similar to invoke_stream but without streaming
        # Return OpenAI-compatible response
        pass


# Custom auth strategy for API key
class OpenAIAuthStrategy(AuthStrategy):
    """Authentication strategy for OpenAI API keys."""

    def __init__(self, agent_config: Dict[str, Any]):
        self.api_key = agent_config.get('api_key')
        if not self.api_key:
            raise ValueError('OpenAI handler requires api_key in agent config')

    def get_credentials(self, request: Request) -> str:
        """Return API key."""
        return self.api_key
```

### Step 2: Register Handler

Update `server/routers/agent.py`:

```python
from ..agents.handlers import (
    BaseDeploymentHandler,
    DatabricksEndpointHandler,
)
from ..agents.handlers.openai_handler import OpenAIHandler  # Add import

DEPLOYMENT_HANDLERS: dict[str, Type[BaseDeploymentHandler]] = {
    'databricks-endpoint': DatabricksEndpointHandler,
    'openai-compatible': OpenAIHandler,  # Add to registry
}
```

### Step 3: Configure Agent

Update `config/agents.json`:

```json
{
  "agents": [
    {
      "id": "openai-gpt4",
      "displayName": "GPT-4",
      "description": "OpenAI GPT-4 model",
      "deployment_type": "openai-compatible",
      "api_base": "https://api.openai.com/v1",
      "api_key": "sk-...",
      "model": "gpt-4",
      "max_tokens": 4096,
      "mlflow_experiment_id": "1234567890"
    }
  ]
}
```

**Security note:** For production, use environment variables for API keys instead of config files:

```python
class OpenAIAuthStrategy(AuthStrategy):
    def __init__(self, agent_config: Dict[str, Any]):
        # Try config first, then environment
        self.api_key = agent_config.get('api_key') or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError('OpenAI API key not found in config or environment')
```

### Step 4: Test

```bash
# Start dev server
./watch.sh

# Test in UI or via curl
curl -X POST http://localhost:8000/api/invoke_endpoint \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "openai-gpt4",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

## Customizing the Agent

### Adding Tools to LangChain Agent

Edit `server/agents/databricks_assistant/tools.py`:

```python
from langchain_core.tools import tool
from databricks.sdk import WorkspaceClient

@tool
def query_unity_catalog(catalog: str, schema: str) -> str:
    """Query Unity Catalog for tables in a schema.

    Args:
        catalog: The catalog name
        schema: The schema name

    Returns:
        List of tables in the schema
    """
    workspace_client = WorkspaceClient()
    tables = workspace_client.tables.list(
        catalog_name=catalog,
        schema_name=schema
    )
    return f"Tables: {[t.name for t in tables]}"


@tool
def get_table_schema(catalog: str, schema: str, table: str) -> str:
    """Get schema information for a Unity Catalog table.

    Args:
        catalog: The catalog name
        schema: The schema name
        table: The table name

    Returns:
        Table schema as string
    """
    workspace_client = WorkspaceClient()
    table_info = workspace_client.tables.get(
        full_name=f"{catalog}.{schema}.{table}"
    )

    columns = []
    for col in table_info.columns:
        columns.append(f"  {col.name}: {col.type_name}")

    return f"Schema for {catalog}.{schema}.{table}:\\n" + "\\n".join(columns)
```

**Tool best practices:**
- Clear docstrings (LLM reads these to understand tool usage)
- Type hints for parameters
- Validate inputs before executing
- Handle errors gracefully
- Return string results (not complex objects)

### Modifying Agent Configuration

Edit `server/agents/databricks_assistant/agent.py`:

```python
from langchain_databricks import ChatDatabricks
from langgraph.prebuilt import create_react_agent

from .tools import query_unity_catalog, get_table_schema, list_catalogs

def create_agent():
    """Create LangChain agent with Unity Catalog tools."""

    # Configure LLM
    llm = ChatDatabricks(
        endpoint="databricks-meta-llama-3-1-70b-instruct",
        temperature=0.1,
        max_tokens=4096
    )

    # Configure tools
    tools = [
        list_catalogs,
        query_unity_catalog,
        get_table_schema,
    ]

    # Create agent
    agent = create_react_agent(
        llm,
        tools=tools,
        state_modifier="You are a helpful assistant that helps users explore and query Unity Catalog. "
                       "Use the provided tools to answer questions about catalogs, schemas, and tables."
    )

    return agent
```

## Frontend Customization

### Adding shadcn/ui Components

```bash
# Navigate to client directory
cd client

# Add a component (e.g., dialog)
bunx --bun shadcn@latest add dialog

# Add multiple components
bunx --bun shadcn@latest add dialog dropdown-menu tabs
```

Components are added to `client/components/ui/`.

### Creating Custom Components

Example: Add a custom chart component

```typescript
// client/components/charts/CustomBarChart.tsx

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

interface CustomBarChartProps {
  data: Array<{ name: string; value: number }>;
  title?: string;
}

export function CustomBarChart({ data, title }: CustomBarChartProps) {
  return (
    <div className="w-full p-4">
      {title && <h3 className="text-lg font-semibold mb-4">{title}</h3>}
      <BarChart width={600} height={300} data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="value" fill="#FF3621" />
      </BarChart>
    </div>
  );
}
```

### Styling with Tailwind

The project uses Tailwind CSS. Configure in `client/tailwind.config.ts`:

```typescript
export default {
  theme: {
    extend: {
      colors: {
        'databricks-orange': '#FF3621',
        'databricks-dark': '#1B1B1B',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
```

## Code Organization

### Backend Structure

```
server/
├── agents/
│   ├── handlers/
│   │   ├── __init__.py              # Export handlers
│   │   ├── base.py                  # BaseDeploymentHandler interface
│   │   └── databricks_endpoint.py   # Databricks handler
│   └── databricks_assistant/
│       ├── __init__.py
│       ├── agent.py                 # LangChain agent definition
│       └── tools.py                 # LangChain tools
├── auth/
│   ├── __init__.py                  # Export auth utilities
│   ├── databricks_auth.py           # Core auth functions
│   └── strategies.py                # Auth strategies
├── routers/
│   ├── __init__.py
│   ├── agent.py                     # Agent invocation + feedback
│   └── chat.py                      # Chat storage endpoints
├── app.py                           # FastAPI app + static serving
├── chat_storage.py                  # In-memory chat storage
└── config_loader.py                 # Load config/*.json files
```

### Frontend Structure

```
client/
├── app/
│   ├── layout.tsx                   # Root layout
│   ├── page.tsx                     # Main chat page
│   └── about/
│       └── page.tsx                 # About page
├── components/
│   ├── chat/
│   │   ├── ChatView.tsx            # Main chat component
│   │   ├── ChatInput.tsx           # Message input
│   │   ├── MessageList.tsx         # Message rendering
│   │   └── MarkdownRenderer.tsx    # Markdown display
│   ├── layout/
│   │   ├── TopBar.tsx              # Navigation bar
│   │   ├── Sidebar.tsx             # Chat history sidebar
│   │   └── MainContent.tsx         # Content wrapper
│   ├── modals/
│   │   ├── TraceModal.tsx          # Trace viewer
│   │   └── FeedbackModal.tsx       # Feedback collection
│   └── ui/                          # shadcn/ui components
├── lib/
│   ├── types.ts                     # TypeScript types
│   ├── api.ts                       # API client wrapper
│   └── utils.ts                     # Utility functions
└── contexts/
    └── ChatContext.tsx              # Global chat state
```

## Development Best Practices

### Code Quality

**Always run before committing:**
```bash
./fix.sh    # Format code
./check.sh  # Run linting
```

**Python code style:**
- Use type hints for all function signatures
- Docstrings for all public functions
- Follow ruff configuration (configured in pyproject.toml)

**TypeScript code style:**
- Use interfaces for component props
- Avoid `any` type
- Use const for immutable values

### Logging

**Backend logging:**
```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate levels
logger.info("Starting agent invocation")
logger.warning("Unusual condition detected")
logger.error("Failed to connect to endpoint")
```

**Frontend logging:**
```typescript
// Use devLog() for development logging (auto-disabled in production)
import { devLog } from '@/lib/utils';

devLog('📡 Sending message to agent');
devLog('🌊 Streaming event received', event);
```

### Error Handling

**Backend:**
```python
from fastapi import HTTPException

try:
    result = handler.invoke(messages)
except ValueError as e:
    logger.error(f"Validation error: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

**Frontend:**
```typescript
try {
  const response = await fetch('/api/endpoint');
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
} catch (error) {
  console.error('API call failed:', error);
  setError('Failed to send message. Please try again.');
}
```

### Testing

**Test agent without UI:**
```bash
./test_agent.sh
```

**Test specific endpoints:**
```bash
# Test health endpoint
curl http://localhost:8000/api/health

# Test agent invocation
curl -X POST http://localhost:8000/api/invoke_endpoint \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "databricks-agent-01",
    "messages": [{"role": "user", "content": "test"}],
    "stream": false
  }'
```

### Hot Reload Workflow

1. **Start dev servers:** `./watch.sh`
2. **Make changes:**
   - Backend: Edit Python files → uvicorn auto-reloads
   - Frontend: Edit React files → Vite hot-reloads
3. **Test immediately** in browser
4. **Check logs** in terminal for errors
5. **Format code** before committing: `./fix.sh`

---

**Next Steps:**
- See [User Guide](user-guide.md) for setup and deployment
- See [Feature Documentation](features/) for specific features
- Check [TODO.md](TODO.md) for planned enhancements

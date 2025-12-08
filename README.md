# Databricks GenAI App Template

A comprehensive app template for deploying AI agents with Databricks. 
Features extensible agent deployment patterns (through Databricks Serving Endpoint, Agent Bricks Endpoint or local agent), MLflow tracing & feedback collection, user authentication, and a modern React chat interface.

![Chat Interface](docs/images/chat-ui.png)

## What is this?

This template bridges the gap between prototype AI agents and production-ready applications. It provides:

- **Extensible deployment architecture** - Support multiple agent types (Databricks endpoints, local agents, Agent Bricks agents)
- **Production authentication** - User token forwarding with on-behalf-of-user permissions
- **Built-in observability** - MLflow tracing and user feedback collection
- **Modern development experience** - Hot reload, TypeScript, component library
- **Multiple deployment targets** - Local development, Databricks Apps

## Key Features

- **Handler Pattern** - Pluggable deployment handlers for different agent types
- **Authentication Strategies** - Flexible auth for HTTP endpoints and SDK-based agents
- **MLflow Integration** - Request tracing, feedback collection, experiment tracking
- **Chat Storage** - Session management with conversation history
- **Streaming Responses** - Real-time Server-Sent Events with trace linking
- **Rich UI** - Markdown rendering, code highlighting, chart visualization, trace viewing, easy customization of look&feel of the app

## Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                      │
│  React + shadcn/ui + Tailwind │ Static export served by FastAPI │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTP/SSE
┌────────────────────▼────────────────────────────────────────────┐
│                    Backend (FastAPI)                            │
│  ┌────────────┐    ┌──────────────┐    ┌─────────────────────┐  │
│  │  Router    │───▶│ Handler      │───▶│ Auth Strategy       │  │
│  │  (agent.py)│    │ Selection    │    │ - HttpTokenAuth     │  │
│  └────────────┘    └──────┬───────┘    │ - WorkspaceClient   │  │
│                           │            └─────────────────────┘  │
│              ┌────────────▼──────────────┐                      │
│              │  Deployment Handlers      │                      │
│              │  - DatabricksEndpoint     │                      │
│              │  - LocalAgent (future)    │                      │
│              │  - OpenAI (future)        │                      │
│              └───────────────────────────┘                      │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                 Databricks Platform                             │
│  Model Serving │ Unity Catalog │ MLflow │ Vector Search │ (...) │
└─────────────────────────────────────────────────────────────────┘
```

### Deployment Flexibility

The handler pattern enables support for multiple agent deployment types:

```python
# Current: Databricks Model Serving endpoints
'databricks-endpoint': DatabricksEndpointHandler

# Future (TODO): Agent Bricks - Muti-Agent Supervisor
'agent-bricks-mas': AgentBricksMASHandler

# Future (TODO): OpenAI-compatible endpoints
'openai-compatible': OpenAIHandler

# Future (TODO): In-process agents using Databricks SDK
'local-agent': LocalAgentHandler
```

Each handler implements the same interface but handles deployment-specific logic:
- Request/response formatting
- Authentication credentials
- Streaming protocols (if available / possible)
- Error handling

**Code location:** `server/agents/handlers/`

### Authentication Strategy

Authentication uses the Strategy Pattern to support different credential types:

**HttpTokenAuth** - For calling external HTTP endpoints (current use):
- Dev: Uses PAT from `DATABRICKS_TOKEN` environment variable
- Prod: Uses user's forwarded token from `x-forwarded-access-token` header
- Returns `(host, token)` tuple for Authorization headers

**WorkspaceClientAuth** - For local agents using Databricks SDK (future):
- Dev: Creates WorkspaceClient with PAT token
- Prod: Creates WorkspaceClient with user's forwarded token
- Returns configured `WorkspaceClient` instance
- Enables Unity Catalog, Vector Search, SQL operations

**Benefits:**
- Maintains user-level permissions and audit trails
- Zero code duplication between deployment types
- Easy to extend with new strategies (API keys, OAuth, service principals)

**Code location:** `server/auth/`

### Request Flow

```
1. User sends message
   ↓
2. POST /api/invoke_endpoint
   ↓
3. Create MLflow trace (client_request_id)
   ↓
4. Select handler based on deployment_type
   ↓
5. Get credentials via auth strategy
   ↓
6. Stream response from agent
   ↓
7. Frontend collects trace data
   ↓
8. Save messages + feedback linking
```

## Quick Start

```bash
# Clone repository
git clone https://github.com/databricks-solutions/databricks-genai-app-template.git
cd databricks-genai-app-template

# Install dependencies (requires uv and npm)
./scripts/setup.sh

# Start development servers
./scripts/start_dev.sh
```

Open **http://localhost:3000** for the frontend (backend runs on http://localhost:8000)

**Prerequisites:** Python 3.12+, Node.js 18+, Databricks workspace with Unity Catalog

See [User Guide](docs/user-guide.md) for complete setup instructions.

## Development

```bash
./scripts/start_dev.sh  # Start both FastAPI (8000) and Next.js (3000)
./scripts/fix.sh        # Format code (ruff + prettier)
./scripts/check.sh      # Run linting and type checks
```

**Development workflow:**
- Backend changes: Edit Python files → uvicorn auto-reloads
- Frontend changes: Edit React/TypeScript files → Next.js hot-reloads
- Configuration: Edit `config/*.json` files → refresh browser

## Deployment

```bash
./scripts/deploy.sh
```

Deploys to Databricks Apps with:
- Local frontend build (Next.js static export)
- Databricks sync via `.databricksignore`
- Environment configuration from `app.yaml`

See [User Guide - Databricks Apps Deployment](docs/user-guide.md#databricks-apps-deployment) for details.

## Documentation

### Guides

- **[User Guide](docs/user-guide.md)** - Setup, configuration, local development, Databricks deployment
- **[Developer Guide](docs/developer-guide.md)** - Architecture deep dive, adding handlers, customization

### Features

- **[MLflow Tracing](docs/features/tracing.md)** - Client-side trace display, function call tracking
- **[Chat Storage](docs/features/chat-storage.md)** - In-memory session management (10 chat limit)
- **[Session Management](docs/features/session-management.md)** - Stream handling, chat switching behavior

### Configuration

- **Environment Variables** - See `env.template` for all available options
- **Agent Configuration** - `config/agents.json` - Define agents and their endpoints
- **App Branding** - `config/app.json` - App name, logo, theme
- **About Page** - `config/about.json` - About page content (Markdown supported)

### Reference

- **[TODO](docs/TODO.md)** - Planned enhancements (persistent storage, background processing)

## Project Structure

```
databricks-genai-app-template/
├── server/                     # FastAPI backend
│   ├── agents/
│   │   ├── handlers/          # Deployment-specific handlers
│   │   └── databricks_assistant/  # Example LangChain agent
│   ├── auth/                  # Authentication strategies
│   ├── routers/               # API endpoints
│   ├── app.py                 # FastAPI app
│   └── chat_storage.py        # In-memory chat storage
├── client/                    # Next.js frontend
│   ├── app/                   # Next.js pages
│   ├── components/            # React components
│   ├── lib/                   # Utilities and types
│   └── contexts/              # React contexts
├── config/                    # Configuration files
│   ├── agents.json           # Agent definitions
│   ├── app.json              # App branding
│   └── about.json            # About page content
├── scripts/                   # Build and deployment scripts
├── docs/                      # Documentation
└── app.yaml                   # Databricks Apps config
```

## Customization

### Add Agent Tools

Add custom tools to the LangChain agent in `server/agents/databricks_assistant/tools.py`:

```python
from langchain_core.tools import tool

@tool
def my_custom_tool(param: str) -> str:
    """Tool description for the LLM."""
    # Your implementation
    return result
```

### Customize UI

Add shadcn/ui components:

```bash
cd client
npx shadcn@latest add dialog
```

Components use [shadcn/ui](https://ui.shadcn.com/) with Tailwind CSS. See `client/tailwind.config.ts` for theme customization.

### Extend Deployment Types

Add handlers for new agent types (OpenAI, local agents, etc.). See [Developer Guide](docs/developer-guide.md#adding-a-new-deployment-type) for step-by-step instructions.

## Known Limitations

- **Chat storage is in-memory** - All chats lost on server restart. See [TODO.md](docs/TODO.md) for persistence plans.
- **Maximum 10 chats** - Oldest chat auto-deleted when limit reached.
- **Single-response-at-a-time** - Cannot switch chats during streaming. See [TODO.md](docs/TODO.md) for background processing plans.
- **No message edit/delete** - Append-only message model.

## Troubleshooting

**Port conflicts:**
```bash
lsof -i :8000    # Check backend port
lsof -i :3000    # Check frontend port
pkill -f uvicorn # Kill FastAPI server
pkill -f next    # Kill Next.js dev server
```

**Authentication errors:**
- **Local dev**: Verify `DATABRICKS_HOST` and `DATABRICKS_TOKEN` in `.env.local`
- **Production**: Check `app.yaml` has correct `DATABRICKS_HOST`
- Check server logs for specific error messages

**Agent not found errors:**
- Verify `config/agents.json` has correct `endpoint_name`
- Check endpoint exists: `databricks serving-endpoints list`
- Ensure endpoint is in `READY` state

**Databricks Apps deployment fails:**
- Check `databricks apps list` for app status
- View logs at `{app-url}/logz` (requires OAuth authentication)
- Review `./scripts/deploy.sh` output for errors

**Build failures:**
- Frontend: `cd client && npm run build`
- Backend: `uv sync` to update dependencies
- Run `./scripts/fix.sh` to fix formatting issues

## Contributing

Before submitting pull requests:

```bash
./scripts/fix.sh    # Format code (ruff + prettier)
./scripts/check.sh  # Run linting and type checks
```

## Support

Databricks support doesn't cover this content. For questions or bugs, please open a [GitHub issue](https://github.com/databricks-solutions/databricks-genai-app-template/issues).

## License

© 2025 Databricks, Inc. All rights reserved. The source in this notebook is provided subject to the [Databricks License](https://databricks.com/db-license-source). All included or referenced third party libraries are subject to the licenses set forth below.

| library      | description                         | license    | source                                      |
| ------------ | ----------------------------------- | ---------- | ------------------------------------------- |
| FastAPI      | Modern web framework for APIs       | MIT        | https://github.com/tiangolo/fastapi         |
| React        | JavaScript library for UIs          | MIT        | https://github.com/facebook/react           |
| Next.js      | React framework                     | MIT        | https://github.com/vercel/next.js           |
| LangChain    | Framework for LLM applications      | MIT        | https://github.com/langchain-ai/langchain   |
| MLflow       | Machine learning lifecycle platform | Apache 2.0 | https://github.com/mlflow/mlflow            |
| shadcn/ui    | Re-usable components                | MIT        | https://github.com/shadcn-ui/ui             |
| Tailwind CSS | Utility-first CSS framework         | MIT        | https://github.com/tailwindlabs/tailwindcss |
| Recharts     | Composable charting library         | MIT        | https://github.com/recharts/recharts        |

---

**Built by Databricks Solutions Team**

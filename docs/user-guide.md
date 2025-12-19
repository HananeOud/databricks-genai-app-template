# User Guide

Complete guide to setting up, configuring, and deploying the Databricks GenAI App Template.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Configuration](#configuration)
- [Running Locally](#running-locally)
- [Databricks Apps Deployment](#databricks-apps-deployment)
- [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)

## Prerequisites

### Required Software

- **Python 3.11+** with [uv](https://github.com/astral-sh/uv) package manager
- **[Bun](https://bun.sh/)** for frontend package management
- **Git** for version control

### Databricks Requirements

- Databricks workspace (AWS, Azure, or GCP)
- Unity Catalog enabled
- Model Serving endpoint deployed with your agent
- Personal Access Token (PAT) for local development

### Access & Permissions

**For local development:**
- Personal Access Token (PAT) with workspace access
- Permissions to call your Model Serving endpoint

**For Databricks Apps deployment:**
- Permission to create and manage Databricks Apps
- Permission to sync files to workspace
- Model Serving endpoint must be accessible from Databricks Apps

## Local Development Setup

### 1. Install Dependencies

**macOS:**
```bash
# Install uv (Python package manager)
brew install uv

# Install bun
brew install oven-sh/bun/bun
```

**Linux:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install bun
curl -fsSL https://bun.sh/install | bash
```

**Windows:**
```powershell
# Install uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install bun
powershell -c "irm bun.sh/install.ps1|iex"
```

### 2. Clone Repository

```bash
git clone https://github.com/databricks-solutions/databricks-genai-app-template.git
cd databricks-genai-app-template
```

### 3. Run Setup Script

```bash
./scripts/setup.sh
```

**What this script does:**

1. **Creates `.env.local`** with prompts for:
   - `DATABRICKS_HOST` - Your Databricks workspace URL (e.g., https://adb-123456789.azuredatabricks.net)
   - `DATABRICKS_TOKEN` - Your Personal Access Token
   - `DATABRICKS_APP_NAME` - (Optional) For deployment
   - `WORKSPACE_SOURCE_PATH` - (Optional) For deployment

2. **Installs Python dependencies:**
   - Runs `uv sync` to create `.venv/` and install backend dependencies

3. **Installs frontend dependencies:**
   - Runs `bun install` in the `client/` directory

**Output:**
```
✅ .env.local created
✅ Python dependencies installed (.venv/ created)
✅ Frontend dependencies installed

Next steps:
  1. Run: ./scripts/start_dev.sh
  2. Open: http://localhost:3000
```

## Configuration

### Environment Variables (.env.local)

The `.env.local` file contains your local development configuration:

```bash
# Required for local development
DATABRICKS_HOST=https://adb-123456789.azuredatabricks.net
DATABRICKS_TOKEN=dapi...

# Optional - for deployment
DATABRICKS_APP_NAME=my-genai-app
WORKSPACE_SOURCE_PATH=/Workspace/Users/your.email@company.com/app-template
```

**Important:**
- `.env.local` is in `.gitignore` - DO NOT commit this file
- Contains sensitive credentials (PAT token)
- Only used for local development
- Production uses OAuth (no token needed)

See `.env.template` for complete reference.

### Application Configuration (config/app.json)

This unified config file contains agents, branding, and dashboard settings:

```json
{
  "agents": [
    {
      "endpoint_name": "my-agent-endpoint",
      "display_name": "My Agent",
      "display_description": "Agent description shown in UI",
      "tools": [
        {
          "name": "tool_function_name",
          "display_name": "Tool Name",
          "description": "What this tool does"
        }
      ],
      "mlflow_experiment_id": "1234567890"
    }
  ],
  "branding": {
    "tabTitle": "My App",
    "appName": "My App",
    "companyName": "My Company",
    "description": "AI-powered assistant",
    "logoPath": "/logos/logo.svg"
  },
  "dashboard": {
    "title": "Dashboard",
    "subtitle": "Analytics and insights",
    "iframeUrl": "",
    "showPadding": true
  }
}
```

**Agent fields:**
- `endpoint_name`: Name of your Databricks Model Serving endpoint
- `mlflow_experiment_id`: MLflow experiment ID for tracing (configured here, NOT .env.local)
- `tools`: Optional array of tools displayed in UI

**Branding fields:**
- `tabTitle`: Browser tab title
- `appName`: Application name displayed in UI
- `logoPath`: Path to logo file in `client/public/`

**Dashboard fields:**
- `iframeUrl`: Optional URL to embed external dashboard (e.g., AI/BI Dashboard)
- `showPadding`: Whether to add padding around iframe

### About Page (config/about.json)

The About page displays rich content with sections, images, and call-to-action. Content is structured with:
- **Hero section**: Title and description shown at top
- **Sections array**: Multiple content sections with titles, taglines, highlights, and images
- **CTA section**: Call-to-action button at bottom

Example structure shows Databricks Data Intelligence Platform information with sections on data foundations, analytics, architecture, and use cases. Each section includes an image path (stored in `client/public/images/`) and bullet-point highlights.

To customize: Edit the JSON to replace titles, content, highlights, and image paths with your own content. All content supports standard text formatting.

## Running Locally

### Start Development Servers

```bash
./scripts/start_dev.sh
```

**What this script does:**

1. Loads environment from `.env.local`
2. Activates Python virtual environment
3. Starts **FastAPI backend** on http://localhost:8000 (uvicorn with auto-reload)
4. Starts **Vite frontend** on http://localhost:3000 (with hot reload)

**Access the application:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

**Stop servers:**
Press `Ctrl+C` in the terminal running the script.

### Development Workflow

**Backend changes (Python files):**
- Edit files in `server/`
- uvicorn auto-reloads on save
- Check terminal for logs

**Frontend changes (React/TypeScript):**
- Edit files in `client/`
- Vite hot-reloads instantly
- Changes appear immediately in browser

**Configuration changes:**
- Edit `config/*.json` files
- Refresh browser to see changes
- No server restart needed

### Code Quality

**Format code:**
```bash
./scripts/fix.sh
```
Runs ruff (Python) and prettier (TypeScript/JavaScript).

**Run linting and type checks:**
```bash
./scripts/check.sh
```
Runs ruff check (Python) and TypeScript compiler checks.

## Databricks Apps Deployment

Deploy your application to Databricks Apps for production use.

### Prerequisites

1. **Databricks CLI authenticated:**
   ```bash
   databricks auth login --host https://your-workspace.databricks.net
   ```

2. **Environment configured in `.env.local`:**
   ```bash
   DATABRICKS_HOST=https://your-workspace.databricks.net
   DATABRICKS_TOKEN=dapi...  # For local dev
   DATABRICKS_APP_NAME=my-genai-app
   WORKSPACE_SOURCE_PATH=/Workspace/Users/your.email@company.com/app-template
   ```

3. **Model Serving endpoint deployed:**
   - Agent must be deployed as Databricks Model Serving endpoint
   - Endpoint name configured in `config/agents.json`
   - Endpoint must be in `READY` state

### Deployment Configuration

#### app.yaml

Databricks Apps configuration (in project root):

```yaml
command:
  - "uvicorn"
  - "server.app:app"
  - "--host"
  - "0.0.0.0"

env:
  - name: ENV
    value: production

  - name: DATABRICKS_HOST
    value: "https://your-workspace.databricks.net"
```

**Important:**
- `ENV=production` tells app to use OAuth (not PAT token)
- `DATABRICKS_HOST` must match your workspace
- No secrets in app.yaml (uses OAuth in production)

#### .databricksignore

Controls which files are synced:

```
# Exclude from sync
client/node_modules/
__pycache__/
*.pyc
.env*

# Include build output (explicitly)
!client/out/
```

### Deploy

```bash
./scripts/deploy.sh
```

**Deployment process:**

1. **Generates requirements.txt** from pyproject.toml
2. **Builds frontend:**
   - Runs `bun install`
   - Runs `bun run build`
   - Creates `client/out/` with static files
3. **Syncs to Databricks:**
   - Uses `.databricksignore` for filtering
   - Syncs to `WORKSPACE_SOURCE_PATH`
   - Includes `client/out/` build output
4. **Deploys app:**
   - Creates/updates app with name from `DATABRICKS_APP_NAME`
   - Configures environment from `app.yaml`
5. **Verifies deployment:**
   - Checks app appears in `databricks apps list`


### Post-Deployment Verification

1. **Check app status:**
   ```bash
   databricks apps list
   ```
   Look for your app with status `ACTIVE`.

2. **Access the app:**
   - Go to your Databricks workspace
   - Navigate to **Compute → Apps**
   - Click on your app name
   - You'll be redirected to OAuth login
   - After authentication, app should load

3. **Test functionality:**
   - Send a test message to the agent
   - Verify response streams correctly
   - Check markdown rendering
   - Test thumbs up/down feedback

4. **Monitor logs:**
   - Click "Logs" tab in Databricks Apps UI
   - Or visit `{app-url}/logz` (requires OAuth)
   - Watch for errors during first interactions

### Update Deployment

To update an existing deployment:

```bash
./scripts/deploy.sh
```

The script automatically:
- Detects existing app
- Rebuilds frontend
- Syncs updated code
- Restarts app with new version

**Note:** Chat history will be lost (in-memory storage), but MLflow traces persist.

## Monitoring and Troubleshooting

### Check Application Health

**Health endpoint:**
```bash
curl https://{app-url}/api/health
```

Expected response:
```json
{
  "status": "healthy"
}
```

### View Application Logs

**Production (Databricks Apps):**
- Web UI: Navigate to app in Databricks workspace → Logs tab
- Direct URL: `https://{app-url}/logz` (requires OAuth)
- Shows FastAPI requests, authentication, agent calls, errors

**Local development:**
- Terminal output shows all logs
- Backend: uvicorn logs
- Frontend: Vite console logs


### Getting Help

1. **Check documentation:** Review files in `/docs` folder
2. **Check existing issues:** [GitHub Issues](https://github.com/databricks-solutions/databricks-genai-app-template/issues)
3. **Open new issue:** Include logs, configuration (redact secrets), error messages
4. **Note:** Databricks support doesn't cover this template (community support only)

---

**Next Steps:**
- See [Developer Guide](developer-guide.md) for architecture details and customization
- See [Feature Documentation](features/) for specific feature details
- Check [Limitations & Roadmap](limitations-and-roadmap.md) for planned enhancements

# User Guide

Complete guide to setting up, configuring, and deploying the Databricks GenAI App Template.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Configuration](#configuration)
- [Running Locally](#running-locally)
- [Testing](#testing)
- [Databricks Apps Deployment](#databricks-apps-deployment)
- [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)

## Prerequisites

### Required Software

- **Python 3.12+** with [uv](https://github.com/astral-sh/uv) package manager
- **Bun** for frontend development (faster than npm/yarn)
- **Git** for version control

### Databricks Requirements

- Databricks workspace (AWS, Azure, or GCP)
- Unity Catalog enabled
- Model Serving endpoint (for agent deployment)
- MLflow experiment (can be auto-created)

### Access & Permissions

**For local development:**
- Personal Access Token (PAT) with workspace access
- Permissions to access Unity Catalog
- Permissions to read/write MLflow experiments

**For Databricks Apps deployment:**
- Permission to create and manage Databricks Apps
- Permission to read/write to workspace files
- Model Serving endpoint access

## Local Development Setup

### 1. Install Dependencies

**macOS:**
```bash
# Install uv (Python package manager)
brew install uv

# Install bun (JavaScript runtime)
brew install bun
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

### 3. Install Project Dependencies

```bash
# Python dependencies (backend)
uv sync

# JavaScript dependencies (frontend)
cd client
bun install
cd ..
```

### 4. Configure Environment

**Option A: Interactive Setup (Recommended)**

```bash
./setup.sh
```

This script will:
- Check for existing `.env.local` file
- Prompt for required configuration values
- Validate Databricks connectivity
- Create or update `.env.local`

**Option B: Manual Setup**

Copy the template and edit manually:

```bash
cp env.template .env.local
```

Edit `.env.local` with your values (see [Configuration](#configuration) section below).

**Option C: Use System Environment Variables**

The app will automatically fall back to system environment variables if `.env.local` doesn't exist.

## Configuration

### Required Environment Variables

Create `.env.local` in the project root with these variables:

```bash
# Databricks Configuration
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=dapi...  # Personal Access Token

# MLflow Configuration
MLFLOW_EXPERIMENT_ID=1234567890  # MLflow experiment for tracing
```

### Optional Environment Variables

```bash
# Environment Mode
ENV=development  # "development" or "production"

# Databricks Profile (optional for local dev)
DATABRICKS_CONFIG_PROFILE=DEFAULT  # Profile from ~/.databrickscfg
```

### Configuration Files

#### `config/agents.json`

Define available agents and their endpoints:

```json
{
  "agents": [
    {
      "id": "databricks-agent-01",
      "displayName": "Databricks Assistant",
      "description": "Explore Unity Catalog and answer questions",
      "deployment_type": "databricks-endpoint",
      "endpoint_name": "your-endpoint-name",
      "mlflow_experiment_id": "1234567890"
    }
  ]
}
```

**Key fields:**
- `deployment_type`: Handler type (`databricks-endpoint`, or future types)
- `endpoint_name`: Databricks Model Serving endpoint name
- `mlflow_experiment_id`: Experiment ID for this agent's traces

#### `config/app.json`

Application branding and metadata:

```json
{
  "appName": "Your App Name",
  "appDescription": "Your app description",
  "logo": "/logos/logo.png",
  "theme": {
    "primaryColor": "#FF3621"
  }
}
```

#### `config/about.json`

About page content (Markdown supported):

```json
{
  "title": "About This App",
  "content": "## Your Content\n\nMarkdown formatted text..."
}
```

### Creating MLflow Experiment

If you don't have an MLflow experiment ID:

**Via Databricks CLI:**
```bash
databricks experiments create --name "/Users/your-email@company.com/genai-app"
```

**Via Databricks UI:**
1. Navigate to Machine Learning → Experiments
2. Click "Create Experiment"
3. Copy the experiment ID from the URL

**Auto-Creation:**
The app will automatically create an experiment if the configured ID doesn't exist.

## Running Locally

### Start Development Servers

```bash
./watch.sh
```

This script starts:
- **FastAPI backend** on http://localhost:8000 (uvicorn with hot reload)
- **React frontend** (Vite dev server proxied through FastAPI)

The script automatically:
- Loads environment from `.env.local`
- Regenerates TypeScript API client from OpenAPI spec
- Opens browser to http://localhost:8000
- Watches for code changes and auto-reloads

**What you'll see:**
```
Starting development servers...
✓ Backend started (uvicorn)
✓ Frontend started (vite)
✓ API client generated
→ http://localhost:8000
```

### Development Workflow

**Backend changes:**
- Edit Python files in `server/`
- uvicorn auto-reloads on save
- No restart needed

**Frontend changes:**
- Edit React/TypeScript files in `client/`
- Vite hot-reloads instantly
- See changes in browser immediately

**Configuration changes:**
- Edit `config/*.json` files
- Refresh browser to see changes
- No server restart needed

### Stop Development Servers

```bash
# Press Ctrl+C in the terminal running ./watch.sh

# Or kill processes manually:
pkill -f uvicorn
pkill -f vite
```

## Testing

### Test Agent Without UI

Test the agent directly without starting the full web application:

```bash
./test_agent.sh
```

This script:
- Executes `server/agents/databricks_assistant/` code directly
- Shows full JSON response
- Displays formatted content
- Useful for debugging agent behavior and tools

**Example output:**
```
Testing agent...
✓ Response received
✓ Trace ID: req-abc123def456

Content:
---
Here is the response from the agent...
---
```

### Format Code

Format all Python and JavaScript code to project standards:

```bash
./fix.sh
```

Runs:
- **ruff** for Python (formatting + auto-fix)
- **prettier** for TypeScript/JavaScript/CSS

**Always run before committing code.**

### Run Quality Checks

Check code quality without making changes:

```bash
./check.sh
```

Runs:
- **ruff** linting (Python)
- **TypeScript** type checking (frontend)

## Databricks Apps Deployment

Deploy your application to Databricks Apps for production use.

### Prerequisites

1. **Databricks CLI configured:**
   ```bash
   databricks auth login
   ```

2. **Environment variables configured in `.env.local`:**
   - `DATABRICKS_HOST`
   - `MLFLOW_EXPERIMENT_ID`
   - App name (optional, defaults in deploy.sh)

3. **Model Serving endpoint deployed:**
   - Agent must be deployed as Databricks Model Serving endpoint
   - Endpoint name configured in `config/agents.json`

### Deployment Configuration

#### `app.yaml`

Databricks Apps configuration file:

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
    value: "https://your-workspace.cloud.databricks.com"

  # MLflow experiment ID (auto-updated by deploy.sh)
  - name: MLFLOW_EXPERIMENT_ID
    value: "1234567890"
```

**Note:** `deploy.sh` automatically updates `MLFLOW_EXPERIMENT_ID` from `.env.local`.

#### `.databricksignore`

Controls which files are synced to Databricks:

```
# Exclude from sync
client/node_modules/
client/.next/
__pycache__/
*.pyc
.env*

# Include build output (explicitly)
!client/out/
```

### Deploy to Databricks Apps

```bash
./deploy.sh
```

**What happens during deployment:**

1. **Validates configuration:**
   - Checks `.env.local` exists
   - Verifies `DATABRICKS_HOST` is set
   - Validates `MLFLOW_EXPERIMENT_ID`

2. **Updates app.yaml:**
   - Automatically sets `MLFLOW_EXPERIMENT_ID` from `.env.local`

3. **Builds frontend locally:**
   - Installs dependencies: `bun install`
   - Runs production build: `bun run build`
   - Generates static files in `client/out/`

4. **Syncs to Databricks:**
   - Uses `.databricksignore` for file filtering
   - Syncs to `/Workspace/Users/{your-email}/apps/{app-name}`
   - Includes `client/out/` build output

5. **Creates/updates app:**
   - Creates new app or updates existing
   - Configures environment from `app.yaml`
   - Starts application

**Example output:**
```
Deploying to Databricks Apps...
✓ Building frontend
✓ Syncing files
✓ Creating app: my-genai-app
✓ Deployment successful

App URL: https://my-genai-app-abc123.azuredatabricks.net
Logs: https://my-genai-app-abc123.azuredatabricks.net/logz
```

### Verify Deployment

1. **Check app status:**
   ```bash
   databricks apps list
   ```

   Look for your app with status `ACTIVE`.

2. **Access the app:**
   - Open the app URL from deploy output
   - You'll be redirected to Databricks OAuth login
   - After authentication, app should load

3. **Test functionality:**
   - Send a test message to the agent
   - Verify response streams correctly
   - Check trace data appears in MLflow

4. **Monitor logs:**
   - Access logs at `{app-url}/logz`
   - Requires browser authentication
   - Watch for errors during first interactions

### Update Existing Deployment

To update an already-deployed app:

```bash
./deploy.sh
```

The script automatically:
- Detects existing app
- Updates code and configuration
- Restarts app with new version

**No data loss:** Chat history will be lost (in-memory storage), but MLflow traces persist.

### Rollback Deployment

If deployment fails or has issues:

1. **Check app status:**
   ```bash
   databricks apps list
   databricks apps get {app-name}
   ```

2. **View logs for errors:**
   ```bash
   # Via browser (requires OAuth)
   open https://{app-url}/logz
   ```

3. **Redeploy previous version:**
   ```bash
   git checkout {previous-commit}
   ./deploy.sh
   ```

4. **Delete app if needed:**
   ```bash
   databricks apps delete {app-name}
   ```

## Monitoring and Troubleshooting

### Check Application Health

**Health endpoint:**
```bash
curl https://{app-url}/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

**MLflow experiment link:**
```bash
curl https://{app-url}/api/tracing_experiment
```

Returns MLflow experiment URL for viewing traces.

### View Application Logs

**Production (Databricks Apps):**
- Web UI: `https://{app-url}/logz` (requires OAuth)
- Logs show FastAPI requests, authentication, agent invocations, errors

**Local development:**
- Terminal output shows all logs
- Use `devLog()` in frontend for client-side debugging

### Common Issues

#### "No X-Forwarded-Access-Token header found"

**Cause:** Not running in Databricks Apps environment or OAuth not configured.

**Solution:**
- Ensure deployed to Databricks Apps (not local dev)
- Check app.yaml has OAuth enabled (default)
- Verify user is authenticated

#### "WorkspaceClient did not provide host or token"

**Cause:** Missing DATABRICKS_HOST in environment.

**Solution:**
- Check `app.yaml` has DATABRICKS_HOST set
- Verify `.env.local` has DATABRICKS_HOST (for local dev)
- Check environment variable is loaded correctly

#### "Agent not found" or "Endpoint not found"

**Cause:** Configuration mismatch between `config/agents.json` and deployed endpoint.

**Solution:**
- Verify `endpoint_name` in `config/agents.json` matches actual endpoint
- Check endpoint exists: `databricks serving-endpoints list`
- Verify endpoint is in `READY` state

#### Frontend shows "localhost:8000" errors in production

**Cause:** Frontend environment variable leaked into production build.

**Solution:**
- Remove `NEXT_PUBLIC_BACKEND_URL` from `.env.local`
- Keep it only in `.env.development`
- Rebuild frontend: `cd client && bun run build`
- Redeploy

#### Chat history lost on deployment

**Expected behavior:** Chat storage is in-memory only.

**Solution:**
- This is a known limitation (see [TODO.md](TODO.md))
- MLflow traces persist and can be viewed separately
- Future: Database storage planned

### Performance Monitoring

**MLflow Experiment:**
- View all agent traces in MLflow UI
- Analyze token usage, latency, errors
- Search by trace ID or time range

**Databricks Apps Metrics:**
- Check app resource usage in Databricks UI
- Monitor CPU, memory, request counts
- View error rates and response times

### Getting Help

1. **Check existing issues:** [GitHub Issues](https://github.com/databricks-solutions/databricks-genai-app-template/issues)
2. **Search documentation:** Check other docs in `/docs` folder
3. **Open new issue:** Include logs, configuration, and error messages
4. **Note:** Databricks support doesn't cover this template (community support only)

---

**Next Steps:**
- See [Developer Guide](developer-guide.md) for architecture details and customization
- See [Feature Documentation](features/) for specific feature details
- Check [TODO.md](TODO.md) for planned enhancements

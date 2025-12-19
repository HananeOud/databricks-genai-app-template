"""FastAPI app for the Databricks Apps + Agents demo."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

# Import tracing module to set up MLflow tracking URI for feedback logging
# Imported with '# noqa: F401' (tells linter it's intentionally unused)
from . import tracing  # noqa: F401

# Routers for organizing endpoints
from .db import run_migrations
from .routers import agent, chat, config, health
from .services.chat import init_storage

# Configure logging for Databricks Apps monitoring
# Logs written to stdout/stderr will be available in Databricks Apps UI and /logz endpoint
logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
  handlers=[
    logging.StreamHandler(),  # This ensures logs go to stdout for Databricks Apps monitoring
  ],
)

logger = logging.getLogger(__name__)

# Determine environment:
# 1. If .env.local exists → local development (load it and default to development)
# 2. If ENV is explicitly set → use that value
# 3. Otherwise → production (Databricks Apps uses app.yaml env vars)
env_local_loaded = load_dotenv(dotenv_path='.env.local')
env = os.getenv('ENV', 'development' if env_local_loaded else 'production')

if env_local_loaded:
  logger.info(f'✅ Loaded .env.local (ENV={env})')
else:
  logger.info(f'ℹ️  Using system environment variables (ENV={env})')


@asynccontextmanager
async def lifespan(app: FastAPI):
  """Async lifespan context manager for startup/shutdown events."""
  # Startup: Initialize async services
  logger.info('🚀 Starting application...')

  # Run database migrations (only if PostgreSQL is configured)
  # Safe to run multiple times - Alembic tracks applied migrations
  run_migrations()

  await init_storage()
  logger.info('✅ Chat storage initialized')

  yield

  # Shutdown: Cleanup if needed
  logger.info('👋 Shutting down application...')


app = FastAPI(lifespan=lifespan)

# Configure CORS based on environment
# Development: Allow localhost:3000 (Vite dev server)
# Production: Empty list (same-origin only, most secure)
# In production, FastAPI serves both frontend and API from same domain
allowed_origins = ['http://localhost:3000'] if env == 'development' else []

logger.info(f'CORS allowed origins: {allowed_origins}')

app.add_middleware(
  CORSMiddleware,
  allow_origins=allowed_origins,
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*'],
)

API_PREFIX = '/api'

# Include routers for modular endpoint organization
app.include_router(health.router, prefix=API_PREFIX, tags=['health'])
app.include_router(config.router, prefix=API_PREFIX, tags=['configuration'])
app.include_router(agent.router, prefix=API_PREFIX, tags=['agents'])
app.include_router(chat.router, prefix=API_PREFIX, tags=['chat'])

# Production: Serve Vite static build
# Vite builds to 'out' directory (configured in vite.config.ts)
# In development, access Vite directly at localhost:3000
# Vite dev server proxies /api/* to this FastAPI backend
build_path = Path('.') / 'client/out'
if build_path.exists():
  logger.info(f'Serving static files from {build_path}')
  app.mount('/', StaticFiles(directory=str(build_path), html=True), name='static')
else:
  logger.warning(
    f'Build directory {build_path} not found. '
    'In development, run Vite separately: cd client && bun run dev'
  )

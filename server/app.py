"""FastAPI app for the Databricks Apps + Agents demo."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

# Import tracing module to set up MLflow tracking URI for feedback logging
# Imported with '# noqa: F401' (tells linter it's intentionally unused)
from . import tracing  # noqa: F401

# Routers for organizing endpoints
from .routers import agent, chat, config, health

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

# Load environment variables from .env.local if it exists (local development)
# In production (Databricks Apps), system environment variables are used
if load_dotenv(dotenv_path='.env.local'):
  logger.info('✅ Loaded configuration from .env.local')
else:
  logger.info('ℹ️  Using system environment variables')

app = FastAPI()

# Configure CORS based on environment
# Development: Allow localhost:3000 (Next.js dev server)
# Production: Empty list (same-origin only, most secure)
# In production, FastAPI serves both frontend and API from same domain
env = os.getenv('ENV', 'production')
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

# Production: Serve Next.js static export
# Next.js builds to 'out' directory when using static export (output: 'export')
# In development, access Next.js directly at localhost:3000
# Next.js handles routing and proxies /api/* to this FastAPI backend
build_path = Path('.') / 'client/out'
if build_path.exists():
  logger.info(f'Serving Next.js static files from {build_path}')
  app.mount('/', StaticFiles(directory=str(build_path), html=True), name='static')
else:
  logger.warning(
    f'Next.js build directory {build_path} not found. '
    'In development, run Next.js separately: cd client && npm run dev'
  )

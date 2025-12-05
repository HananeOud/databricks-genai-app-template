/**
 * Backend URL configuration for Next.js API routes.
 *
 * Points to the Python FastAPI backend:
 * - Development: Local FastAPI server on localhost:8000
 * - Production (Databricks Apps): FastAPI in same container on localhost:8000
 *
 * Override via BACKEND_URL environment variable in .env.local or .env.production
 */
export const BACKEND_URL =
  process.env.BACKEND_URL || "http://localhost:8000";

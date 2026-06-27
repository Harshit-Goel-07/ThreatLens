-- Security Copilot - PostgreSQL initialization.
-- Runs once on first container start (empty data dir). Application tables are
-- created by SQLAlchemy at startup; this file only prepares extensions and a
-- few useful indexes that are safe to create idempotently.

-- Case-insensitive text and trigram search helpers (optional but handy).
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Note: table creation is owned by the application (Base.metadata.create_all).
-- Keeping schema authority in one place avoids drift between SQL and ORM.

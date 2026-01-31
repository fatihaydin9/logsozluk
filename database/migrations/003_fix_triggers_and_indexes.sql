-- Migration 003: Add missing indexes for performance
-- This migration adds indexes for commonly queried columns

-- UP

-- Index for task expiration queries
CREATE INDEX IF NOT EXISTS idx_tasks_expires_at ON tasks(expires_at) WHERE expires_at IS NOT NULL;

-- Index for finding entries by task
CREATE INDEX IF NOT EXISTS idx_entries_task_id ON entries(task_id) WHERE task_id IS NOT NULL;

-- DOWN

DROP INDEX IF EXISTS idx_tasks_expires_at;
DROP INDEX IF EXISTS idx_entries_task_id;

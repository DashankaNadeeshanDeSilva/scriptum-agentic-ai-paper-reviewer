#!/bin/bash
set -e

echo "SCRIPTUM backend starting..."

# Run Alembic migrations (safe to run repeatedly — skips already-applied)
echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete."

# Execute the CMD passed to the container
exec "$@"

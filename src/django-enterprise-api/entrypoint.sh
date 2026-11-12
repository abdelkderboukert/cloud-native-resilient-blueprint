#!/bin/sh
set -e

echo "=== Starting Enterprise Django REST API ==="

# Wait for PostgreSQL database availability
echo "Checking database connectivity..."
python << 'EOF'
import os
import sys
import time
import psycopg

db_url = os.environ.get("DATABASE_URL")
if not db_url or "sqlite" in db_url:
    print("Using local SQLite database. Skipping PostgreSQL connection wait.")
    sys.exit(0)

max_retries = 30
retry_delay = 2

for attempt in range(1, max_retries + 1):
    try:
        conn = psycopg.connect(db_url, connect_timeout=3)
        conn.close()
        print("Connected to PostgreSQL database successfully!")
        sys.exit(0)
    except Exception as exc:
        print(f"Waiting for database (attempt {attempt}/{max_retries}): {exc}")
        time.sleep(retry_delay)

print("Warning: Timed out waiting for database. Proceeding anyway.")
EOF

# Apply schema migrations
echo "Applying database schema migrations..."
python manage.py migrate --noinput

# Collect static assets
echo "Collecting static assets..."
python manage.py collectstatic --noinput --clear || true

# Execute application server
echo "Starting Gunicorn WSGI server on port 8000..."
exec gunicorn enterprise_platform.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-3} \
    --threads ${GUNICORN_THREADS:-2} \
    --worker-class gthread \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -

#!/usr/bin/env bash

set -euo pipefail

python -m app.backend_pre_start
alembic upgrade head
python -m app.initial_data

exec uvicorn app.main:app --host 0.0.0.0 --port 8000

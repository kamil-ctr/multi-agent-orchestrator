#!/bin/bash
# One-command startup: backend (FastAPI, :8000) + frontend (Vite, :5173).
set -e

cd "$(dirname "$0")"

if [ -f backend/venv/bin/activate ]; then
  source backend/venv/bin/activate
else
  echo "No backend/venv found — run: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

if [ ! -d frontend/node_modules ]; then
  echo "No frontend/node_modules found — run: cd frontend && npm install"
  exit 1
fi

trap 'kill 0' EXIT INT TERM

(cd backend && uvicorn main:app --reload --port 8000) &
(cd frontend && npm run dev) &
wait

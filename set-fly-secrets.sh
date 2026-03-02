#!/bin/bash
# Load .env and set Fly secrets. Run from TentService directory.
set -e
cd "$(dirname "$0")"

if [[ ! -f .env ]]; then
  echo "Error: .env not found. Create it from .env.example first."
  exit 1
fi

# Export vars from .env (handles KEY=value format)
set -a
source .env
set +a

fly secrets set \
  APP_NAME="${APP_NAME}" \
  DEBUG="${DEBUG}" \
  DEBUG_ROUTES_ENABLED="${DEBUG_ROUTES_ENABLED}" \
  SUPABASE_URL="${SUPABASE_URL}" \
  SUPABASE_PUBLISHABLE_KEY="${SUPABASE_PUBLISHABLE_KEY}" \
  SUPABASE_SECRET_KEY="${SUPABASE_SECRET_KEY}" \
  SUPABASE_SERVICE_ROLE_KEY="${SUPABASE_SERVICE_ROLE_KEY}" \
  SUPABASE_JWT_SECRET="${SUPABASE_JWT_SECRET}" \
  AUTH_ENABLED="${AUTH_ENABLED}" \
  SEED_ADMIN_USER_ID="${SEED_ADMIN_USER_ID}"

echo "Secrets set successfully."

#!/bin/bash
set -euo pipefail

echo "Starting Citation-Grounded Research Gap Analysis Assistant..."
echo ""

if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

python -m src.main "$@"


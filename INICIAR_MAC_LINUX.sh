#!/usr/bin/env bash
# Inicia DengueML-UPN en macOS o Linux. Uso: ./INICIAR_MAC_LINUX.sh [--puerto 8502]
cd "$(dirname "$0")" || exit 1
for py in "${DENGUEML_PYTHON:-}" python3.12 python3.11 python3; do
  [ -z "$py" ] && continue
  if command -v "$py" >/dev/null 2>&1 && "$py" -c "import sys; sys.exit(0 if sys.version_info[:2] in [(3,11),(3,12)] else 1)"; then
    exec "$py" iniciar.py "$@"
  fi
done
echo "Instale Python 3.11 o 3.12 (64 bits) con venv: https://www.python.org/downloads/"
echo "En Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
exit 1

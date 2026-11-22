#!/bin/sh
# Punto de entrada del contenedor EDU-ALERTA Panamá
set -e

cmd="${1:-app}"
shift || true

case "$cmd" in
  app)
    # Prepara base, datos de demostración y primera ejecución del pipeline (idempotente)
    python -m edualerta.cli bootstrap
    exec streamlit run app/Inicio.py \
      --server.address=0.0.0.0 --server.port=8501 \
      --server.headless=true --browser.gatherUsageStats=false "$@"
    ;;
  scheduler)
    exec python -m edualerta.scheduler "$@"
    ;;
  pipeline)
    exec python -m edualerta.cli pipeline "$@"
    ;;
  reset)
    exec python -m edualerta.cli reset "$@"
    ;;
  test)
    exec python -m pytest -v "$@"
    ;;
  *)
    exec "$cmd" "$@"
    ;;
esac

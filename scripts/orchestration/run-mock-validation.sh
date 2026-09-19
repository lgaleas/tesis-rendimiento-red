#!/bin/bash
set -e
source scripts/utils/helpers.sh

cleanup_environment
setup_experiment_dir "mock_validation"

docker compose up -d mock_io
sleep 3

MONITOR_CSV="${RAW_DIR}/mock_validation_resources.csv"
CONTAINER="mock_backend"

start_monitor $CONTAINER "$MONITOR_CSV"

echo "[INFO] Ejecutando k6 contra mock_io..."
docker run --rm -i \
    --cpuset-cpus="3,11" \
    --network benchmark_net \
    --user "$(id -u):$(id -g)" \
    -v "$(pwd)":/app \
    -w /app \
    grafana/k6 run \
    --summary-export="${RAW_DIR}/mock_validation_summary.json" \
    scripts/load_tests/k6-mock-validate.js > "${LOGS_DIR}/mock_validation_k6.log" 2>&1

stop_monitor

docker logs $CONTAINER > "${LOGS_DIR}/mock_validation_container.log" 2>&1

docker rm -f $CONTAINER >/dev/null 2>&1 || true

echo "[COMPLETADO] Validación de mock_io finalizada."
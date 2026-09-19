#!/bin/bash
set -e
source scripts/utils/helpers.sh

SCENARIO="A"

echo "======================================================"
echo "[INFO] Starting Ramping Load Test (Capacity Planning)"
echo "Methodology: Escenario A, Ramping Arrival Rate"
echo "======================================================"

cleanup_environment
setup_experiment_dir "ramping"

for FRAMEWORK in "fastapi" "express"; do
    PORT=$(get_port $FRAMEWORK)
    CONTAINER="${FRAMEWORK}_backend"

    for ENDPOINT in "cpu" "io"; do
        echo "------------------------------------------------------"
        echo "[INFO] Ramping Load - Framework: $FRAMEWORK | Endpoint: /$ENDPOINT"
        
        if ! start_container $FRAMEWORK; then continue; fi
        apply_network_scenario $SCENARIO $CONTAINER || true

        TIMESTAMP=$(date +"%H%M%S")
        FILENAME="${FRAMEWORK}_${ENDPOINT}_ramping_${TIMESTAMP}"
        
        start_monitor $CONTAINER "${RAW_DIR}/${FILENAME}_resources.csv"
        
        echo "[RUN] Executing k6 ramping test on $ENDPOINT..."

        docker run --rm -i \
            --name "k6_ramping_${TIMESTAMP}" \
            --cpuset-cpus="3,11" \
            --network benchmark_net \
            --user "$(id -u):$(id -g)" \
            -v "$(pwd)":/app \
            -w /app \
            -e TARGET_URL="http://${CONTAINER}:${PORT}" \
            -e ENDPOINT="/$ENDPOINT" \
            grafana/k6 run \
            --out json="${RAW_DIR}/${FILENAME}_metrics.json" \
            --summary-export="${RAW_DIR}/${FILENAME}_summary.json" \
            scripts/load_tests/k6-ramping.js > "${LOGS_DIR}/${FILENAME}_k6.log" 2>&1 || true

        stop_monitor

        docker logs $CONTAINER > "${LOGS_DIR}/${FILENAME}_container.log" 2>&1
        teardown_container $CONTAINER
    done
done

./venv/bin/python scripts/analysis/analyze-ramping.py "${EXPERIMENT_DIR}" || true

echo "======================================================"
echo "[COMPLETED] Ramping Load Test finished."
echo "Check the 'processed' folder for Capacity CSVs."
echo "======================================================"
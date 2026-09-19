#!/bin/bash
set -e
source scripts/utils/helpers.sh

REPETITIONS=${1:-15}
SCENARIO="A"
LOAD_PROFILE="medium"
RPS=50
DURATION="30s"

echo "======================================================"
echo "[INFO] Starting Baseline Test Battery (Scenario A)"
echo "Repetitions: $REPETITIONS | Profile: $LOAD_PROFILE"
echo "======================================================"

cleanup_environment
setup_experiment_dir "baseline"

for REP in $(seq 1 $REPETITIONS); do
    for FRAMEWORK in "fastapi" "express"; do
        PORT=$(get_port $FRAMEWORK)
        CONTAINER="${FRAMEWORK}_backend"

        for ENDPOINT in "cpu" "io"; do
            echo "------------------------------------------------------"
            echo "[INFO] Repetition $REP/$REPETITIONS - Framework: $FRAMEWORK | Endpoint: /$ENDPOINT"
            
            if ! start_container $FRAMEWORK; then continue; fi
            apply_network_scenario $SCENARIO $CONTAINER

            TIMESTAMP=$(date +"%H%M%S")
            FILENAME="${FRAMEWORK}_${ENDPOINT}_${SCENARIO}_${LOAD_PROFILE}_${REP}_${TIMESTAMP}"
            
            start_monitor $CONTAINER "${RAW_DIR}/${FILENAME}_resources.csv"
            run_k6 $PORT "/$ENDPOINT" $RPS $DURATION $FILENAME $CONTAINER
            stop_monitor

            docker logs $CONTAINER > "${LOGS_DIR}/${FILENAME}_container.log" 2>&1
            teardown_container $CONTAINER
        done
    done
done

run_analysis "analyze.py"
echo "======================================================"
echo "[COMPLETED] Baseline battery finished successfully."
echo "======================================================"
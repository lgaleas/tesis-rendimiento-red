#!/bin/bash
set -e
source scripts/utils/helpers.sh

REPETITIONS=${1:-15}
LOAD_PROFILE="medium"
RPS=50
DURATION="30s"
FRAMEWORKS=("fastapi" "express")
SCENARIOS=("A" "B" "C")
ENDPOINTS=("cpu" "io")

echo "======================================================"
echo "[INFO] Starting Chaos Experimentation Matrix"
echo "Repetitions: $REPETITIONS | Profile: $LOAD_PROFILE"
echo "======================================================"

cleanup_environment
setup_experiment_dir "chaos_test"

for REP in $(seq 1 $REPETITIONS); do
    for SCENARIO in "${SCENARIOS[@]}"; do
        for FRAMEWORK in "${FRAMEWORKS[@]}"; do
            PORT=$(get_port $FRAMEWORK)
            CONTAINER="${FRAMEWORK}_backend"
            
            for ENDPOINT in "${ENDPOINTS[@]}"; do
                echo "------------------------------------------------------"
                echo "[INFO] Rep $REP/$REPETITIONS | Scenario: $SCENARIO | Framework: $FRAMEWORK | Endpoint: /$ENDPOINT"
                
                if ! start_container $FRAMEWORK; then continue; fi
                if ! apply_network_scenario $SCENARIO $CONTAINER; then teardown_container $CONTAINER; continue; fi
                
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
done

run_analysis "analyze.py"
echo "======================================================"
echo "[COMPLETED] Chaos experimentation battery finished."
echo "======================================================"
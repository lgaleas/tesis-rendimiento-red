#!/bin/bash
set -e
trap 'echo "[ERROR] Script failed on line $LINENO. Exit code: $?"' ERR
source scripts/utils/helpers.sh

REPETITIONS=${1:-15}
DURATION="30s"
PROFILES=("low" "medium" "high")
SCENARIOS=("C")
FRAMEWORKS=("fastapi" "express")
ENDPOINTS=("cpu" "io")
declare -A RPS_MAP=( ["low"]=10 ["medium"]=50 ["high"]=100 )

echo "======================================================"
echo "[INFO] Starting Systematic Experiment - SCENARIO C ONLY"
echo "Repetitions: $REPETITIONS | Duration per test: $DURATION"
echo "======================================================"

cleanup_environment
setup_experiment_dir "scenario_C"

SUCCESS_COUNT=0
FAIL_COUNT=0

for REP in $(seq 1 $REPETITIONS); do
    for PROFILE in "${PROFILES[@]}"; do
        RPS=${RPS_MAP[$PROFILE]}
        for SCENARIO in "${SCENARIOS[@]}"; do
            for FRAMEWORK in "${FRAMEWORKS[@]}"; do
                PORT=$(get_port $FRAMEWORK)
                CONTAINER="${FRAMEWORK}_backend"
                
                for ENDPOINT in "${ENDPOINTS[@]}"; do
                    echo "------------------------------------------------------"
                    echo "[INFO] Rep $REP | Profile: $PROFILE ($RPS RPS) | Scenario: $SCENARIO | Framework: $FRAMEWORK | Endpoint: /$ENDPOINT"
                    
                    if ! start_container $FRAMEWORK; then
                        FAIL_COUNT=$((FAIL_COUNT + 1))
                        continue
                    fi
                    
                    if ! apply_network_scenario $SCENARIO $CONTAINER; then
                        teardown_container $CONTAINER
                        FAIL_COUNT=$((FAIL_COUNT + 1))
                        continue
                    fi
                    
                    TIMESTAMP=$(date +"%H%M%S")
                    FILENAME="${FRAMEWORK}_${ENDPOINT}_${SCENARIO}_${PROFILE}_${REP}_${TIMESTAMP}"
                    
                    start_monitor $CONTAINER "${RAW_DIR}/${FILENAME}_resources.csv"
                    run_k6 $PORT "/$ENDPOINT" $RPS $DURATION $FILENAME $CONTAINER
                    stop_monitor

                    docker logs $CONTAINER > "${LOGS_DIR}/${FILENAME}_container.log" 2>&1
                    teardown_container $CONTAINER
                    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
                done
            done
        done
    done
done

echo "======================================================"
echo "[COMPLETED] Data collection for Scenario C finished."
echo "  - Successful tests: $SUCCESS_COUNT | Failed tests: $FAIL_COUNT"
echo "======================================================"

run_analysis "analyze-scenario-C.py"
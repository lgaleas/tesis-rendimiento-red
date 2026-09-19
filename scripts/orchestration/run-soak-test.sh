#!/bin/bash
set -e
source scripts/utils/helpers.sh

DURATION=${1:-60m}        
RPS=50                 
SCENARIO="B"           
ENDPOINT="io"          

echo "======================================================"
echo "[INFO] Starting SOAK TEST (Resistance Test)"
echo "Duration: $DURATION | RPS: $RPS | Scenario: $SCENARIO | Endpoint: /$ENDPOINT"
echo "======================================================"

cleanup_environment
setup_experiment_dir "soak"

for FRAMEWORK in "fastapi" "express"; do
    PORT=$(get_port $FRAMEWORK)
    CONTAINER="${FRAMEWORK}_backend"
    
    echo "------------------------------------------------------"
    echo "[INFO] Evaluating Garbage Collector in: $FRAMEWORK (Takes $DURATION...)"
    
    if ! start_container $FRAMEWORK; then continue; fi
    if ! apply_network_scenario $SCENARIO $CONTAINER; then teardown_container $CONTAINER; continue; fi
    
    CLEAN_ENDPOINT=$(echo $ENDPOINT | tr -d '/')
    FILENAME="${FRAMEWORK}_soak_${CLEAN_ENDPOINT}_${SCENARIO}"
    
    start_monitor $CONTAINER "${RAW_DIR}/${FILENAME}_resources.csv"
    run_k6_soak $PORT "/${CLEAN_ENDPOINT}" $RPS $DURATION $FILENAME $CONTAINER
    sleep 5
    stop_monitor
            
    echo "[OK] Soak Test for $FRAMEWORK finished."
    docker logs $CONTAINER > "${LOGS_DIR}/${FILENAME}_container.log" 2>&1
    teardown_container $CONTAINER

    ./scripts/utils/cleanup.sh > /dev/null 2>&1 || true
    sync && sudo sh -c "echo 3 > /proc/sys/vm/drop_caches" 2>/dev/null
    sleep 2
done

echo "======================================================"
echo "[COMPLETED] Generating RAM timeline graph..."
echo "======================================================"
run_analysis "analyze-soak.py"
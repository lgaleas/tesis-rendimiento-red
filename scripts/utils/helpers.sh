#!/bin/bash

lock_cpu_frequency() {
    echo "[INFO] Locking CPU frequency to 4.0GHz (Disabling Boost/DVFS)..."
    if ! command -v cpupower >/dev/null 2>&1; then
        echo "[ERROR] cpupower no está instalado. Instálalo con: sudo apt install linux-tools-common linux-tools-$(uname -r)"
        return 1
    fi

    sudo cpupower frequency-set -g performance -u 4.0GHz 2>&1 | grep -v "No such file" || true
    local actual_gov=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)
    if [ "$actual_gov" = "performance" ]; then
        echo "[OK] CPU governor set to performance, max frequency 4.0 GHz"
    else
        echo "[WARN] Governor is '$actual_gov'. Performance may not be active. Check: cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
    fi
}

restore_cpu_frequency() {
    echo "[INFO] Restoring CPU frequency to dynamic boost..."
    if command -v cpupower >/dev/null 2>&1; then
        sudo cpupower frequency-set -g schedutil -d 400MHz -u 5.6GHz 2>/dev/null || \
        sudo cpupower frequency-set -g ondemand -d 400MHz -u 5.6GHz 2>/dev/null || \
        echo "[WARN] Could not restore CPU governor. Run manually."
    fi
    sudo swapon -a 2>/dev/null || echo "[WARN] Could not re-enable swap."
}

on_exit_trap() {
    local exit_code=$?
    if [ -n "$_TRAP_RUNNING" ]; then
        echo "[WARN] Trap already running, ignoring repeated signal."
        return
    fi
    _TRAP_RUNNING=1
    echo -e "\n[INFO] Signal caught (Finish or Cancel). Executing final cleanup..."
    stop_monitor
    ./scripts/utils/cleanup.sh > /dev/null 2>&1 || true
    restore_cpu_frequency
    exit $exit_code
}
trap 'on_exit_trap' EXIT INT TERM

cleanup_environment() {
    echo "[INFO] Cleaning orphaned monitor processes..."
    pkill -f "monitor-resources.sh" 2>/dev/null || true
    sleep 1
    local orphans=$(ps aux | grep -E "monitor-resources|docker stats" | grep -v grep | wc -l)
    if [ "$orphans" -gt 0 ]; then
        echo "[WARN] Found $orphans orphaned processes, forcing kill..."
        pkill -9 -f "monitor-resources.sh" 2>/dev/null || true
    fi
    ./scripts/utils/cleanup.sh > /dev/null 2>&1 || true
    
    echo "[INFO] Purging System RAM Cache and disabling Swap..."
    sync 
    sudo sh -c "echo 3 > /proc/sys/vm/drop_caches"
    sudo swapoff -a

    lock_cpu_frequency

    docker compose up -d mock_io
    sleep 3
}

setup_experiment_dir() {
    local prefix=$1
    RUN_ID=$(date +"%Y%m%d_%H%M%S")
    EXPERIMENT_DIR="experimentos/${prefix}_${RUN_ID}"
    RAW_DIR="${EXPERIMENT_DIR}/raw"
    LOGS_DIR="${EXPERIMENT_DIR}/logs"
    PROC_DIR="${EXPERIMENT_DIR}/processed"
    GRAPH_DIR="${EXPERIMENT_DIR}/graphs"

    mkdir -p "$RAW_DIR" "$LOGS_DIR" "$PROC_DIR" "$GRAPH_DIR"
    echo "[INFO] Output directory generated: ${EXPERIMENT_DIR}"
}

get_port() {
    if [ "$1" == "fastapi" ]; then echo "8000"; else echo "3000"; fi
}

start_container() {
    local framework=$1
    local port=$(get_port $framework)
    local container="${framework}_backend"

    echo "[INFO] Starting container $container..."
    if ! docker compose up -d $framework > /dev/null 2>&1; then
        echo "[ERROR] Failed to start container $container."
        return 1
    fi

    local max_retries=60
    local count=0
    until curl -s http://localhost:$port/health > /dev/null 2>&1; do
        sleep 1
        count=$((count+1))
        if [ $count -ge $max_retries ]; then
            echo "[ERROR] Container $framework did not start in time."
            docker rm -f $container > /dev/null 2>&1 || true
            return 1
        fi
    done
    echo "[INFO] Container $framework is ready."
    return 0
}

apply_network_scenario() {
    local scenario=$1
    local container=$2
    echo "[INFO] Applying network scenario $scenario..."
    if ! ./scripts/utils/netem-scenarios.sh "$scenario" "$container" "$LOGS_DIR" > "${LOGS_DIR}/${container}_netem_setup.log" 2>&1; then
        echo "[ERROR] netem-scenarios.sh failed for $container."
        return 1
    fi
    sleep 2
    return 0
}

start_monitor() {
    local container=$1
    local output_csv=$2
    ./scripts/utils/monitor-resources.sh "$container" "$output_csv" &
    MONITOR_PID=$!
}

stop_monitor() {
    if [ -n "$MONITOR_PID" ]; then
        kill $MONITOR_PID 2>/dev/null || true
        sleep 1
        if ps -p $MONITOR_PID > /dev/null 2>&1; then
            kill -9 $MONITOR_PID 2>/dev/null || true
        fi
        wait $MONITOR_PID 2>/dev/null || true
    fi
}

run_k6() {
    local port=$1
    local endpoint=$2
    local rps=$3
    local duration=$4
    local filename=$5
    local container=$6

    echo "[RUN] Executing k6 load test on $endpoint"
    local k6_exit=0
    timeout 120 docker run --rm -i \
        --name "k6_injector_$(date +%H%M%S)" \
        --cpuset-cpus="3,11" \
        --network benchmark_net \
        --user "$(id -u):$(id -g)" \
        -v "$(pwd)":/app \
        -w /app \
        -e TARGET_URL="http://${container}:${port}" \
        -e ENDPOINT="$endpoint" \
        -e RPS="$rps" \
        -e DURATION="$duration" \
        grafana/k6 run \
        --out json="${RAW_DIR}/${filename}_metrics.json" \
        --summary-export="${RAW_DIR}/${filename}_summary.json" \
        scripts/load_tests/k6-load.js > "${LOGS_DIR}/${filename}_k6.log" 2>&1 || k6_exit=$?
        
    if [ "$k6_exit" -eq 124 ]; then
        echo "[WARN] k6 timed out (120s), generating partial summary..."
        echo '{"error": "k6 timeout", "partial": true}' > "${RAW_DIR}/${filename}_summary.json"
    elif [ "$k6_exit" -ne 0 ]; then
        echo "[WARN] k6 failed with exit code $k6_exit."
    else
        echo "[OK] Results saved successfully."
    fi
}

run_k6_soak() {
    echo "[RUN] k6 SOAK test started (Duration: $duration). Logs: ${LOGS_DIR}/${FILENAME}_k6.log"
    echo "       Monitor CSV: ${RAW_DIR}/${FILENAME}_resources.csv"
    local port=$1
    local endpoint=$2
    local rps=$3
    local duration=$4
    local filename=$5
    local container=$6

    echo "[RUN] Executing k6 SOAK test on $endpoint"
    docker run --rm -i \
        --cpuset-cpus="3,11" \
        --network benchmark_net \
        --user "$(id -u):$(id -g)" \
        -v "$(pwd)":/app \
        -w /app \
        -e TARGET_URL="http://${container}:${port}" \
        -e ENDPOINT="$endpoint" \
        -e RPS="$rps" \
        -e DURATION="$duration" \
        grafana/k6 run \
        --out json="${RAW_DIR}/${filename}_metrics.json" \
        --summary-export="${RAW_DIR}/${filename}_summary.json" \
        scripts/load_tests/k6-load.js \
        > "${LOGS_DIR}/${filename}_k6.log" 2>&1 || k6_exit=$?

    if [ "$k6_exit" -ne 0 ]; then
        echo "[WARN] k6 finalizó con código $k6_exit. Revisar ${LOGS_DIR}/${filename}_k6.log"
    else
        echo "[OK] k6 terminó exitosamente."
    fi
}

teardown_container() {
    local container=$1
    docker rm -f "$container" > /dev/null 2>&1 || true
    sleep 2
}

run_analysis() {
    local analyze_script=$1
    if [ "$(ls -A ${RAW_DIR}/*.json 2>/dev/null)" ] || [ "$(ls -A ${RAW_DIR}/*.csv 2>/dev/null)" ]; then
        echo "[INFO] Processing data and exporting graphs..."
        ./venv/bin/python "scripts/analysis/${analyze_script}" "${EXPERIMENT_DIR}" 2>&1 | tee "${LOGS_DIR}/analysis.log" || true
    else
        echo "[ERROR] No data found in ${RAW_DIR} to analyze."
    fi
    chown -R ${SUDO_USER:-$USER}:${SUDO_USER:-$USER} "${EXPERIMENT_DIR}"
}

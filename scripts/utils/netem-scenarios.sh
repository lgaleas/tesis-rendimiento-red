#!/bin/bash

set -e

SCENARIO=$1
CONTAINER=$2
LOG_DIR=${3:-logs}

mkdir -p "$LOG_DIR"

docker exec $CONTAINER tc qdisc del dev eth0 root 2>/dev/null || true
docker exec $CONTAINER tc qdisc del dev eth0 ingress 2>/dev/null || true
docker exec $CONTAINER ip link del ifb0 2>/dev/null || true

if [ "$SCENARIO" == "A" ]; then
    echo "[CAOS] Escenario A aplicado en $CONTAINER (Sin degradación)."
    exit 0
fi

docker exec $CONTAINER ip link add ifb0 type ifb
docker exec $CONTAINER ip link set ifb0 up
docker exec $CONTAINER tc qdisc add dev eth0 handle ffff: ingress
docker exec $CONTAINER tc filter add dev eth0 parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev ifb0

case $SCENARIO in
    B)
        docker exec $CONTAINER tc qdisc add dev eth0 root netem delay 73ms 22ms 30% loss 12%
        docker exec $CONTAINER tc qdisc add dev ifb0 root netem delay 73ms 22ms 30% loss 12%
        echo "[CAOS] Escenario B (P90 M-Lab Ecuador semanal): delay 73ms, jitter 22ms, loss 12%, correl 30%"
        ;;
    C)
        docker exec $CONTAINER tc qdisc add dev eth0 root netem delay 80.5ms 45ms distribution paretonormal loss 17% reorder 10%
        docker exec $CONTAINER tc qdisc add dev ifb0 root netem delay 80.5ms 45ms distribution paretonormal loss 17% reorder 10%
        echo "[CAOS] Escenario C (P95 M-Lab Ecuador semanal): delay 80.5ms, jitter 45ms, loss 17%, reorder 10%"
        ;;
    *)
        echo "[ERROR] Escenario no válido. Use A, B o C."
        exit 1
        ;;
esac

docker exec $CONTAINER tc -s qdisc show dev eth0 > "${LOG_DIR}/${CONTAINER}_netem_egress.log"
docker exec $CONTAINER tc -s qdisc show dev ifb0 > "${LOG_DIR}/${CONTAINER}_netem_ingress.log"

if ! grep -q "netem" "${LOG_DIR}/${CONTAINER}_netem_egress.log" || ! grep -q "netem" "${LOG_DIR}/${CONTAINER}_netem_ingress.log"; then
    echo "[ERROR FATAL] Las reglas Ingress/Egress no se aplicaron correctamente."
    exit 1
fi

exit 0
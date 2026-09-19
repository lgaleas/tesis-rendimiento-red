#!/bin/bash

CONTAINER=$1
OUTPUT_CSV=$2

if [ -z "$CONTAINER" ] || [ -z "$OUTPUT_CSV" ]; then
    echo "Uso: $0 <Nombre_Contenedor> <Archivo_Salida.csv>"
    exit 1
fi

DIR=$(dirname "$OUTPUT_CSV")
if [ ! -d "$DIR" ]; then
    exit 0
fi

echo "timestamp,cpu_percent,mem_usage,cpu_temp_c,tcp_conns" > "$OUTPUT_CSV"

while true; do
    if [ ! -d "$DIR" ]; then
        exit 0
    fi
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
        exit 0
    fi
    
    TIMESTAMP=$(date +"%Y-%m-%dT%H:%M:%S")
    STATS=$(docker stats $CONTAINER --no-stream --format "{{.CPUPerc}},{{.MemUsage}}" 2>/dev/null || echo "0.00%,0MiB / 0MiB")
    
    if [ "$STATS" == "0.00%,0MiB / 0MiB" ]; then
        exit 0
    fi
    
    CLEAN_STATS=$(echo "$STATS" | awk -F',' '{
        gsub(/%/, "", $1); 
        split($2, mem, " / "); 
        match(mem[1], /[0-9.]+/); 
        val = substr(mem[1], RSTART, RLENGTH);
        print $1 "," val
    }')
    
    TEMP=$(sensors -j 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for chip, entries in data.items():
        for name, values in entries.items():
            if any(k in name.lower() for k in ('tctl','tdie','package id 0','core 0')):
                temp = values.get('temp1_input') or values.get('temp1') or values.get('temp')
                if temp is not None:
                    print(temp)
                    sys.exit(0)
except: pass
" 2>/dev/null || echo "NaN")

    TCP_CONNS=$(docker exec $CONTAINER ss -t -n state established 2>/dev/null | grep -v "Recv-Q" | wc -l)
    if [ -z "$TCP_CONNS" ]; then
        TCP_CONNS="0"
    fi

    echo "$TIMESTAMP,$CLEAN_STATS,$TEMP,$TCP_CONNS" >> "$OUTPUT_CSV"
    sleep 1
done
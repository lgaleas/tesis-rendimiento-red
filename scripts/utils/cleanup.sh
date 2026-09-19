#!/bin/bash

echo "[LIMPIEZA] Deteniendo y eliminando contenedores del experimento..."
docker rm -f fastapi_backend express_backend mock_backend 2>/dev/null || true

echo "[LIMPIEZA] Eliminando redes huérfanas..."
docker network prune -f > /dev/null

echo "[LIMPIEZA] Eliminando logs crudos de k6 (Opcional, descomentar si deseas vaciar logs)..."

echo "[COMPLETADO] El entorno está limpio."
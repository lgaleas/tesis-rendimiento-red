# ==============================================================================
# Build Stage: Instalación de dependencias
# ==============================================================================
FROM python:3.14.3-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# Production Stage: Imagen final ligera
# ==============================================================================
FROM python:3.14.3-slim

# Herramientas de red para Ingeniería del Caos (netem)
RUN apt-get update && apt-get install -y iproute2 iputils-ping && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages

COPY --from=builder /usr/local/bin /usr/local/bin
COPY app/ /app/

# Metadata labels para trazabilidad
LABEL maintainer="leyber.galeas@uta.edu.ec"
LABEL version="1.0.0"
LABEL description="FastAPI backend for thesis performance comparison"
LABEL thesis.project="rendimiento-red-degradada"

EXPOSE 8000

# Cambiar de --workers 2 a --workers 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

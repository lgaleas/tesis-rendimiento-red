# ==============================================================================
# Build Stage: Instalación de dependencias
# ==============================================================================
FROM node:24.14.0-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev

# ==============================================================================
# Production Stage: Imagen final ligera
# ==============================================================================
FROM node:24.14.0-alpine

RUN apk add --no-cache iproute2 iputils

WORKDIR /app

COPY --from=builder /app/node_modules ./node_modules

COPY src/ ./src/

LABEL maintainer="leyber.galeas@uta.edu.ec"
LABEL version="1.0.0"
LABEL description="Express.js backend for thesis performance comparison"
LABEL thesis.project="rendimiento-red-degradada"

EXPOSE 3000

CMD ["node", "src/index.js"]
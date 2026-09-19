# Impacto del rendimiento de FastAPI vs Express.js bajo degradación de red

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22841248.svg)](https://doi.org/10.5281/zenodo.22841248)

Tesis de grado — evaluación empírica del rendimiento de dos frameworks
backend (FastAPI, Express.js) bajo condiciones de red degradada,
simulando infraestructura de telecomunicaciones ecuatoriana mediante
Ingeniería del Caos (tc/netem).

## Arquitectura

![Arquitectura](resultados/graficas/0_arquitectura_netem_simetrico.png)

## Resultados clave

![Latencia P99 por escenario](resultados/graficas/comp_01_latency_evolution.png)

## Hallazgos principales

- **Bajo carga ideal (Escenario A, 100 RPS)**: en el endpoint `/cpu`, FastAPI mantuvo una latencia P99 de ~3 ms frente a los ~25 ms de Express, con un uso de CPU sustancialmente menor (~28% vs ~90%).
- **Bajo red degradada (Escenarios B y C)**: ambos frameworks convergen a un comportamiento similar — la latencia P99 se dispara por encima de los 850-950 ms y la tasa de errores supera el 35-50%, dominada por la degradación de red (tc/netem) más que por el framework en sí.
- **Prueba de resistencia (soak test, 60 min, 50 RPS)**: con throughput y latencia prácticamente idénticos entre ambos (~49.9 RPS, ~880 ms P99), **FastAPI mostró un drift de memoria de +48 MiB** a lo largo de la hora, mientras que **Express se mantuvo estable en +1.2 MiB** — una diferencia relevante para servicios de larga duración que no aparece en pruebas cortas.

## Cómo correr el experimento

```bash
docker compose up -d
./scripts/orchestration/run-baseline.sh
```

## Estructura del repositorio

- `services/` — código de los backends FastAPI y Express.js instrumentados
- `scripts/orchestration/` — scripts que ejecutan cada escenario de red (A: ideal, B: inestable, C: caos)
- `scripts/analysis/` — pipeline de análisis estadístico y generación de gráficas
- `resultados/tablas/` — CSVs agregados y tablas LaTeX generadas
- `resultados/graficas/` — gráficas finales usadas en la defensa

## Dataset completo

Los datos crudos completos (~10GB, todas las repeticiones y escenarios,
más los CSVs de latencias/errores/GC por petición individual)
están publicados en Zenodo: [10.5281/zenodo.22841248](https://doi.org/10.5281/zenodo.22841248)

## Stack técnico

Docker · tc/netem · k6 · FastAPI · Express.js · pandas · matplotlib · seaborn

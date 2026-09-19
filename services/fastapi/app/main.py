import hashlib
import asyncio
import os
import time
import json
import gc
import httpx
from datetime import datetime
from fastapi import FastAPI, HTTPException
from gc_monitor import start_gc_monitor, memory_snapshot_task, get_rss_mb

app = FastAPI()

HASH_ITERATIONS = int(os.getenv("HASH_ITERATIONS", 8000))

http_client = None

@app.on_event("startup")
async def startup_event():
    global http_client
    start_gc_monitor()
    asyncio.create_task(memory_snapshot_task())
    http_client = httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=100, max_connections=100))

@app.on_event("shutdown")
async def shutdown_event():
    global http_client
    if http_client:
        await http_client.aclose()

@app.get("/health")
def health_check():
    return {"status": "ok", "framework": "fastapi"}

@app.get("/cpu")
async def cpu_bound():
    start_time = time.perf_counter()
    payload = b"deterministic_seed_string_for_fair_comparison"
    
    for _ in range(HASH_ITERATIONS):
        payload = hashlib.sha256(payload).digest()
        
    duration_ms = (time.perf_counter() - start_time) * 1000.0
    rss_mb = get_rss_mb()
    
    print(json.dumps({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": "cpu_endpoint_complete",
        "framework": "fastapi",
        "duration_ms": duration_ms,
        "iterations": HASH_ITERATIONS,
        "memory": {"rss_mb": rss_mb}
    }), flush=True)
    
    return {"status": "success", "iterations": HASH_ITERATIONS}

@app.get("/io")
async def io_bound():
    try:
        # Usar el cliente global reutilizable
        response = await http_client.get("http://mock_io:80/")
        
        rss_mb = get_rss_mb()
            
        print(json.dumps({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": "io_endpoint_complete",
            "framework": "fastapi",
            "memory": {"rss_mb": rss_mb}
        }), flush=True)
        
        return {"status": "success", "mock_status": response.status_code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
import gc
import time
import json
import asyncio
from datetime import datetime

gc_stats = {"collections": 0, "total_time_ms": 0.0}
gc_start_time = 0.0

def gc_callback(phase, info):
    global gc_start_time
    if phase == "start":
        gc_start_time = time.perf_counter()
    elif phase == "stop":
        duration_ms = (time.perf_counter() - gc_start_time) * 1000.0
        gc_stats["collections"] += 1
        gc_stats["total_time_ms"] += duration_ms
        
        print(json.dumps({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": "gc_cycle",
            "framework": "fastapi",
            "gc_type": f"Generation {info.get('generation', 'Unknown')}",
            "duration_ms": duration_ms,
            "total_collections": gc_stats["collections"],
            "total_gc_time_ms": gc_stats["total_time_ms"]
        }), flush=True)

def get_rss_mb() -> float:
    try:
        with open('/proc/self/status') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    return round(int(line.split()[1]) / 1024, 2)
    except Exception:
        return 0.0
    return 0.0

async def memory_snapshot_task():
    while True:
        await asyncio.sleep(10)
        avg_gc_time = round(gc_stats["total_time_ms"] / gc_stats["collections"], 2) if gc_stats["collections"] > 0 else 0
        print(json.dumps({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": "memory_snapshot",
            "framework": "fastapi",
            "memory": {"rss_mb": get_rss_mb()},
            "gc_summary": {
                "total_collections": gc_stats["collections"],
                "total_time_ms": gc_stats["total_time_ms"],
                "avg_gc_time_ms": avg_gc_time
            }
        }), flush=True)

def start_gc_monitor():
    gc.callbacks.append(gc_callback)
    print("[INFO] Garbage Collector monitor initialized", flush=True)
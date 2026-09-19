const { PerformanceObserver } = require('perf_hooks');

let gcStats = { collections: 0, totalTimeMs: 0 };
const gcTypes = { 0: 'Unknown', 1: 'Scavenge', 2: 'Mark/Sweep', 4: 'Incremental', 8: 'Weak/Phantom' };

const startGcMonitor = () => {
    const gcObserver = new PerformanceObserver((list) => {
        const entry = list.getEntries()[0];
        gcStats.collections++;
        gcStats.totalTimeMs += entry.duration;
        
        console.log(JSON.stringify({
            timestamp: new Date().toISOString(), 
            event: 'gc_cycle', 
            framework: 'express',
            gc_type: gcTypes[entry.kind] || 'Unknown', 
            duration_ms: entry.duration,
            total_collections: gcStats.collections, 
            total_gc_time_ms: gcStats.totalTimeMs
        }));
    });
    gcObserver.observe({ entryTypes: ['gc'] });

    setInterval(() => {
        const memUsage = process.memoryUsage();
        const avgGcTime = gcStats.collections > 0 ? (gcStats.totalTimeMs / gcStats.collections) : 0;
        
        console.log(JSON.stringify({
            timestamp: new Date().toISOString(), 
            event: 'memory_snapshot', 
            framework: 'express',
            memory: { rss_mb: Math.round(memUsage.rss / 1024 / 1024 * 100) / 100 },
            gc_summary: {
                total_collections: gcStats.collections,
                total_time_ms: gcStats.totalTimeMs,
                avg_gc_time_ms: Math.round(avgGcTime * 100) / 100
            }
        }));
    }, 10000);
    
    console.log('[INFO] Garbage Collector monitor initialized');
};

module.exports = { startGcMonitor };
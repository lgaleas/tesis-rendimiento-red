const express = require('express');
const crypto = require('crypto');
const { startGcMonitor } = require('./gcMonitor');
const { setGlobalDispatcher, Agent } = require('undici');

setGlobalDispatcher(new Agent({
    connections: 100
}));

const PORT = process.env.PORT || 3000;
const HASH_ITERATIONS = parseInt(process.env.HASH_ITERATIONS || '8000', 10);

startGcMonitor();
const app = express();

app.get('/health', (req, res) => { 
    res.json({ status: 'ok', framework: 'express' }); 
});

app.get('/cpu', (req, res) => {
    const startTime = Date.now();
    let payload = Buffer.from('deterministic_seed_string_for_fair_comparison', 'utf8');
    
    for (let i = 0; i < HASH_ITERATIONS; i++) { 
        payload = crypto.createHash('sha256').update(payload).digest(); 
    }
    
    const durationMs = Date.now() - startTime;
    const rssMb = Math.round(process.memoryUsage().rss / 1024 / 1024 * 100) / 100;
    
    console.log(JSON.stringify({
        timestamp: new Date().toISOString(), 
        event: 'cpu_endpoint_complete', 
        framework: 'express',
        duration_ms: durationMs, 
        iterations: HASH_ITERATIONS,
        memory: { rss_mb: rssMb }
    }));
    
    res.json({ status: 'success', iterations: HASH_ITERATIONS });
});

app.get('/io', async (req, res) => {
    try {
        // Petición asíncrona real a través de la interfaz de red degradada (eth0)
        const response = await fetch('http://mock_io:80/');
        await response.text(); // Consumir el cuerpo para liberar el socket
        
        const rssMb = Math.round(process.memoryUsage().rss / 1024 / 1024 * 100) / 100;
        
        console.log(JSON.stringify({
            timestamp: new Date().toISOString(), 
            event: 'io_endpoint_complete', 
            framework: 'express',
            memory: { rss_mb: rssMb }
        }));
        
        res.json({ status: 'success', mock_status: response.status });
    } catch (error) {
        // SI LA RED FALLA, DEVOLVER 500, NO CRASHEAR EL CONTENEDOR
        res.status(500).json({ status: 'error', message: error.message });
    }
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`[INFO] Express listening on port ${PORT} at 0.0.0.0`);
});
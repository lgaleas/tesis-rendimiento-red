import http from 'k6/http';
import { check } from 'k6';

const TARGET_URL = __ENV.TARGET_URL || 'http://localhost:8000';
const ENDPOINT = __ENV.ENDPOINT || '/health';

export const options = {
    noConnectionReuse: true,
    userAgent: 'K6-Ramping-Injector/1.0',
    scenarios: {
        capacity_test: {
            executor: 'ramping-arrival-rate',
            startRate: 10,
            timeUnit: '1s',
            preAllocatedVUs: 50,
            maxVUs: 2000,
            stages: [
                { target: 200, duration: '3m' }, // Incremento constante hasta 200 RPS
                { target: 250, duration: '1m' }, // Empuje final a 250 RPS para forzar quiebre
            ],
        },
    },
    thresholds: {
        // Se establecen thresholds para abortar temprano si el sistema colapsa abruptamente
        http_req_failed: ['rate<0.50'], 
    },
};

export default function () {
    const params = {
        timeout: '2s',
        headers: { 'Content-Type': 'application/json', 'Connection': 'close' }
    };

    const res = http.get(`${TARGET_URL}${ENDPOINT}`, params);
    
    check(res, {
        'status is 200': (r) => r.status === 200,
    });
}
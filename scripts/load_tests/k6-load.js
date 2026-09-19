import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';

const TARGET_URL = __ENV.TARGET_URL || 'http://localhost:8000';
const ENDPOINT = __ENV.ENDPOINT || '/health';

const targetRps = parseInt(__ENV.RPS) || 50;
const sustainedDuration = __ENV.DURATION || '30s';

const successfulReqs = new Counter('successful_requests');

export const options = {
    noConnectionReuse: true,
    userAgent: 'K6-Chaos-Injector/1.0',
    scenarios: {
        open_model: {
            executor: 'constant-arrival-rate',
            rate: targetRps,
            timeUnit: '1s',
            duration: sustainedDuration,
            preAllocatedVUs: Math.max(targetRps, 50),
            maxVUs: targetRps * 30,
        },
    },
    thresholds: {
        http_req_failed: ['rate<0.05'],
        http_req_duration: ['p(99)<500'],
    },
};

export default function () {
    const params = {
        timeout: '1s',
        headers: {
            'Content-Type': 'application/json',
            'Connection': 'close'
        }
    };

    const res = http.get(`${TARGET_URL}${ENDPOINT}`, params);
    
    if (res.status === 200) {
        successfulReqs.add(1);
    }

    check(res, {
        'status is 200': (r) => r.status === 200,
        'response time < 500ms': (r) => r.timings.duration < 500,
    });
}
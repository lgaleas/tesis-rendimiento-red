import http from 'k6/http';
import { check } from 'k6';

export const options = {
  noConnectionReuse: true,
  userAgent: 'K6-Validation/1.0',
  scenarios: {
    mock_validation: {
      executor: 'constant-arrival-rate',
      rate: 500,
      timeUnit: '1s',
      duration: '60s',
      preAllocatedVUs: 100,
      maxVUs: 200,
    },
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
  const res = http.get('http://mock_io:80/', params);
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
}
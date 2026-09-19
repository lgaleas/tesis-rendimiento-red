import os, json
import pandas as pd
from datetime import datetime
from src.config import COLD_START_SEC, LOCAL_TZ

def parse_k6_summary(filepath):
    if not os.path.exists(filepath): return 0.0, 0.0
    with open(filepath, 'r') as f: data = json.load(f)
    metrics = data.get('metrics', {})
    succ = metrics.get('successful_requests', {})
    tp = succ['values'].get('rate', 0) if 'values' in succ else succ.get('rate', metrics.get('http_reqs', {}).get('rate', 0))
    err_metric = metrics.get('http_req_failed', {})
    err = err_metric['values'].get('rate', 0) * 100 if 'values' in err_metric else err_metric.get('value', 0) * 100
    return tp, err

def parse_k6_metrics_and_errors(filepath, apply_cold_start=True):
    if not os.path.exists(filepath): return pd.DataFrame(), pd.DataFrame()
    durations, errors = [], []
    first_ts = None
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if '"Point"' not in line: continue
            try:
                row = json.loads(line)
                if row.get('type') == 'Point':
                    ts = datetime.fromisoformat(row['data']['time'].replace('Z', '+00:00'))
                    val = row['data']['value']
                    if first_ts is None: first_ts = ts
                    rel_sec = (ts - first_ts).total_seconds()
                    if apply_cold_start and rel_sec < COLD_START_SEC: continue

                    if row.get('metric') == 'http_req_duration' and val is not None:
                        durations.append({'Time': ts, 'Relative_Time': rel_sec, 'Latency': val})
                    elif row.get('metric') == 'http_req_failed' and val is not None:
                        errors.append({'Time': ts, 'Relative_Time': rel_sec, 'Failed': val})
            except: pass
    return pd.DataFrame(durations), pd.DataFrame(errors)

def parse_resources(filepath, apply_cold_start=True):
    if not os.path.exists(filepath): return pd.DataFrame()
    try:
        df = pd.read_csv(filepath)
        if 'timestamp' not in df.columns: return pd.DataFrame()
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce')
        if df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.tz_localize(LOCAL_TZ).dt.tz_convert('UTC')
        t_start = df['timestamp'].iloc[0]
        df['Relative_Time'] = (df['timestamp'] - t_start).dt.total_seconds()
        if apply_cold_start:
            df = df[df['Relative_Time'] >= COLD_START_SEC].copy()
            df['Relative_Time'] = df['Relative_Time'] - df['Relative_Time'].min()
        return df
    except: return pd.DataFrame()

def parse_gc_events(filepath, framework):
    if not os.path.exists(filepath):
        return pd.DataFrame()
    events = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if 'gc_cycle' not in line:
                continue
            try:
                import re
                match = re.search(r'\{[^}]+\}', line)
                if not match:
                    continue
                row = json.loads(match.group())
                if row.get('event') == 'gc_cycle' and row.get('timestamp'):
                    events.append({
                        'Time': pd.to_datetime(row['timestamp']),
                        'Duration': row.get('duration_ms', 0),
                        'Type': row.get('gc_type', 'Unknown')
                    })
            except:
                pass

    df = pd.DataFrame(events)
    return df

import pytz

COLD_START_SEC = 10
SLO_MS = 500
TIMEOUT_MS = 1000

COLORS = {'FastAPI': '#1f77b4', 'Express': '#ff7f0e'}
FRAMEWORK_ORDER = ['FastAPI', 'Express']
PROFILE_ORDER = ['low', 'medium', 'high']
SCENARIO_ORDER = ['A (Ideal)', 'B (Inestable)', 'C (Caos)']

LOCAL_TZ = pytz.timezone('America/Guayaquil')
import graphviz

# Configuración inicial del lienzo (Alta resolución, flujo Arriba hacia Abajo)
dot = graphviz.Digraph('ArbolProblemas', format='png')
dot.attr(rankdir='TB', dpi='300', splines='ortho', nodesep='0.6', ranksep='0.8')

# Paleta de colores (Tonos pastel profesionales)
C_AMARILLO = '#fff9c4'
C_VERDE    = '#c8e6c9'
C_ROJO     = '#ffcdd2'
C_AZUL     = '#bbdefb'
C_BLANCO   = '#ffffff'
C_BORDE    = '#444444'

# Estilos globales para nodos (cajas) y bordes (flechas)
dot.attr('node', shape='box', style='filled, rounded', fontname='Helvetica',
         fontsize='12', fontcolor='#111111', color=C_BORDE, penwidth='1.2',
         margin='0.25,0.15')
dot.attr('edge', color='#666666', penwidth='1.5', arrowsize='0.9')

# ==========================================
# 1. CAUSAS (Bloques Superiores)
# ==========================================
# --- Bloque Izquierdo ---
dot.node('C1A', 'Benchmarks solo en\nentornos ideales', fillcolor=C_AMARILLO)
dot.node('C1B', 'Falta de pruebas de\nIngeniería del Caos', fillcolor=C_AMARILLO)
dot.node('C1C', 'Evaluaciones de rendimiento\nincompletas', fillcolor=C_VERDE, fontname='Helvetica-Bold')

# --- Bloque Central ---
dot.node('C2A', 'Infraestructura de red\ndegradada en Ecuador', fillcolor=C_AMARILLO)
dot.node('C2B', 'Crisis energética afectando\ntelecomunicaciones', fillcolor=C_AMARILLO)
dot.node('C2C', 'Contexto regional con\nred inestable', fillcolor=C_VERDE, fontname='Helvetica-Bold')

# --- Bloque Derecho ---
dot.node('C3A', 'Suposición errónea\nde red confiable', fillcolor=C_AMARILLO)
dot.node('C3B', 'Desarrollo sin considerar\ndegradación operativa', fillcolor=C_AMARILLO)
dot.node('C3C', 'Falacias de computación\ndistribuida', fillcolor=C_VERDE, fontname='Helvetica-Bold')

# ==========================================
# 2. PROBLEMA CENTRAL (Bloque Medio)
# ==========================================
# Letra más grande y caja destacada
dot.node('PC', 'Vacío de evidencia empírica sobre degradación de\nrendimiento de FastAPI vs Express.js en\ncondiciones de red degradada',
         fillcolor=C_ROJO, fontsize='14', fontname='Helvetica-Bold', margin='0.4,0.2')

# ==========================================
# 3. EFECTOS (Bloques Inferiores)
# ==========================================
# --- Bloque Izquierdo ---
dot.node('E1A', 'Impacto económico', fillcolor=C_AZUL, fontname='Helvetica-Bold')
dot.node('E1B', 'Pérdidas por tiempo\nde inactividad', fillcolor=C_BLANCO)
dot.node('E1C', 'Aumento del\nCloud Waste', fillcolor=C_BLANCO)

# --- Bloque Central ---
dot.node('E2A', 'Baja calidad de servicio', fillcolor=C_AZUL, fontname='Helvetica-Bold')
dot.node('E2B', 'Latencia excesiva', fillcolor=C_BLANCO)
dot.node('E2C', 'Tasa de errores elevada', fillcolor=C_BLANCO)

# --- Bloque Derecho ---
dot.node('E3A', 'Decisiones arquitectónicas\nsubóptimas', fillcolor=C_AZUL, fontname='Helvetica-Bold')
dot.node('E3B', 'Sistemas no resilientes', fillcolor=C_BLANCO)
dot.node('E3C', 'Ineficiencia en recursos', fillcolor=C_BLANCO)

# ==========================================
# 4. CONEXIONES Y ENRUTAMIENTO (Flechas)
# ==========================================
# Causas de primer nivel -> Causas directas
dot.edge('C1A', 'C1C')
dot.edge('C1B', 'C1C')
dot.edge('C2A', 'C2C')
dot.edge('C2B', 'C2C')
dot.edge('C3A', 'C3C')
dot.edge('C3B', 'C3C')

# Causas directas -> Problema Central
dot.edge('C1C', 'PC')
dot.edge('C2C', 'PC')
dot.edge('C3C', 'PC')

# Problema Central -> Efectos principales
dot.edge('PC', 'E1A')
dot.edge('PC', 'E2A')
dot.edge('PC', 'E3A')

# Efectos principales -> Efectos derivados
dot.edge('E1A', 'E1B')
dot.edge('E1A', 'E1C')
dot.edge('E2A', 'E2B')
dot.edge('E2A', 'E2C')
dot.edge('E3A', 'E3B')
dot.edge('E3A', 'E3C')

# Generar y guardar la imagen en el directorio actual
dot.render('anexo1_arbol_problemas_HD', view=False, cleanup=True)
print("Generación completada: 'anexo1_arbol_problemas_HD.png' creado con éxito.")
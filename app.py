# Jerónimo Martins Colombia — Nómina 2025
# Creado por Jeysshon
# Parsing posicional + matching con MASTERDATA. Incluye SALARIO en Netos y Preno_Convertida.

import streamlit as st
import pandas as pd
import re
from datetime import datetime
import io

# -------------------------------
# Configuración de página
# -------------------------------
st.set_page_config(
    page_title="JMC · Nómina 2025 — Consolidación",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------
# Estilos mejorados y atractivos
# -------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Variables CSS */
    :root {
        --primary-color: #1e40af;
        --secondary-color: #3b82f6;
        --accent-color: #06b6d4;
        --success-color: #10b981;
        --warning-color: #f59e0b;
        --error-color: #ef4444;
        --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --gradient-secondary: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --gradient-success: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        --glass-bg: rgba(255, 255, 255, 0.1);
        --glass-border: rgba(255, 255, 255, 0.2);
        --shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
    }

    /* Reset y fuentes */
    .main {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Header principal */
    .main-header {
        background: var(--gradient-primary);
        padding: 2rem 1.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
        backdrop-filter: blur(10px);
        box-shadow: var(--shadow);
        border: 1px solid var(--glass-border);
    }
    
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-subtitle {
        font-size: 1.1rem;
        font-weight: 400;
        opacity: 0.9;
        margin-bottom: 0;
    }
    
    /* Tarjetas mejoradas */
    .glass-card {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid var(--glass-border);
        box-shadow: var(--shadow);
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.5);
    }
    
    /* Botones personalizados */
    .custom-button {
        background: var(--gradient-primary);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px 0 rgba(31, 38, 135, 0.4);
        text-decoration: none;
        display: inline-block;
        text-align: center;
        margin: 0.5rem;
    }
    
    .custom-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px 0 rgba(31, 38, 135, 0.6);
        background: var(--gradient-secondary);
    }
    
    .success-button {
        background: var(--gradient-success);
    }
    
    .success-button:hover {
        background: linear-gradient(135deg, #06b6d4 0%, #10b981 100%);
    }
    
    /* Métricas mejoradas */
    .metric-card {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        border: 1px solid var(--glass-border);
        box-shadow: var(--shadow);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: scale(1.02);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: var(--accent-color);
        margin-bottom: 0.5rem;
    }
    
    .metric-label {
        font-size: 0.9rem;
        font-weight: 500;
        opacity: 0.8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Sidebar mejorado */
    .sidebar .sidebar-content {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
    }
    
    /* File uploader personalizado */
    .uploadedfile {
        background: var(--glass-bg);
        border-radius: 12px;
        border: 2px dashed var(--glass-border);
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    /* Tabs personalizados */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: var(--glass-bg);
        border-radius: 12px;
        padding: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        border-radius: 8px;
        padding: 0 24px;
        font-weight: 500;
        border: none;
        background: transparent;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--gradient-primary) !important;
        color: white !important;
    }
    
    /* Alertas mejoradas */
    .stAlert {
        border-radius: 12px;
        border: none;
        box-shadow: var(--shadow);
    }
    
    /* Footer mejorado */
    .footer {
        margin-top: 3rem;
        padding: 2rem 0;
        text-align: center;
        background: var(--glass-bg);
        border-radius: 16px;
        backdrop-filter: blur(10px);
        border: 1px solid var(--glass-border);
    }
    
    .footer-text {
        font-size: 0.9rem;
        opacity: 0.8;
        margin-bottom: 0.5rem;
    }
    
    .footer-brand {
        font-weight: 600;
        background: var(--gradient-primary);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Animaciones y transiciones */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes pulse {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.7;
        }
    }
    
    .fade-in {
        animation: fadeInUp 0.6s ease-out;
    }
    
    .pulse {
        animation: pulse 2s infinite;
    }
    
    /* Responsivo Mobile First */
    @media (max-width: 768px) {
        .main-header {
            padding: 1.5rem 1rem;
            margin-bottom: 1.5rem;
        }
        
        .glass-card {
            padding: 1rem;
            margin: 0.8rem 0;
        }
        
        .custom-button {
            width: 100%;
            margin: 0.25rem 0;
            min-width: unset;
        }
        
        .metric-card {
            margin-bottom: 0.8rem;
        }
        
        .feature-tag {
            width: calc(50% - 0.5rem);
            text-align: center;
        }
        
        .footer {
            padding: 1.5rem 1rem;
            margin-top: 2rem;
        }
    }
    
    @media (max-width: 480px) {
        .main-header {
            padding: 1rem 0.8rem;
        }
        
        .glass-card {
            padding: 0.8rem;
        }
        
        .metric-card {
            padding: 1rem;
        }
        
        .feature-tag {
            width: 100%;
            margin: 0.2rem 0;
        }
    }
    
    /* Tablet */
    @media (min-width: 769px) and (max-width: 1024px) {
        .main-title {
            font-size: 2.2rem;
        }
        
        .main-subtitle {
            font-size: 1rem;
        }
        
        .custom-button {
            min-width: 140px;
        }
    }
    
    /* Desktop grande */
    @media (min-width: 1200px) {
        .main-header {
            padding: 2.5rem 2rem;
        }
        
        .glass-card {
            padding: 2rem;
        }
        
        .metric-card {
            padding: 2rem;
        }
    }
    
    /* Ocultar elementos Streamlit */
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    header[data-testid="stHeader"] {display: none;}
    
    /* Progress bar adaptivo */
    .stProgress > div > div > div > div {
        background: var(--gradient-primary);
        border-radius: 10px;
        transition: all 0.3s ease;
    }
    
    /* DataFrames adaptativos */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: var(--shadow);
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        border: 1px solid var(--glass-border);
    }
    
    .stDataFrame [data-testid="stDataFrame"] > div {
        background-color: var(--bg-primary) !important;
        color: var(--text-primary) !important;
    }
    
    /* Streamlit components override */
    .stSelectbox > div > div {
        background-color: var(--glass-bg) !important;
        color: var(--text-primary) !important;
        border-color: var(--glass-border) !important;
    }
    
    .stFileUploader > div {
        background-color: var(--glass-bg) !important;
        border-color: var(--glass-border) !important;
        color: var(--text-primary) !important;
    }
    
    /* Spinner personalizado */
    .stSpinner > div {
        border-color: var(--accent-color) !important;
    }
    
    /* Success/Error messages */
    .stSuccess {
        background-color: rgba(16, 185, 129, 0.1) !important;
        color: var(--success-color) !important;
        border-color: var(--success-color) !important;
    }
    
    .stError {
        background-color: rgba(239, 68, 68, 0.1) !important;
        color: var(--error-color) !important;
        border-color: var(--error-color) !important;
    }
    
    .stWarning {
        background-color: rgba(245, 158, 11, 0.1) !important;
        color: var(--warning-color) !important;
        border-color: var(--warning-color) !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# Utilidades (sin cambios)
# -------------------------------
def safe_slice(s: str, a: int, b: int) -> str:
    if a >= len(s): return ""
    return s[a:b]

def to_num(v):
    try:
        if pd.isna(v) or v == '': return 0
        return float(str(v).replace('.', '').replace(',', '.'))
    except:
        return 0

# código como primer token: /5xxx, Y###, Z###, 4 dígitos o 3–5 dígitos
CODIGO_REGEX = re.compile(r'^\s*(/5\d+|[YZ]\d{3}|\d{4}|\d{3,5})')

def extraer_codigo_y_concepto(linea: str):
    texto = linea.replace('\t', ' ')
    m = CODIGO_REGEX.match(texto)
    if m:
        codigo = m.group(1).strip()
        idx_fin = m.end()
    else:
        parts = texto.strip().split()
        codigo = parts[0] if parts else ""
        idx_fin = texto.find(codigo) + len(codigo) if codigo else 0
    concepto = texto[idx_fin:50].strip()
    return codigo, concepto

# -------- SALARIO ROBUSTO ----------
def _normalize(s: str) -> str:
    s = s.lower().strip()
    s = s.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
    return re.sub(r'[^a-z0-9]', '', s)

CANDIDATOS_SALARIO = [
    'importe','importebase','salario','salariobase','sueldo','sueldobase',
    'basico','basicos','basicointegral','remuneracion','remuneraciones','valorbase'
]

def adjuntar_salario(df_merged: pd.DataFrame) -> pd.DataFrame:
    """Crea/normaliza columna SALARIO desde MASTERDATA, aunque tenga espacios o nombres raros."""
    if 'SALARIO' in df_merged.columns:
        return df_merged

    norm_map = {col: _normalize(col) for col in df_merged.columns}
    elegido = None
    # prioridad: coincidencia contiene alguno de los candidatos
    for col, key in norm_map.items():
        if any(cand in key for cand in CANDIDATOS_SALARIO):
            elegido = col
            break

    if elegido:
        df_merged['SALARIO'] = df_merged[elegido]
    else:
        # si no encontró nada, crea vacío
        df_merged['SALARIO'] = pd.NA

    # tipificar a número si es string con separadores
    if df_merged['SALARIO'].dtype == object:
        df_merged['SALARIO'] = df_merged['SALARIO'].apply(lambda x: to_num(x) if isinstance(x, str) else x)

    return df_merged

# -------------------------------
# Parsing de Liquidación (conceptos) - sin cambios
# -------------------------------
def procesar_liquidacion_pipeline(contenido_archivo_txt: str) -> pd.DataFrame:
    lineas = contenido_archivo_txt.split('\n')
    df = pd.DataFrame({'Linea': [linea.strip('\r') for linea in lineas if linea.strip()]})

    def extraer_sap(linea):
        if 'Núm. Personal' in linea or 'Nm. Personal' in linea:
            m = re.search(r'Personal\.+(\d+)', linea)
            return m.group(1) if m else None
        return None

    df['SAP_Ident'] = df['Linea'].apply(extraer_sap)
    df['SAP_Ident'] = df['SAP_Ident'].fillna(method='ffill')

    def es_concepto(linea):
        s = linea.strip()
        if 'PESOS CON 00/100' in s: return False
        if len(s) <= 30: return False
        codigo, _ = extraer_codigo_y_concepto(s)
        return bool(re.match(r'^(Y|Z|9|2|/5)', codigo))

    df = df[df['Linea'].apply(es_concepto)].copy()

    def parsear(row):
        linea = row['Linea']
        codigo, concepto = extraer_codigo_y_concepto(linea)
        return {
            'CÓDIGO':   codigo,
            'CONCEPTO': concepto,
            'CANTIDAD': safe_slice(linea, 50, 70).strip(),
            'VALOR':    safe_slice(linea, 69, 89).strip(),
            'SAP':      row['SAP_Ident'],
        }

    out = pd.DataFrame([parsear(r) for _, r in df.iterrows()])
    if not out.empty:
        out['CANTIDAD'] = out['CANTIDAD'].apply(to_num)
        out['VALOR']    = out['VALOR'].apply(to_num)
        out['SAP']      = pd.to_numeric(out['SAP'], errors='coerce')
    return out

# -------------------------------
# Parsing de Netos - sin cambios
# -------------------------------
def procesar_netos_pipeline(contenido_archivo_txt: str) -> pd.DataFrame:
    lineas = contenido_archivo_txt.split('\n')
    df = pd.DataFrame({'Linea': [linea.strip() for linea in lineas if linea.strip()]})

    def extraer_sap(linea):
        if 'Núm. Personal' in linea or 'Nm. Personal' in linea:
            m = re.search(r'Personal\.+(\d+)', linea)
            return m.group(1) if m else None
        return None

    df['SAP_Ident'] = df['Linea'].apply(extraer_sap)
    df['SAP_Ident'] = df['SAP_Ident'].fillna(method='ffill')

    df = df[df['Linea'].str.contains('Total General', na=False)].copy()

    def parsear(row):
        linea = row['Linea']
        return {
            'NETO':  safe_slice(linea, 0, 32).strip(),
            'Valor': linea[-20:].strip(),
            'SAP':   row['SAP_Ident'],
        }

    out = pd.DataFrame([parsear(r) for _, r in df.iterrows()])
    if not out.empty:
        out['Valor'] = out['Valor'].apply(to_num)
        out['SAP']   = pd.to_numeric(out['SAP'], errors='coerce')
    return out

# -------------------------------
# Carga + Consolidación - sin cambios
# -------------------------------
def procesar_archivos(archivo_liquidacion, archivo_masterdata):
    try:
        contenido = archivo_liquidacion.getvalue().decode('latin-1', errors='ignore')
        df_conceptos = procesar_liquidacion_pipeline(contenido)
        df_netos     = procesar_netos_pipeline(contenido)

        if df_conceptos.empty and df_netos.empty:
            st.error("No se pudieron extraer datos del archivo de liquidación.")
            return None, None, None

        try:
            masterdata_df = pd.read_excel(archivo_masterdata, engine='openpyxl')
        except:
            masterdata_df = pd.read_excel(archivo_masterdata)

        masterdata_df.columns = masterdata_df.columns.str.strip()
        return df_conceptos, df_netos, masterdata_df

    except Exception as e:
        st.error(f"Error durante el procesamiento: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return None, None, None

# -------------------------------
# Exportación a Excel - sin cambios
# -------------------------------
def crear_excel_descarga(df_conceptos, df_netos, masterdata_df):
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # --- NETOS ---
            if df_netos is not None and masterdata_df is not None:
                netos = pd.merge(df_netos, masterdata_df, left_on='SAP', right_on='Nº pers.', how='left')
                netos = adjuntar_salario(netos)  # <-- asegurar SALARIO
                # Selección/renombrado
                cols_map = {
                    'NETO':'NETO','Valor':'Valor','SAP':'SAP',
                    'Número ID':'CÉDULA','Número de personal':'NOMBRE',
                    'División de personal':'REGIONAL','Ce.coste':'CE_COSTE',
                    'Fecha':'F. ING','Función':'CARGO','Área de personal':'NIVEL'
                }
                cols_base = [c for c in cols_map.keys() if c in netos.columns]
                df_final = netos[cols_base].rename(columns=cols_map)
                # Añadir SALARIO (ya creado) y ordenar
                df_final['SALARIO'] = netos['SALARIO']
                order = ['NETO','Valor','SAP','CÉDULA','NOMBRE','REGIONAL','CE_COSTE','SALARIO','F. ING','CARGO','NIVEL']
                df_final = df_final[[c for c in order if c in df_final.columns]]
                df_final.to_excel(writer, sheet_name='Netos', index=False)

            # --- CONCEPTOS (Preno_Convertida) ---
            if df_conceptos is not None and masterdata_df is not None:
                conceptos = pd.merge(df_conceptos, masterdata_df, left_on='SAP', right_on='Nº pers.', how='left')
                conceptos = adjuntar_salario(conceptos)  # <-- asegurar SALARIO
                cols_map = {
                    'CÓDIGO':'CÓDIGO','CONCEPTO':'CONCEPTO','CANTIDAD':'CANTIDAD','VALOR':'VALOR','SAP':'SAP',
                    'Número ID':'CÉDULA','Número de personal':'NOMBRE',
                    'Fecha':'F. INGRESO','Función':'CARGO','Área de personal':'NIVEL'
                }
                cols_base = [c for c in cols_map.keys() if c in conceptos.columns]
                df_final = conceptos[cols_base].rename(columns=cols_map)
                df_final['SALARIO'] = conceptos['SALARIO']
                order = ['CÓDIGO','CONCEPTO','CANTIDAD','VALOR','SAP','CÉDULA','NOMBRE','SALARIO','F. INGRESO','CARGO','NIVEL']
                df_final = df_final[[c for c in order if c in df_final.columns]]
                df_final.to_excel(writer, sheet_name='Preno_Convertida', index=False)

        output.seek(0)
        return output

    except Exception as e:
        st.error(f"Error al crear archivo Excel: {str(e)}")
        import traceback
        st.error(f"Traceback completo: {traceback.format_exc()}")
        return None

# -------------------------------
# UI MEJORADA
# -------------------------------
def main():
    # Header principal mejorado
    st.markdown("""
    <div class="main-header fade-in">
        <h1 class="main-title">💼 Jerónimo Martins Colombia</h1>
        <p class="main-subtitle">Sistema de Consolidación de Nómina 2025</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Descripción con tarjeta de vidrio
    st.markdown("""
    <div class="glass-card fade-in">
        <h3>🚀 Consolidación Inteligente</h3>
        <p>Sistema avanzado de <strong>parsing posicional</strong> que extrae automáticamente conceptos y netos 
        de archivos de liquidación, identifica códigos SAP y los consolida con el MASTERDATA para generar 
        reportes listos para análisis empresarial.</p>
        
        <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 1rem;">
            <span style="background: rgba(16, 185, 129, 0.1); color: #10b981; padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.9rem;">
                ✅ Parsing Automático
            </span>
            <span style="background: rgba(59, 130, 246, 0.1); color: #3b82f6; padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.9rem;">
                📊 Matching SAP
            </span>
            <span style="background: rgba(245, 158, 11, 0.1); color: #f59e0b; padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.9rem;">
                📈 Análisis Empresarial
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar mejorado
    st.sidebar.markdown("""
    <div class="glass-card">
        <h3 style="margin-top: 0;">📁 Cargar Archivos</h3>
        <p style="font-size: 0.9rem; opacity: 0.8;">Sube los archivos necesarios para iniciar el procesamiento</p>
    </div>
    """, unsafe_allow_html=True)
    
    archivo_liquidacion = st.sidebar.file_uploader(
        "📄 Archivo de liquidación (.txt)", 
        type=['txt'], 
        help="Archivo con codificación latin-1 (CP1252) que contiene los datos de liquidación."
    )
    
    archivo_masterdata = st.sidebar.file_uploader(
        "📊 MASTERDATA (.xlsx)", 
        type=['xlsx'], 
        help="Archivo Excel que debe incluir la columna 'Nº pers.' para el matching con SAP."
    )
    
    # Estado de archivos mejorado
    if archivo_liquidacion or archivo_masterdata:
        st.sidebar.markdown("### 📋 Estado de Archivos")
        if archivo_liquidacion:
            st.sidebar.markdown("""
            <div class="status-card status-success">
                ✅ <strong>Liquidación cargada</strong><br>
                <small>📄 {}</small>
            </div>
            """.format(archivo_liquidacion.name), unsafe_allow_html=True)
        if archivo_masterdata:
            formato = archivo_masterdata.name.split('.')[-1].upper()
            st.sidebar.markdown(f"""
            <div class="status-card status-success">
                ✅ <strong>MASTERDATA cargado</strong><br>
                <small>📊 {archivo_masterdata.name} ({formato})</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.sidebar.markdown("""
        <div class="status-card status-info">
            📋 <strong>Archivos pendientes</strong><br>
            <small>Carga ambos archivos para continuar</small>
        </div>
        """, unsafe_allow_html=True)

    # Botón de procesamiento mejorado
    if st.sidebar.button("🚀 Procesar Datos", type="primary", use_container_width=True):
        if archivo_liquidacion is not None and archivo_masterdata is not None:
            # Progress bar personalizado
            progress_container = st.empty()
            progress_container.markdown("""
            <div class="glass-card">
                <h4>⚡ Procesando datos...</h4>
                <p>Ejecutando parsing posicional y consolidación con MASTERDATA</p>
            </div>
            """, unsafe_allow_html=True)
            
            progress_bar = st.progress(0)
            
            with st.spinner('🔄 Analizando archivos...'):
                progress_bar.progress(25)
                df_conceptos, df_netos, masterdata_df = procesar_archivos(archivo_liquidacion, archivo_masterdata)
                progress_bar.progress(100)
                
            progress_container.empty()
            
            if df_conceptos is not None or df_netos is not None:
                st.success("🎉 ¡Procesamiento completado exitosamente!")
                
                # Métricas mejoradas
                st.markdown("### 📊 Resultados del Procesamiento")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{len(df_conceptos) if df_conceptos is not None else 0:,}</div>
                        <div class="metric-label">Conceptos Extraídos</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{len(df_netos) if df_netos is not None else 0:,}</div>
                        <div class="metric-label">Netos Procesados</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{len(masterdata_df):,}</div>
                        <div class="metric-label">Registros MASTERDATA</div>
                    </div>
                    """, unsafe_allow_html=True)

                # Tabs mejorados
                tab1, tab2 = st.tabs(["👁️ Vista Previa", "📥 Descargar Resultados"])
                
                with tab1:
                    st.markdown("### 📋 Preno_Convertida — Muestra de Datos")
                    if df_conceptos is not None:
                        st.dataframe(
                            df_conceptos.head(20), 
                            use_container_width=True,
                            height=400
                        )
                    
                    st.markdown("### 💰 Netos — Resumen")
                    if df_netos is not None:
                        st.dataframe(
                            df_netos.head(10), 
                            use_container_width=True,
                            height=300
                        )

                with tab2:
                    st.markdown("""
                    <div class="glass-card">
                        <h3>📁 Archivo Consolidado</h3>
                        <p>Descarga el archivo Excel con todas las hojas procesadas, incluyendo datos de SALARIO y matching completo con MASTERDATA.</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    excel_file = crear_excel_descarga(df_conceptos, df_netos, masterdata_df)
                    
                    if excel_file:
                        filename = f"JMC_Nomina2025_Consolidado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        
                        st.download_button(
                            label="📥 Descargar Excel Consolidado",
                            data=excel_file.getvalue(),
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary",
                            use_container_width=True
                        )
                        
                        st.markdown("""
                        <div style="background: rgba(16, 185, 129, 0.1); border-radius: 12px; padding: 1rem; margin-top: 1rem;">
                            <p style="margin: 0; color: #10b981;">
                                ✅ <strong>Archivo listo:</strong> Contiene hojas 'Netos' y 'Preno_Convertida' con datos de SALARIO integrados
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("❌ No fue posible generar el archivo de descarga")
                        
        else:
            st.warning("⚠️ Por favor, carga ambos archivos para continuar con el procesamiento")

    # Footer mejorado
    st.markdown("""
    <div class="footer">
        <div class="footer-text">
            Desarrollado con ❤️ por <span class="footer-brand">Jeysshon</span>
        </div>
        <div style="font-size: 0.8rem; opacity: 0.6;">
            Jerónimo Martins Colombia · Sistema de Nómina 2025
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

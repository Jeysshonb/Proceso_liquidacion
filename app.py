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
# Estilos simples
# -------------------------------
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 1.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .main-subtitle {
        font-size: 1.1rem;
        margin-bottom: 0;
        opacity: 0.9;
    }
    
    .info-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .feature-tag {
        display: inline-block;
        padding: 0.5rem 1rem;
        margin: 0.25rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 500;
    }
    
    .tag-green { background: rgba(16, 185, 129, 0.2); color: #10b981; }
    .tag-blue { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
    .tag-orange { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
    
    .metric-box {
        text-align: center;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        background: rgba(255, 255, 255, 0.05);
    }
    
    .metric-number {
        font-size: 2rem;
        font-weight: bold;
        color: #3b82f6;
    }
    
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.7;
        margin-top: 0.5rem;
    }
    
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
</style>
""", unsafe_allow_html=True)

# -------------------------------
# Utilidades
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

def _normalize(s: str) -> str:
    s = s.lower().strip()
    s = s.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
    return re.sub(r'[^a-z0-9]', '', s)

CANDIDATOS_SALARIO = [
    'importe','importebase','salario','salariobase','sueldo','sueldobase',
    'basico','basicos','basicointegral','remuneracion','remuneraciones','valorbase'
]

def adjuntar_salario(df_merged: pd.DataFrame) -> pd.DataFrame:
    if 'SALARIO' in df_merged.columns:
        return df_merged

    norm_map = {col: _normalize(col) for col in df_merged.columns}
    elegido = None
    for col, key in norm_map.items():
        if any(cand in key for cand in CANDIDATOS_SALARIO):
            elegido = col
            break

    if elegido:
        df_merged['SALARIO'] = df_merged[elegido]
    else:
        df_merged['SALARIO'] = pd.NA

    if df_merged['SALARIO'].dtype == object:
        df_merged['SALARIO'] = df_merged['SALARIO'].apply(lambda x: to_num(x) if isinstance(x, str) else x)

    return df_merged

# -------------------------------
# Parsing de Liquidación
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
# Parsing de Netos
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
# Procesamiento principal
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
            archivo_nombre = archivo_masterdata.name.lower()
            
            if archivo_nombre.endswith('.csv'):
                masterdata_df = pd.read_csv(archivo_masterdata, encoding='utf-8')
            elif archivo_nombre.endswith('.xlsb'):
                masterdata_df = pd.read_excel(archivo_masterdata, engine='pyxlsb')
            elif archivo_nombre.endswith(('.xlsx', '.xls', '.xlsm')):
                try:
                    masterdata_df = pd.read_excel(archivo_masterdata, engine='openpyxl')
                except:
                    masterdata_df = pd.read_excel(archivo_masterdata, engine='xlrd')
            else:
                masterdata_df = pd.read_excel(archivo_masterdata)
                
        except Exception as e:
            st.error(f"Error al leer MASTERDATA: {str(e)}")
            return None, None, None

        masterdata_df.columns = masterdata_df.columns.str.strip()
        
        if 'Nº pers.' not in masterdata_df.columns:
            st.error("No se encontró la columna 'Nº pers.' en MASTERDATA")
            return None, None, None
            
        return df_conceptos, df_netos, masterdata_df

    except Exception as e:
        st.error(f"Error durante el procesamiento: {str(e)}")
        return None, None, None

# -------------------------------
# Exportación a Excel
# -------------------------------
def crear_excel_descarga(df_conceptos, df_netos, masterdata_df):
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if df_netos is not None and masterdata_df is not None:
                netos = pd.merge(df_netos, masterdata_df, left_on='SAP', right_on='Nº pers.', how='left')
                netos = adjuntar_salario(netos)
                cols_map = {
                    'NETO':'NETO','Valor':'Valor','SAP':'SAP',
                    'Número ID':'CÉDULA','Número de personal':'NOMBRE',
                    'División de personal':'REGIONAL','Ce.coste':'CE_COSTE',
                    'Fecha':'F. ING','Función':'CARGO','Área de personal':'NIVEL'
                }
                cols_base = [c for c in cols_map.keys() if c in netos.columns]
                df_final = netos[cols_base].rename(columns=cols_map)
                df_final['SALARIO'] = netos['SALARIO']
                order = ['NETO','Valor','SAP','CÉDULA','NOMBRE','REGIONAL','CE_COSTE','SALARIO','F. ING','CARGO','NIVEL']
                df_final = df_final[[c for c in order if c in df_final.columns]]
                df_final.to_excel(writer, sheet_name='Netos', index=False)

            if df_conceptos is not None and masterdata_df is not None:
                conceptos = pd.merge(df_conceptos, masterdata_df, left_on='SAP', right_on='Nº pers.', how='left')
                conceptos = adjuntar_salario(conceptos)
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
        return None

# -------------------------------
# Interfaz principal
# -------------------------------
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1 class="main-title">💼 Jerónimo Martins Colombia</h1>
        <p class="main-subtitle">Sistema de Consolidación de Nómina 2025</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Descripción
    st.markdown("""
    <div class="info-card">
        <h3>🚀 Consolidación Inteligente</h3>
        <p>Sistema avanzado de parsing posicional que extrae automáticamente conceptos y netos 
        de archivos de liquidación, identifica códigos SAP y los consolida con el MASTERDATA.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Features
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<span class="feature-tag tag-green">✅ Parsing Automático</span>', unsafe_allow_html=True)
    with col2:
        st.markdown('<span class="feature-tag tag-blue">📊 Matching SAP</span>', unsafe_allow_html=True)
    with col3:
        st.markdown('<span class="feature-tag tag-orange">📈 Análisis Empresarial</span>', unsafe_allow_html=True)
    with col4:
        st.markdown('<span class="feature-tag tag-blue">📁 Multi-formato</span>', unsafe_allow_html=True)

    # Sidebar
    st.sidebar.header("📁 Cargar Archivos")
    
    archivo_liquidacion = st.sidebar.file_uploader(
        "📄 Archivo de liquidación (.txt)", 
        type=['txt']
    )
    
    archivo_masterdata = st.sidebar.file_uploader(
        "📊 MASTERDATA", 
        type=['xlsx', 'xlsb', 'xls', 'xlsm', 'csv']
    )
    
    # Estado de archivos
    if archivo_liquidacion:
        st.sidebar.success("✅ Liquidación cargada")
    if archivo_masterdata:
        st.sidebar.success("✅ MASTERDATA cargado")

    # Botón de procesamiento
    if st.sidebar.button("🚀 Procesar Datos", type="primary", use_container_width=True):
        if archivo_liquidacion and archivo_masterdata:
            with st.spinner('Procesando archivos...'):
                df_conceptos, df_netos, masterdata_df = procesar_archivos(archivo_liquidacion, archivo_masterdata)
            
            if df_conceptos is not None or df_netos is not None:
                st.success("✅ Procesamiento completado")
                
                # Métricas
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-number">{len(df_conceptos) if df_conceptos is not None else 0:,}</div>
                        <div class="metric-label">Conceptos</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-number">{len(df_netos) if df_netos is not None else 0:,}</div>
                        <div class="metric-label">Netos</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-number">{len(masterdata_df):,}</div>
                        <div class="metric-label">MASTERDATA</div>
                    </div>
                    """, unsafe_allow_html=True)

                # Tabs
                tab1, tab2 = st.tabs(["👁️ Vista Previa", "📥 Descargar"])
                
                with tab1:
                    if df_conceptos is not None:
                        st.subheader("📋 Conceptos")
                        st.dataframe(df_conceptos.head(10), use_container_width=True)
                    
                    if df_netos is not None:
                        st.subheader("💰 Netos")
                        st.dataframe(df_netos.head(10), use_container_width=True)

                with tab2:
                    excel_file = crear_excel_descarga(df_conceptos, df_netos, masterdata_df)
                    
                    if excel_file:
                        filename = f"JMC_Nomina2025_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        
                        st.download_button(
                            label="📥 Descargar Excel",
                            data=excel_file.getvalue(),
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary"
                        )
        else:
            st.warning("⚠️ Carga ambos archivos para continuar")

    # Footer simple
    st.markdown("---")
    st.markdown("**Desarrollado por Jeysshon** | Jerónimo Martins Colombia 2025")

if __name__ == "__main__":
    main()

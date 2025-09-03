import streamlit as st
import pandas as pd
import re
from datetime import datetime
import io

# =========================
# Configuración de la página
# =========================
st.set_page_config(
    page_title="JMC · Nómina 2025 — Parsing & Matching",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# Estilos de “fina coquetería”
# =========================
STYLES = """
<style>
/* Badges y toques suaves */
.badges {display:flex; gap:.5rem; flex-wrap:wrap; margin-top:-8px; margin-bottom:8px;}
.badge {
  background: linear-gradient(135deg,#10b981 0%, #06b6d4 100%);
  color: white; padding: 3px 10px; border-radius: 999px;
  font-size: 12px; font-weight: 700; letter-spacing:.2px;
}
.subtle {
  border: 1px solid rgba(255,255,255,.08);
  background: rgba(16,185,129,.06);
  border-radius: 12px; padding: 12px 14px; margin: 6px 0 14px 0;
}
footer {visibility:hidden}
.small {font-size:12px; opacity:.85}
.hr {height:1px; border:none; background:rgba(255,255,255,.08); margin: 12px 0 16px 0;}
</style>
"""
st.markdown(STYLES, unsafe_allow_html=True)

# =========================
# Helpers
# =========================
def limpiar_columnas_duplicadas(df):
    """Elimina columnas duplicadas de un DataFrame."""
    if df is None or df.empty:
        return df
    if df.columns.duplicated().any():
        st.warning(f"⚠️ Columnas duplicadas encontradas: {df.columns[df.columns.duplicated()].tolist()}")
        df_limpio = df.loc[:, ~df.columns.duplicated()]
        st.success(f"✅ DataFrame limpiado: {len(df.columns)} -> {len(df_limpio.columns)} columnas")
        return df_limpio
    return df

def safe_slice(s: str, a: int, b: int) -> str:
    """Devuelve s[a:b] sin romper si la línea es corta."""
    if a >= len(s):
        return ""
    return s[a:b]

# --- Parsing robusto de CÓDIGO + CONCEPTO ---
# Acepta: /5xxx, Y###, Z###, 4 dígitos, o bloques 3–5 dígitos.
CODIGO_REGEX = re.compile(r'^\s*(/5\d+|[YZ]\d{3}|\d{4}|\d{3,5})')

def extraer_codigo_y_concepto(linea: str):
    """
    CÓDIGO: primer token válido al inicio (no ancho fijo).
    CONCEPTO: texto entre el fin del CÓDIGO y la col 50 (previo a CANTIDAD).
    """
    texto = linea.replace('\t', ' ')  # evitar "Apoy\t o ..."
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

# =========================
# Parsing de archivos
# =========================
def procesar_liquidacion_power_query_style(contenido_archivo):
    """Parsing lineal + tokenización de conceptos + matching SAP."""
    lineas = contenido_archivo.split('\n')
    df_inicial = pd.DataFrame({'Linea': [linea.strip('\r') for linea in lineas if linea.strip()]})

    # SAP identificado por cabecera y propagado hacia abajo (forward-fill)
    def extraer_sap(linea):
        if 'Núm. Personal' in linea or 'Nm. Personal' in linea:
            m = re.search(r'Personal\.+(\d+)', linea)
            return m.group(1) if m else None
        return None

    df_inicial['SAP_Ident'] = df_inicial['Linea'].apply(extraer_sap)
    df_inicial['SAP_Ident'] = df_inicial['SAP_Ident'].fillna(method='ffill')

    # Filtrado de líneas que representan conceptos válidos
    def filtrar_conceptos(linea):
        s = linea.strip()
        if 'PESOS CON 00/100' in s:
            return False
        if len(s) <= 30:
            return False
        codigo, _ = extraer_codigo_y_concepto(s)
        return bool(re.match(r'^(Y|Z|9|2|/5)', codigo))

    df_conceptos = df_inicial[df_inicial['Linea'].apply(filtrar_conceptos)].copy()

    # Parseo final (con CÓDIGO/CONCEPTO robustos)
    def parsear_partes(row):
        linea = row['Linea']
        codigo, concepto = extraer_codigo_y_concepto(linea)
        return {
            'CÓDIGO': codigo,
            'CONCEPTO': concepto,
            'CANTIDAD': safe_slice(linea, 50, 70).strip(),
            'VALOR':   safe_slice(linea, 69, 89).strip(),
            'SAP':     row['SAP_Ident']
        }

    partes_list = [parsear_partes(r) for _, r in df_conceptos.iterrows()]
    df_parseado = pd.DataFrame(partes_list)

    # Tipificación
    def to_num(v):
        try:
            if pd.isna(v) or v == '':
                return 0
            return float(str(v).replace('.', '').replace(',', '.'))
        except:
            return 0

    df_parseado['CANTIDAD'] = df_parseado['CANTIDAD'].apply(to_num)
    df_parseado['VALOR']    = df_parseado['VALOR'].apply(to_num)
    df_parseado['SAP']      = pd.to_numeric(df_parseado['SAP'], errors='coerce')
    return df_parseado

def procesar_netos_power_query_style(contenido_archivo):
    """Extracción de NETOS a partir de líneas marcadas como 'Total General'."""
    lineas = contenido_archivo.split('\n')
    df_inicial = pd.DataFrame({'Linea': [linea.strip() for linea in lineas if linea.strip()]})

    def extraer_sap(linea):
        if 'Núm. Personal' in linea or 'Nm. Personal' in linea:
            m = re.search(r'Personal\.+(\d+)', linea)
            return m.group(1) if m else None
        return None

    df_inicial['SAP_Ident'] = df_inicial['Linea'].apply(extraer_sap)
    df_inicial['SAP_Ident'] = df_inicial['SAP_Ident'].fillna(method='ffill')

    df_netos = df_inicial[df_inicial['Linea'].str.contains('Total General', na=False)].copy()

    def parsear_netos(row):
        linea = row['Linea']
        return {
            'NETO':  safe_slice(linea, 0, 32).strip(),
            'Valor': linea[-20:].strip(),
            'SAP':   row['SAP_Ident']
        }

    netos_list = [parsear_netos(r) for _, r in df_netos.iterrows()]
    df = pd.DataFrame(netos_list)

    def to_num(v):
        try:
            if pd.isna(v) or v == '':
                return 0
            return float(str(v).replace('.', '').replace(',', '.'))
        except:
            return 0

    df['Valor'] = df['Valor'].apply(to_num)
    df['SAP']   = pd.to_numeric(df['SAP'], errors='coerce')
    return df

def procesar_archivos(archivo_liquidacion, archivo_masterdata):
    """
    Pipeline de:
    1) parsing de conceptos y netos,
    2) identificación/propagación de SAP,
    3) consolidación con MASTERDATA.
    """
    try:
        contenido = archivo_liquidacion.getvalue().decode('latin-1', errors='ignore')
        df_conceptos = procesar_liquidacion_power_query_style(contenido)
        df_netos = procesar_netos_power_query_style(contenido)

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

def crear_excel_descarga(df_conceptos, df_netos, masterdata_df):
    """Genera archivo XLSX con hojas de NETOS y CONCEPTOS consolidadas."""
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # --- HOJA NETOS ---
            if df_netos is not None and masterdata_df is not None:
                netos = pd.merge(
                    df_netos, masterdata_df,
                    left_on='SAP', right_on='Nº pers.', how='left'
                )
                cols_map = {
                    'NETO': 'NETO', 'Valor': 'Valor', 'SAP': 'SAP',
                    'Número ID': 'CÉDULA', 'Número de personal': 'NOMBRE',
                    'División de personal': 'REGIONAL', 'Ce.coste': 'CE_COSTE',
                    '     Importe': 'SALARIO', 'Fecha': 'F. ING',
                    'Función': 'CARGO', 'Área de personal': 'NIVEL'
                }
                cols_ok = {k: v for k, v in cols_map.items() if k in netos.columns}
                if cols_ok:
                    df_final = netos[list(cols_ok.keys())].rename(columns=cols_ok)
                    order = ['NETO','Valor','SAP','CÉDULA','NOMBRE','REGIONAL','CE_COSTE','SALARIO','F. ING','CARGO','NIVEL']
                    df_final = df_final[[c for c in order if c in df_final.columns]]
                    df_final.to_excel(writer, sheet_name='Netos', index=False)

            # --- HOJA CONCEPTOS ---
            if df_conceptos is not None and masterdata_df is not None:
                conceptos = pd.merge(
                    df_conceptos, masterdata_df,
                    left_on='SAP', right_on='Nº pers.', how='left'
                )
                cols_map = {
                    'CÓDIGO': 'CÓDIGO', 'CONCEPTO': 'CONCEPTO',
                    'CANTIDAD': 'CANTIDAD', 'VALOR': 'VALOR', 'SAP': 'SAP',
                    'Número ID': 'CÉDULA', 'Número de personal': 'NOMBRE',
                    '     Importe': 'SALARIO', 'Fecha': 'F. INGRESO',
                    'Función': 'CARGO', 'Área de personal': 'NIVEL'
                }
                cols_ok = {k: v for k, v in cols_map.items() if k in conceptos.columns}
                if cols_ok:
                    df_final = conceptos[list(cols_ok.keys())].rename(columns=cols_ok)
                    order = ['CÓDIGO','CONCEPTO','CANTIDAD','VALOR','SAP','CÉDULA','NOMBRE','SALARIO','F. INGRESO','CARGO','NIVEL']
                    df_final = df_final[[c for c in order if c in df_final.columns]]
                    df_final.to_excel(writer, sheet_name='Conceptos', index=False)

        output.seek(0)
        return output
    except Exception as e:
        st.error(f"Error al crear archivo Excel: {str(e)}")
        import traceback
        st.error(f"Traceback completo: {traceback.format_exc()}")
        return None

# =========================
# UI principal
# =========================
def main():
    st.title("📊 Jerónimo Martins Colombia — Nómina 2025")
    st.markdown("""
<div class="badges">
  <span class="badge">Creado por Jeysshon</span>
  <span class="badge">Parsing & Matching</span>
  <span class="badge">HR Data · Toma de decisiones</span>
</div>
<div class="subtle">
Este módulo consolida **conceptos de nómina y netos** mediante un pipeline de parsing posicional, 
tokenización del **código de concepto**, identificación/propagación de **SAP ID** y matching con **MASTERDATA**. 
El resultado es un **dataset listo para análisis** y soporte a decisiones.
</div>
""", unsafe_allow_html=True)

    st.sidebar.header("📁 Cargar archivos")
    archivo_liquidacion = st.sidebar.file_uploader(
        "📄 Archivo de liquidación (.txt)",
        type=['txt'],
        help="Usa el .txt exportado con codificación latin-1 (CP1252)."
    )
    archivo_masterdata = st.sidebar.file_uploader(
        "📊 MASTERDATA (.xlsx)",
        type=['xlsx'],
        help="Debe contener la columna 'Nº pers.' para el matching."
    )

    if st.sidebar.button("🚀 Procesar", type="primary"):
        if archivo_liquidacion is not None and archivo_masterdata is not None:
            with st.spinner('⏳ Ejecutando pipeline de parsing y matching...'):
                df_conceptos, df_netos, masterdata_df = procesar_archivos(
                    archivo_liquidacion, archivo_masterdata
                )

                if df_conceptos is not None or df_netos is not None:
                    st.success("✅ ¡Procesamiento completado!")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📦 Conceptos extraídos", len(df_conceptos) if df_conceptos is not None else 0)
                    with col2:
                        st.metric("💰 Netos extraídos", len(df_netos) if df_netos is not None else 0)
                    with col3:
                        st.metric("👥 Registros MASTERDATA", len(masterdata_df))

                    tab1, tab2 = st.tabs(["🔍 Vista previa", "📥 Descargar"])
                    with tab1:
                        st.markdown("**Conceptos (primeras 20 filas):**")
                        if df_conceptos is not None:
                            st.dataframe(df_conceptos.head(20), use_container_width=True)
                        st.markdown("**Netos (primeras 10 filas):**")
                        if df_netos is not None:
                            st.dataframe(df_netos.head(10), use_container_width=True)

                    with tab2:
                        st.subheader("Descargar archivo procesado")
                        excel_file = crear_excel_descarga(df_conceptos, df_netos, masterdata_df)
                        if excel_file:
                            st.download_button(
                                label="📁 Descargar Excel (Dataset consolidado)",
                                data=excel_file.getvalue(),
                                file_name=f"JMC_Nomina2025_DatasetConsolidado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                type="primary"
                            )
                            st.success("✅ Dataset consolidado generado con éxito.")
                        else:
                            st.error("❌ No fue posible generar el archivo.")
        else:
            st.warning("⚠️ Carga ambos archivos para continuar.")

    # Panel lateral técnico (sin nombrar ‘Power Query’)
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧩 Especificaciones técnicas")
    st.sidebar.markdown("""
- **Codificación**: latin-1 (CP1252)  
- **Identificación SAP**: detección por cabecera y *forward-fill*  
- **Conceptos**: tokenización del **CÓDIGO** (Y*, Z*, 9*, 2*, /5*)  
- **Offsets**: `CONCEPTO` (fin de código → col 50), `CANTIDAD` (50–70), `VALOR` (69–89)  
- **Matching**: unión con MASTERDATA por **SAP = 'Nº pers.'**  
- **Salida**: Excel con hojas **Netos** y **Conceptos**
""")

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.caption("Creado por Jeysshon · Jerónimo Martins Colombia · Nómina 2025")

if __name__ == "__main__":
    main()

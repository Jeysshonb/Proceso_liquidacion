# Jerónimo Martins Colombia — Nómina 2025
# Creado por Jeysshon
# Parsing posicional + matching con MASTERDATA. Incluye SALARIO en Netos y Preno_Convertida.

import streamlit as st
import pandas as pd
import re
from datetime import datetime
import io

# -------------------------------
# Configuración mínima de página
# -------------------------------
st.set_page_config(
    page_title="JMC · Nómina 2025 — Consolidación",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------
# Estilos sobrios
# -------------------------------
st.markdown("""
<style>
  .soft-card {border:1px solid rgba(255,255,255,.08); border-radius:12px; padding:14px 16px; margin:10px 0 18px 0; background:rgba(120,120,120,.04);}
  .hr {height:1px; background:rgba(255,255,255,.08); margin:10px 0 14px 0;}
  .footnote {font-size:12px; opacity:.75;}
  footer {visibility:hidden;}
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
# Parsing de Liquidación (conceptos)
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
# Carga + Consolidación
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
# Exportación a Excel (incluye SALARIO)
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
# UI
# -------------------------------
def main():
    st.title("Jerónimo Martins Colombia — Nómina 2025")
    st.markdown("""
    <div class="soft-card">
      Consolidación de <strong>conceptos</strong> y <strong>netos</strong> mediante parsing posicional,
      identificación/propagación de <strong>SAP ID</strong> y unión con <strong>MASTERDATA</strong>.
      Salida: dataset listo para análisis y soporte a decisiones.
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.header("Cargar archivos")
    archivo_liquidacion = st.sidebar.file_uploader("Archivo de liquidación (.txt)", type=['txt'], help="Codificación latin-1 (CP1252).")
    archivo_masterdata = st.sidebar.file_uploader("MASTERDATA (.xlsx)", type=['xlsx'], help="Debe incluir 'Nº pers.' para el matching.")

    if st.sidebar.button("Procesar", type="primary"):
        if archivo_liquidacion is not None and archivo_masterdata is not None:
            with st.spinner('Ejecutando parsing y matching...'):
                df_conceptos, df_netos, masterdata_df = procesar_archivos(archivo_liquidacion, archivo_masterdata)
            if df_conceptos is not None or df_netos is not None:
                st.success("Procesamiento completado.")
                c1, c2, c3 = st.columns(3)
                c1.metric("Conceptos extraídos", len(df_conceptos) if df_conceptos is not None else 0)
                c2.metric("Netos extraídos", len(df_netos) if df_netos is not None else 0)
                c3.metric("Registros MASTERDATA", len(masterdata_df))

                tab1, tab2 = st.tabs(["Vista previa", "Descargar"])
                with tab1:
                    st.subheader("Preno_Convertida — primeras 20 filas")
                    if df_conceptos is not None:
                        st.dataframe(df_conceptos.head(20), use_container_width=True)
                    st.subheader("Netos — primeras 10 filas")
                    if df_netos is not None:
                        st.dataframe(df_netos.head(10), use_container_width=True)

                with tab2:
                    excel_file = crear_excel_descarga(df_conceptos, df_netos, masterdata_df)
                    if excel_file:
                        st.download_button(
                            label="Descargar Excel (consolidado)",
                            data=excel_file.getvalue(),
                            file_name=f"JMC_Nomina2025_Consolidado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary"
                        )
                        st.caption("Archivo consolidado con Netos y Preno_Convertida (incluye SALARIO).")
                    else:
                        st.error("No fue posible generar el archivo.")
        else:
            st.warning("Carga ambos archivos para continuar.")

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.caption("Creado por Jeysshon · Jerónimo Martins Colombia · Nómina 2025")

if __name__ == "__main__":
    main()

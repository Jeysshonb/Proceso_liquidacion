import streamlit as st
import pandas as pd
import re
from datetime import datetime
import io

# Configuración de la página
st.set_page_config(
    page_title="Procesador de Liquidación y MASTERDATA",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def limpiar_columnas_duplicadas(df):
    """
    Elimina columnas duplicadas de un DataFrame
    """
    if df is None or df.empty:
        return df
    
    if df.columns.duplicated().any():
        st.warning(f"⚠️ Columnas duplicadas encontradas: {df.columns[df.columns.duplicated()].tolist()}")
        df_limpio = df.loc[:, ~df.columns.duplicated()]
        st.success(f"✅ DataFrame limpiado: {len(df.columns)} -> {len(df_limpio.columns)} columnas")
        return df_limpio
    
    return df

def procesar_liquidacion_power_query_style(contenido_archivo):
    """
    Replica exactamente los pasos del Power Query para procesar liquidación
    """
    # Paso 1: Separar por líneas como CSV con delimiter ";"
    lineas = contenido_archivo.split('\n')
    
    # Crear DataFrame inicial con columna "Linea"
    df_inicial = pd.DataFrame({'Linea': [linea.strip() for linea in lineas if linea.strip()]})
    
    # Paso 2: Agregar columna SAP_Ident
    def extraer_sap(linea):
        if 'Núm. Personal' in linea or 'Nm. Personal' in linea:
            # Extraer números después de "Personal"
            match = re.search(r'Personal\.+(\d+)', linea)
            return match.group(1) if match else None
        return None
    
    df_inicial['SAP_Ident'] = df_inicial['Linea'].apply(extraer_sap)
    
    # Paso 3: Fill Down - Rellenar SAP_Ident hacia abajo
    df_inicial['SAP_Ident'] = df_inicial['SAP_Ident'].fillna(method='ffill')
    
    # Paso 4: Filtrar filas - Replicar la lógica del Power Query
    def filtrar_conceptos(linea):
        linea = linea.strip()
        if 'PESOS CON 00/100' in linea:
            return False
        if len(linea) <= 30:
            return False
        
        codigo = linea[:4].strip()
        return (codigo.startswith('Y') or 
                codigo.startswith('Z') or 
                codigo.startswith('9') or 
                codigo.startswith('2') or 
                codigo.startswith('/5'))
    
    df_conceptos = df_inicial[df_inicial['Linea'].apply(filtrar_conceptos)].copy()
    
    # Paso 5: Parsear las partes - Replicar exactamente las posiciones del Power Query
    def parsear_partes(row):
        linea = row['Linea']
        return {
            'CÓDIGO': linea[:11].strip(),
            'CONCEPTO': linea[11:46].strip(),
            'CANTIDAD': linea[50:70].strip(),
            'VALOR': linea[69:89].strip(),
            'SAP': row['SAP_Ident']
        }
    
    partes_list = []
    for _, row in df_conceptos.iterrows():
        partes = parsear_partes(row)
        partes_list.append(partes)
    
    df_parseado = pd.DataFrame(partes_list)
    
    # Paso 6: Convertir tipos de datos
    def safe_convert_number(val):
        try:
            if pd.isna(val) or val == '':
                return 0
            # Limpiar formato de números (quitar puntos y comas)
            val_clean = str(val).replace('.', '').replace(',', '.')
            return float(val_clean)
        except:
            return 0
    
    df_parseado['CANTIDAD'] = df_parseado['CANTIDAD'].apply(safe_convert_number)
    df_parseado['VALOR'] = df_parseado['VALOR'].apply(safe_convert_number)
    df_parseado['SAP'] = pd.to_numeric(df_parseado['SAP'], errors='coerce')
    
    return df_parseado

def procesar_netos_power_query_style(contenido_archivo):
    """
    Replica exactamente los pasos del Power Query para procesar NETOS
    """
    # Paso 1: Separar por líneas
    lineas = contenido_archivo.split('\n')
    df_inicial = pd.DataFrame({'Linea': [linea.strip() for linea in lineas if linea.strip()]})
    
    # Paso 2: Agregar columna SAP_Ident
    def extraer_sap(linea):
        if 'Núm. Personal' in linea or 'Nm. Personal' in linea:
            match = re.search(r'Personal\.+(\d+)', linea)
            return match.group(1) if match else None
        return None
    
    df_inicial['SAP_Ident'] = df_inicial['Linea'].apply(extraer_sap)
    
    # Paso 3: Fill Down
    df_inicial['SAP_Ident'] = df_inicial['SAP_Ident'].fillna(method='ffill')
    
    # Paso 4: Filtrar solo líneas que contienen "Total General"
    df_netos = df_inicial[df_inicial['Linea'].str.contains('Total General', na=False)].copy()
    
    # Paso 5: Parsear las partes para NETOS
    def parsear_netos(row):
        linea = row['Linea']
        return {
            'NETO': linea[:32].strip(),  # Concepto (Total General:)
            'Valor': linea[-20:].strip(),  # Últimos 20 caracteres para el valor
            'SAP': row['SAP_Ident']
        }
    
    netos_list = []
    for _, row in df_netos.iterrows():
        partes = parsear_netos(row)
        netos_list.append(partes)
    
    df_netos_parseado = pd.DataFrame(netos_list)
    
    # Convertir tipos
    def safe_convert_number(val):
        try:
            if pd.isna(val) or val == '':
                return 0
            val_clean = str(val).replace('.', '').replace(',', '.')
            return float(val_clean)
        except:
            return 0
    
    df_netos_parseado['Valor'] = df_netos_parseado['Valor'].apply(safe_convert_number)
    df_netos_parseado['SAP'] = pd.to_numeric(df_netos_parseado['SAP'], errors='coerce')
    
    return df_netos_parseado

def procesar_archivos(archivo_liquidacion, archivo_masterdata):
    """
    Procesa los archivos replicando exactamente la lógica de Power Query
    """
    try:
        # 1. Leer archivo de Liquidación
        contenido_liquidacion = archivo_liquidacion.getvalue().decode('latin-1', errors='ignore')
        
        # 2. Procesar conceptos (Preno_Convertida)
        df_conceptos = procesar_liquidacion_power_query_style(contenido_liquidacion)
        
        # 3. Procesar netos
        df_netos = procesar_netos_power_query_style(contenido_liquidacion)
        
        if df_conceptos.empty and df_netos.empty:
            st.error("No se pudieron extraer datos del archivo de liquidación")
            return None, None, None
        
        # 4. Leer archivo MASTERDATA
        try:
            masterdata_df = pd.read_excel(archivo_masterdata, engine='openpyxl')
        except:
            try:
                masterdata_df = pd.read_excel(archivo_masterdata)
            except Exception as e:
                st.error(f"Error al leer MASTERDATA: {str(e)}")
                return None, None, None
        
        # 5. Limpiar nombres de columnas del MASTERDATA
        masterdata_df.columns = masterdata_df.columns.str.strip()
        
        return df_conceptos, df_netos, masterdata_df
        
    except Exception as e:
        st.error(f"Error durante el procesamiento: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return None, None, None

def crear_excel_descarga(df_conceptos, df_netos, masterdata_df):
    """
    Crea el Excel final replicando exactamente los JOINs de Power Query
    """
    output = io.BytesIO()
    
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            
            # ==========================================
            # HOJA 1: "Netos" - Replicar JOIN del Power Query
            # ==========================================
            
            if df_netos is not None and masterdata_df is not None:
                # JOIN: NETOS + MASTERDATA por SAP / "Nº pers."
                netos_con_master = pd.merge(
                    df_netos,
                    masterdata_df,
                    left_on='SAP',
                    right_on='Nº pers.',
                    how='left'
                )
                
                # Seleccionar y renombrar columnas como en Power Query
                columnas_netos = {
                    'NETO': 'NETO',
                    'Valor': 'Valor', 
                    'SAP': 'SAP',
                    'Número ID': 'CÉDULA',
                    'Número de personal': 'NOMBRE',
                    'División de personal': 'REGIONAL',
                    'Ce.coste': 'CE_COSTE',
                    '     Importe': 'SALARIO',
                    'Fecha': 'F. ING',
                    'Función': 'CARGO',
                    'Área de personal': 'NIVEL'
                }
                
                # Seleccionar solo columnas que existen
                cols_disponibles = {k: v for k, v in columnas_netos.items() if k in netos_con_master.columns}
                
                if cols_disponibles:
                    netos_final = netos_con_master[list(cols_disponibles.keys())].rename(columns=cols_disponibles)
                    
                    # Reordenar columnas exactamente como en Power Query
                    orden_columnas = ['NETO', 'Valor', 'SAP', 'CÉDULA', 'NOMBRE', 'REGIONAL', 'CE_COSTE', 'SALARIO', 'F. ING', 'CARGO', 'NIVEL']
                    columnas_finales = [col for col in orden_columnas if col in netos_final.columns]
                    
                    netos_final = netos_final[columnas_finales]
                    netos_final.to_excel(writer, sheet_name='Netos', index=False)
            
            # ==========================================
            # HOJA 2: "Preno_Convertida" - Replicar JOIN del Power Query  
            # ==========================================
            
            if df_conceptos is not None and masterdata_df is not None:
                # JOIN: CONCEPTOS + MASTERDATA por SAP / "Nº pers."
                conceptos_con_master = pd.merge(
                    df_conceptos,
                    masterdata_df,
                    left_on='SAP',
                    right_on='Nº pers.',
                    how='left'
                )
                
                # Seleccionar y renombrar columnas como en Power Query
                columnas_convertida = {
                    'CÓDIGO': 'CÓDIGO',
                    'CONCEPTO': 'CONCEPTO',
                    'CANTIDAD': 'CANTIDAD',
                    'VALOR': 'VALOR',
                    'SAP': 'SAP',
                    'Número ID': 'CÉDULA',
                    'Número de personal': 'NOMBRE',
                    '     Importe': 'SALARIO',
                    'Fecha': 'F. INGRESO',
                    'Función': 'CARGO',
                    'Área de personal': 'NIVEL'
                }
                
                # Seleccionar solo columnas que existen
                cols_disponibles = {k: v for k, v in columnas_convertida.items() if k in conceptos_con_master.columns}
                
                if cols_disponibles:
                    convertida_final = conceptos_con_master[list(cols_disponibles.keys())].rename(columns=cols_disponibles)
                    
                    # Reordenar columnas exactamente como en Power Query
                    orden_columnas = ['CÓDIGO', 'CONCEPTO', 'CANTIDAD', 'VALOR', 'SAP', 'CÉDULA', 'NOMBRE', 'SALARIO', 'F. INGRESO', 'CARGO', 'NIVEL']
                    columnas_finales = [col for col in orden_columnas if col in convertida_final.columns]
                    
                    convertida_final = convertida_final[columnas_finales]
                    convertida_final.to_excel(writer, sheet_name='Preno_Convertida', index=False)
        
        output.seek(0)
        return output
        
    except Exception as e:
        st.error(f"Error al crear archivo Excel: {str(e)}")
        import traceback
        st.error(f"Traceback completo: {traceback.format_exc()}")
        return None

def main():
    st.title("📊 Procesador de Liquidación y MASTERDATA")
    st.markdown("---")
    
    st.markdown("""
    ### 🎯 Replica exactamente la lógica de Power Query
    
    **Proceso para Preno_Convertida:**
    1. Extrae SAP de líneas "Núm. Personal" 
    2. Filtra conceptos (Y*, Z*, 9*, 2*, /5*)
    3. Parsea: Código(0-11), Concepto(11-46), Cantidad(50-70), Valor(69-89)
    4. JOIN con MASTERDATA por SAP = "Nº pers."
    
    **Proceso para Netos:**
    1. Filtra solo líneas con "Total General"
    2. Parsea: Concepto(0-32), Valor(últimos 20)  
    3. JOIN con MASTERDATA por SAP = "Nº pers."
    """)
    
    st.sidebar.header("📁 Cargar Archivos")
    
    archivo_liquidacion = st.sidebar.file_uploader(
        "📄 Archivo de Liquidación (.txt)",
        type=['txt'],
        help="Archivo de liquidación con encoding latin-1"
    )
    
    archivo_masterdata = st.sidebar.file_uploader(
        "📊 Archivo MASTERDATA (.xlsx)",
        type=['xlsx'],
        help="Archivo MASTERDATA con columna 'Nº pers.'"
    )
    
    if st.sidebar.button("🚀 Procesar Archivos", type="primary"):
        if archivo_liquidacion is not None and archivo_masterdata is not None:
            with st.spinner('⏳ Procesando con lógica de Power Query...'):
                df_conceptos, df_netos, masterdata_df = procesar_archivos(
                    archivo_liquidacion, archivo_masterdata
                )
                
                if df_conceptos is not None or df_netos is not None:
                    st.success("✅ ¡Procesamiento completado!")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("📊 Conceptos extraídos", len(df_conceptos) if df_conceptos is not None else 0)
                    
                    with col2:
                        st.metric("💰 Netos extraídos", len(df_netos) if df_netos is not None else 0)
                    
                    with col3:
                        st.metric("👥 Registros MASTERDATA", len(masterdata_df))
                    
                    tab1, tab2 = st.tabs(["📊 Vista Previa", "📁 Descargar"])
                    
                    with tab1:
                        st.subheader("🔍 Vista previa")
                        
                        if df_conceptos is not None:
                            st.markdown("**Conceptos procesados:**")
                            st.dataframe(df_conceptos.head(20), use_container_width=True)
                        
                        if df_netos is not None:
                            st.markdown("**Netos procesados:**") 
                            st.dataframe(df_netos.head(10), use_container_width=True)
                    
                    with tab2:
                        st.subheader("📥 Descargar archivo procesado")
                        
                        excel_file = crear_excel_descarga(df_conceptos, df_netos, masterdata_df)
                        
                        if excel_file:
                            st.download_button(
                                label="📁 Descargar Excel (Power Query Logic)",
                                data=excel_file.getvalue(),
                                file_name=f"Preno_convertida_PowerQuery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                type="primary"
                            )
                            
                            st.success("✅ Archivo generado con lógica exacta de Power Query")
                        else:
                            st.error("❌ Error al generar archivo")
                            
        else:
            st.warning("⚠️ Por favor carga ambos archivos")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### 🔧 LÓGICA POWER QUERY REPLICADA:
    - Encoding: latin-1 (CP1252)
    - SAP desde "Núm. Personal" + Fill Down
    - Filtros exactos de conceptos
    - Parsing por posiciones fijas
    - JOINs por SAP = "Nº pers."
    """)

if __name__ == "__main__":
    main()

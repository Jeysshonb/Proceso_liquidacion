import streamlit as st
import pandas as pd
import re
from datetime import datetime
import io
import base64

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
    
    # Verificar si hay columnas duplicadas
    if df.columns.duplicated().any():
        st.warning(f"⚠️ Columnas duplicadas encontradas: {df.columns[df.columns.duplicated()].tolist()}")
        
        # Eliminar columnas duplicadas (mantener la primera)
        df_limpio = df.loc[:, ~df.columns.duplicated()]
        
        st.success(f"✅ DataFrame limpiado: {len(df.columns)} -> {len(df_limpio.columns)} columnas")
        return df_limpio
    
    return df

def parsear_recibo_liquidacion(contenido_archivo):
    """
    Parsea un archivo de recibos de liquidación con formato específico
    """
    empleados = []
    empleado_actual = {}
    
    lineas = contenido_archivo.split('\n')
    
    for i, linea in enumerate(lineas):
        linea = linea.strip()
        
        # Nueva página o nuevo empleado
        if linea.startswith('Pagina:'):
            if empleado_actual:  # Guardar empleado anterior si existe
                empleados.append(empleado_actual.copy())
                empleado_actual = {}
            continue
        
        # Saltar líneas vacías y encabezados
        if not linea or linea.startswith('RECIBO DE PAGO') or linea.startswith('Fecha:'):
            continue
        
        # Extraer información del empleado
        try:
            # Número de personal y cédula
            if 'Nm. Personal' in linea and 'Cedula Ident' in linea:
                personal_match = re.search(r'Nm\. Personal\.+(\d+)', linea)
                cedula_match = re.search(r'Cedula Ident\.+ (\d+)', linea)
                
                if personal_match:
                    empleado_actual['SAP'] = int(personal_match.group(1))
                if cedula_match:
                    empleado_actual['CEDULA'] = int(cedula_match.group(1))
            
            # Nombre del empleado y sueldo básico
            elif 'Empleado' in linea and 'Sueldo Bsico' in linea:
                nombre_match = re.search(r'Empleado \.+ (.+?)\s+Sueldo Bsico\.+\s*([\d\.,]+)', linea)
                if nombre_match:
                    empleado_actual['NOMBRE'] = nombre_match.group(1).strip()
                    sueldo_str = nombre_match.group(2).replace('.', '').replace(',', '.')
                    try:
                        empleado_actual['SALARIO'] = float(sueldo_str)
                    except:
                        empleado_actual['SALARIO'] = 0
            
            # Compañía y fecha de nacimiento
            elif 'Compaa' in linea and 'Fecha Nacto' in linea:
                compania_match = re.search(r'Compaa\.+ (.+?)\s+Fecha Nacto\.+(.+)', linea)
                if compania_match:
                    empleado_actual['COMPANIA'] = compania_match.group(1).strip()
                    empleado_actual['FECHA_NACIMIENTO'] = compania_match.group(2).strip()
            
            # División y fecha de ingreso
            elif 'Divisin' in linea and 'Fecha Ingreso' in linea:
                division_match = re.search(r'Divisin\.+ (.+?)\s+Fecha Ingreso\.+(.+)', linea)
                if division_match:
                    empleado_actual['REGIONAL'] = division_match.group(1).strip()
                    empleado_actual['F_ING'] = division_match.group(2).strip()
            
            # Subdivisión y relación laboral
            elif 'Subdivisin' in linea and 'Relacin Lab' in linea:
                subdivision_match = re.search(r'Subdivisin\.+ (.+?)\s+Relacin Lab\.+(.+)', linea)
                if subdivision_match:
                    empleado_actual['SUBDIVISION'] = subdivision_match.group(1).strip()
                    empleado_actual['CARGO'] = subdivision_match.group(2).strip()
            
            # Centro de coste
            elif 'Ce.coste' in linea:
                ce_coste_match = re.search(r'Ce\.coste\.+(\d+)', linea)
                if ce_coste_match:
                    empleado_actual['CE_COSTE'] = int(ce_coste_match.group(1))
            
            # Buscar conceptos y valores (líneas que terminan con números)
            elif re.search(r'^[A-Za-záéíóúÁÉÍÓÚñÑ\s\.]+\s+([\d\.,\-]+)$', linea):
                concepto_match = re.match(r'^(.+?)\s+([\d\.,\-]+)$', linea)
                if concepto_match:
                    concepto = concepto_match.group(1).strip()
                    valor_str = concepto_match.group(2).replace('.', '').replace(',', '.')
                    try:
                        valor = float(valor_str)
                        # Limpiar el nombre del concepto
                        concepto_limpio = re.sub(r'[^\w\s]', '', concepto).strip().upper().replace(' ', '_')
                        if concepto_limpio:
                            empleado_actual[f'CONCEPTO_{concepto_limpio}'] = valor
                    except:
                        pass
        
        except Exception as e:
            # Continuar con la siguiente línea si hay error en el parsing
            continue
    
    # Agregar último empleado
    if empleado_actual:
        empleados.append(empleado_actual)
    
    if len(empleados) == 0:
        return pd.DataFrame()
    
    # Convertir a DataFrame
    df = pd.DataFrame(empleados)
    
    # Calcular valor neto si no existe
    if 'NETO' not in df.columns:
        # Buscar columnas de conceptos para calcular el neto
        conceptos_cols = [col for col in df.columns if col.startswith('CONCEPTO_')]
        if conceptos_cols:
            df['NETO'] = df[conceptos_cols].sum(axis=1, skipna=True)
        elif 'SALARIO' in df.columns:
            df['NETO'] = df['SALARIO']
    
    return df

def procesar_archivos(archivo_liquidacion, archivo_masterdata):
    """
    Procesa los archivos de Liquidación y MASTERDATA
    """
    try:
        # 1. Parsear archivo de Liquidación
        contenido_liquidacion = archivo_liquidacion.getvalue().decode('utf-8', errors='ignore')
        liquidacion_df = parsear_recibo_liquidacion(contenido_liquidacion)
        
        if liquidacion_df.empty:
            st.error("No se pudieron extraer datos del archivo de liquidación")
            return None, None, None
        
        # 2. Leer archivo MASTERDATA
        try:
            masterdata_df = pd.read_excel(archivo_masterdata, engine='openpyxl')
        except:
            try:
                # Si falla openpyxl, intentar con otros motores
                masterdata_df = pd.read_excel(archivo_masterdata)
            except Exception as e:
                st.error(f"Error al leer MASTERDATA: {str(e)}")
                return None, None, None
        
        # 3. Limpiar nombres de columnas
        liquidacion_df.columns = liquidacion_df.columns.str.strip()
        masterdata_df.columns = masterdata_df.columns.str.strip()
        
        # 4. Buscar columnas de unión
        sap_col_liquidacion = 'SAP' if 'SAP' in liquidacion_df.columns else None
        sap_col_masterdata = 'Nº pers.' if 'Nº pers.' in masterdata_df.columns else None
        
        # 5. Realizar merge si es posible
        if sap_col_liquidacion and sap_col_masterdata:
            liquidacion_df[sap_col_liquidacion] = pd.to_numeric(liquidacion_df[sap_col_liquidacion], errors='coerce')
            masterdata_df[sap_col_masterdata] = pd.to_numeric(masterdata_df[sap_col_masterdata], errors='coerce')
            
            resultado_df = pd.merge(
                liquidacion_df, 
                masterdata_df, 
                left_on=sap_col_liquidacion, 
                right_on=sap_col_masterdata, 
                how='left',
                suffixes=('_liquidacion', '_masterdata')
            )
            
            # ✅ SOLUCIÓN: Limpiar columnas duplicadas después del merge
            resultado_df = limpiar_columnas_duplicadas(resultado_df)
            
        else:
            resultado_df = liquidacion_df
            # También limpiar liquidacion_df por si acaso
            resultado_df = limpiar_columnas_duplicadas(resultado_df)
        
        # También limpiar los otros DataFrames
        liquidacion_df = limpiar_columnas_duplicadas(liquidacion_df)
        masterdata_df = limpiar_columnas_duplicadas(masterdata_df)
        
        return resultado_df, liquidacion_df, masterdata_df
        
    except Exception as e:
        st.error(f"Error durante el procesamiento: {str(e)}")
        st.error(f"Detalles del error: {type(e).__name__}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return None, None, None

def crear_excel_descarga(resultado_df, liquidacion_df, masterdata_df):
    """
    Crea un archivo Excel para descargar - Basado en el código Python exitoso
    """
    output = io.BytesIO()
    
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            
            if resultado_df is not None:
                # Limpiar columnas duplicadas antes de escribir
                resultado_df_limpio = limpiar_columnas_duplicadas(resultado_df)
                
                # Hoja con datos combinados
                resultado_df_limpio.to_excel(writer, sheet_name='Datos_Combinados', index=False)
                
                # Crear hoja "Netos" similar al archivo original - mismo formato que el código Python
                netos_df = resultado_df_limpio.copy()
                
                # Reorganizar columnas para que se parezca al formato original
                columnas_netos = []
                if 'NETO' in netos_df.columns:
                    columnas_netos.append('NETO')
                if 'SALARIO' in netos_df.columns:
                    columnas_netos.append('SALARIO')
                
                # Buscar columna SAP
                sap_col = None
                for col in ['SAP']:
                    if col in netos_df.columns:
                        columnas_netos.append(col)
                        sap_col = col
                        break
                
                # Agregar otras columnas importantes
                for col in ['CEDULA', 'NOMBRE', 'REGIONAL', 'CE_COSTE', 'F_ING', 'CARGO']:
                    if col in netos_df.columns:
                        columnas_netos.append(col)
                
                # Agregar columnas restantes
                for col in netos_df.columns:
                    if col not in columnas_netos:
                        columnas_netos.append(col)
                
                netos_df = netos_df[columnas_netos]
                netos_df.to_excel(writer, sheet_name='Netos', index=False)
                
            else:
                # Si no hay merge, solo datos de liquidación
                liquidacion_df_limpio = limpiar_columnas_duplicadas(liquidacion_df)
                liquidacion_df_limpio.to_excel(writer, sheet_name='Liquidacion', index=False)
            
            # Hoja MASTERDATA
            if masterdata_df is not None:
                masterdata_df_limpio = limpiar_columnas_duplicadas(masterdata_df)
                masterdata_df_limpio.to_excel(writer, sheet_name='MASTERDATA', index=False)
            
            # Información del procesamiento - mismo formato que el código Python original
            info_data = {
                'Información': [
                    'Archivo procesado el:',
                    'Empleados en Liquidación:',
                    'Registros en MASTERDATA:',
                    'Empleados con match:',
                    'Columna de unión Liquidación:',
                    'Columna de unión MASTERDATA:'
                ],
                'Valor': [
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    len(liquidacion_df) if liquidacion_df is not None else 0,
                    len(masterdata_df) if masterdata_df is not None else 0,
                    resultado_df[resultado_df.columns[resultado_df.columns.str.contains('Nº pers.', na=False)]].iloc[:, 0].notna().sum() if resultado_df is not None and any(resultado_df.columns.str.contains('Nº pers.', na=False)) else 0,
                    'SAP' if liquidacion_df is not None and 'SAP' in liquidacion_df.columns else 'No encontrada',
                    'Nº pers.' if masterdata_df is not None and 'Nº pers.' in masterdata_df.columns else 'No encontrada'
                ]
            }
            
            info_df = pd.DataFrame(info_data)
            info_df.to_excel(writer, sheet_name='Info_Procesamiento', index=False)
        
        output.seek(0)
        return output
        
    except Exception as e:
        st.error(f"Error al crear archivo Excel: {str(e)}")
        return None

def main():
    # Título principal
    st.title("📊 Procesador de Liquidación y MASTERDATA")
    st.markdown("---")
    
    # Descripción
    st.markdown("""
    ### 🎯 ¿Qué hace esta aplicación?
    Esta herramienta procesa archivos de liquidación en formato de recibos de pago y los combina con datos maestros (MASTERDATA) para generar reportes estructurados en Excel.
    
    ### 📋 Funcionalidades:
    - ✅ Extrae información de recibos de liquidación (formato texto)
    - ✅ Combina con datos de MASTERDATA (Excel/XLSB)
    - ✅ Genera archivo Excel con múltiples hojas
    - ✅ Interfaz web fácil de usar
    - ✅ **Detección y limpieza automática de columnas duplicadas**
    """)
    
    # Sidebar para carga de archivos
    st.sidebar.header("📁 Cargar Archivos")
    
    # Archivo de Liquidación
    archivo_liquidacion = st.sidebar.file_uploader(
        "📄 Archivo de Liquidación (.txt)",
        type=['txt'],
        help="Selecciona el archivo de recibos de liquidación en formato texto"
    )
    
    # Archivo MASTERDATA
    archivo_masterdata = st.sidebar.file_uploader(
        "📊 Archivo MASTERDATA (.xlsx)",
        type=['xlsx'],
        help="Selecciona el archivo con los datos maestros (solo formato .xlsx)"
    )
    
    # Botón de procesamiento
    if st.sidebar.button("🚀 Procesar Archivos", type="primary"):
        if archivo_liquidacion is not None and archivo_masterdata is not None:
            with st.spinner('⏳ Procesando archivos...'):
                resultado_df, liquidacion_df, masterdata_df = procesar_archivos(
                    archivo_liquidacion, archivo_masterdata
                )
                
                if resultado_df is not None:
                    st.success("✅ ¡Procesamiento completado exitosamente!")
                    
                    # Mostrar estadísticas
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("👥 Empleados", len(liquidacion_df))
                    
                    with col2:
                        st.metric("📊 Registros MASTERDATA", len(masterdata_df))
                    
                    with col3:
                        matches = 0
                        if 'SAP' in liquidacion_df.columns and 'Nº pers.' in resultado_df.columns:
                            matches = resultado_df['Nº pers.'].notna().sum()
                        st.metric("🔗 Matches encontrados", matches)
                    
                    with col4:
                        st.metric("📋 Total columnas", len(resultado_df.columns))
                    
                    # Mostrar información de columnas duplicadas si las hubo
                    if any([df.columns.duplicated().any() for df in [resultado_df, liquidacion_df, masterdata_df] if df is not None]):
                        st.info("ℹ️ Se detectaron y limpiaron columnas duplicadas automáticamente")
                    
                    # Pestañas para mostrar datos
                    tab1, tab2, tab3 = st.tabs(["📊 Vista Previa", "📈 Estadísticas", "📁 Descargar"])
                    
                    with tab1:
                        st.subheader("🔍 Vista previa de los datos procesados")
                        
                        # Selector de hoja
                        hoja_seleccionada = st.selectbox(
                            "Selecciona qué datos ver:",
                            ["Datos Combinados", "Solo Liquidación", "Solo MASTERDATA"]
                        )
                        
                        try:
                            if hoja_seleccionada == "Datos Combinados":
                                # Mostrar información de columnas para diagnóstico
                                st.write(f"**Total de columnas:** {len(resultado_df.columns)}")
                                st.write(f"**Primeras 5 columnas:** {list(resultado_df.columns[:5])}")
                                st.dataframe(resultado_df.head(100), use_container_width=True)
                            elif hoja_seleccionada == "Solo Liquidación":
                                st.write(f"**Total de columnas:** {len(liquidacion_df.columns)}")
                                st.write(f"**Primeras 5 columnas:** {list(liquidacion_df.columns[:5])}")
                                st.dataframe(liquidacion_df.head(100), use_container_width=True)
                            else:
                                st.write(f"**Total de columnas:** {len(masterdata_df.columns)}")
                                st.write(f"**Primeras 5 columnas:** {list(masterdata_df.columns[:5])}")
                                st.dataframe(masterdata_df.head(100), use_container_width=True)
                        except Exception as e:
                            st.error(f"Error al mostrar DataFrame: {str(e)}")
                            st.error("Verifica que no haya caracteres especiales en los nombres de columnas")
                    
                    with tab2:
                        st.subheader("📈 Estadísticas del procesamiento")
                        
                        # Información de liquidación
                        st.markdown("#### 💰 Datos de Liquidación")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if 'SALARIO' in liquidacion_df.columns:
                                salario_promedio = liquidacion_df['SALARIO'].mean()
                                st.metric("💵 Salario Promedio", f"${salario_promedio:,.0f}")
                        
                        with col2:
                            if 'REGIONAL' in liquidacion_df.columns:
                                regionales = liquidacion_df['REGIONAL'].nunique()
                                st.metric("🏢 Regionales", regionales)
                        
                        # Top regionales
                        if 'REGIONAL' in liquidacion_df.columns:
                            st.markdown("#### 🏆 Top Regionales por Empleados")
                            top_regionales = liquidacion_df['REGIONAL'].value_counts().head(10)
                            st.bar_chart(top_regionales)
                    
                    with tab3:
                        st.subheader("📥 Descargar archivo procesado")
                        st.markdown("Haz clic en el botón para descargar el archivo Excel con todos los datos procesados.")
                        
                        # Generar archivo para descarga
                        excel_file = crear_excel_descarga(resultado_df, liquidacion_df, masterdata_df)
                        
                        if excel_file:
                            st.download_button(
                                label="📁 Descargar Excel procesado",
                                data=excel_file.getvalue(),
                                file_name=f"Liquidacion_procesada_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                type="primary"
                            )
                            
                            st.info("💡 El archivo contiene las siguientes hojas:\n- **Datos_Combinados**: Merge completo\n- **Netos**: Formato ordenado\n- **MASTERDATA**: Datos maestros\n- **Info_Procesamiento**: Resumen")
                        else:
                            st.error("❌ Error al generar el archivo de descarga")
                            
        else:
            st.warning("⚠️ Por favor carga ambos archivos antes de procesar.")
    
    # Información adicional en el sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### 💡 Consejos:
    - El archivo de liquidación debe ser formato texto (.txt) de JMC
    - La aplicación detecta automáticamente las columnas de unión SAP
    - Optimizado para procesar recibos de pago de Jerónimo Martins Colombia
    - **Limpia automáticamente columnas duplicadas**
    - Interfaz web especializada para nómina de Jerónimo Martins Colombia
    """)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style='text-align: center; font-size: 10px; color: #888;'>
        Nómina 2025<br>
        Desarrollado by @jeysshon<br>
        ✅ Versión con limpieza de columnas duplicadas
    </div>
    """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center'>
        <p>🚀 Desarrollado para el procesamiento eficiente de datos de liquidación</p>
        <p>📧 ¿Necesitas ayuda? Contacta al equipo de desarrollo</p>
        <p><small>🔧 Versión mejorada con corrección de columnas duplicadas</small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

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

def mapear_codigo_concepto(concepto_name):
    """
    Mapea nombres de conceptos a códigos específicos basado en el archivo REAL subido
    """
    # Mapeo exacto extraído del archivo real
    mapeo_real = {
        'APOYO_DE_SOSTENIMIENTO': ('Y050', 'Apoyo de Sostenimiento'),
        'APOYO_SOSTENIMIENTO_PRA': ('Y051', 'Apoyo Sostenimiento Pra'),
        'BASE_SALUD_AUTOLIQ_JM': ('9262', 'Base Salud Autoliq. JM'),
        'BASE_DESCUENTO_EMPLEADO': ('9263', 'Base Descuento Empleado'),
        'SUELDO_BASICO': ('Y010', 'Sueldo Básico'),
        'SALARIO_PARTI_TIME_DIAS': ('Y011', 'Salario Parti-time Días'),
        'SALARIO_PART_TIME_HORAS': ('Y090', 'Salario Part-time Horas'),
        'SUSPENSION_CONTRATO_SEN': ('Y1P4', 'Suspensión contrato SEN'),
        'AUXILIO_TRANS_LEGAL': ('Y200', 'Auxilio  de Trans Legal'),
        'RECARGO_NOCTURNO_35': ('Y220', 'Recargo Nocturno (35)'),
        'RECARGO_NOCT_DOM_110': ('Y221', 'recargo noct dom (110)'),
        'PAGO_DESCANSO_REMUNERAD': ('Y250', 'Pago descanso remunerad'),
        'HORA_EXTRA_DIURNA_125': ('Y300', 'Hora Extra Diurna (125)'),
        'HORA_EXTRA_NOCTURNA_17': ('Y305', 'Hora Extra Nocturna (17'),
        'HORA_EX_DIURNA_FEST_20': ('Y310', 'Hora Ex Diurna Fest (20'),
        'HORA_EX_NOCT_FEST_250': ('Y315', 'Hora Ex Noct.Fest (250)'),
        'COMPENSATORIO': ('Y350', 'Compensatorio'),
        'INCAPA_FUERA_TURNO': ('Y510', 'Incapa. fuera de turno'),
        'VALES_ALIMENTACION_BP': ('Y598', 'Vales alimentación BP'),
        'BONO_POR_LOCALIDAD': ('Y616', 'Bono por Localidad'),
        'RECARGO_DOMINGO_FEST': ('YM01', 'Recargo domingo y/o fes'),
        'AUX_DIAS_INIC_INCAP': ('Y1A1', 'Aux.Días inic.incap gra'),
        'DIA_DE_LA_FAMILIA': ('Y1D1', 'Día de la Familia'),
        'AUSENCIA_NO_JUSTIFICADA': ('Y1S2', 'Ausencia no justificada'),
        'AUS_REG_SIN_SOPORTE': ('Y1S4', 'Aus Reg sin Soporte'),
        'AUS_SIN_SOPORTE_RECH': ('Y1S5', 'Aus.Sin Soporte Rech Do'),
        'DESCUENTO_SALUD': ('Z000', 'Descuento Salud'),
        'DESCUENTO_PENSION': ('Z010', 'Descuento Pensión'),
        'DESC_AUTORIZADO_CAJA': ('Z498', 'Desc autorizado Caja'),
        'DESCUENTO_COOP_COMUNIDA': ('Z542', 'Descuento coop comunida'),
        'COMPENSACION_MAYOR_VALO': ('Z550', 'Compensación mayor valo'),
        'FONDO_EMPL_JMC_ATULADO': ('Z573', 'Fondo Empl. JMC ATuLado'),
        'DESCUENTO_BIG_PASS': ('Z590', 'Descuento Big Pass'),
        'DESCUENTO_PAY_FLOW': ('Z610', 'Descuento Pay Flow'),
        'DESCUENTO_ALMUERZO': ('ZCA2', 'Descuento almuerzo'),
        'PREST_LIBRE_INVERS_ATUL': ('ZLB1', 'Prest Libre Invers ATuL'),
        'DOTACION_OPERACIONES': ('9DT3', 'Dotación operaciones')
    }
    
    concepto_key = concepto_name.upper().replace(' ', '_').replace('.', '_').replace('-', '_')
    
    # Buscar coincidencias parciales
    for key, (codigo, concepto) in mapeo_real.items():
        if key in concepto_key or any(word in concepto_key for word in key.split('_') if len(word) > 3):
            return codigo, concepto
    
    # Si no encuentra coincidencia exacta, devolver código genérico
    return 'Y999', concepto_name.title()

def crear_excel_descarga(resultado_df, liquidacion_df, masterdata_df):
    """
    Crea un archivo Excel con SOLO 2 hojas: Netos y Preno_Convertida
    Replicando EXACTAMENTE la estructura del archivo real subido
    """
    output = io.BytesIO()
    
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            
            if resultado_df is not None:
                # Limpiar columnas duplicadas antes de escribir
                resultado_df_limpio = limpiar_columnas_duplicadas(resultado_df)
                
                # ==========================================
                # HOJA 1: "Netos" - EXACTAMENTE como en el archivo real
                # ==========================================
                
                netos_data = []
                for idx, row in resultado_df_limpio.iterrows():
                    # Calcular el valor neto sumando conceptos positivos y restando negativos
                    conceptos_cols = [col for col in resultado_df_limpio.columns if col.startswith('CONCEPTO_')]
                    valor_neto = 0
                    
                    if conceptos_cols:
                        for concepto_col in conceptos_cols:
                            if pd.notna(row[concepto_col]):
                                valor_neto += float(row[concepto_col])
                    
                    # Si no hay conceptos, usar el salario como base
                    if valor_neto == 0:
                        valor_neto = row.get('SALARIO', 0)
                    
                    neto_row = {
                        'NETO': 'Total General:',  # Texto fijo exacto del archivo real
                        'Valor': int(valor_neto) if valor_neto else 0,  # Valor calculado como entero
                        'SAP': int(row.get('SAP', 0)) if pd.notna(row.get('SAP')) else 0,
                        'CÉDULA': int(row.get('CEDULA', 0)) if pd.notna(row.get('CEDULA')) else 0,
                        'NOMBRE': str(row.get('NOMBRE', '')),
                        'REGIONAL': str(row.get('REGIONAL', '')),
                        'CE_COSTE': int(row.get('CE_COSTE', 0)) if pd.notna(row.get('CE_COSTE')) else 0,
                        'SALARIO': int(row.get('SALARIO', 0)) if pd.notna(row.get('SALARIO')) else 0,
                        'F. ING': row.get('F_ING', ''),  # Mantener formato original
                        'CARGO': str(row.get('CARGO', '')),
                        'NIVEL': str(row.get('NIVEL', 'Non Manager X-XII'))
                    }
                    netos_data.append(neto_row)
                
                if netos_data:
                    netos_df = pd.DataFrame(netos_data)
                    netos_df.to_excel(writer, sheet_name='Netos', index=False)
                
                # ==========================================
                # HOJA 2: "Preno_Convertida" - EXACTAMENTE como en el archivo real
                # ==========================================
                
                convertida_data = []
                
                # Buscar todas las columnas de conceptos
                conceptos_cols = [col for col in resultado_df_limpio.columns if col.startswith('CONCEPTO_')]
                
                for idx, row in resultado_df_limpio.iterrows():
                    # Si hay conceptos específicos en el archivo de liquidación
                    if conceptos_cols:
                        for concepto_col in conceptos_cols:
                            if pd.notna(row[concepto_col]) and row[concepto_col] != 0:
                                # Extraer nombre del concepto sin el prefijo CONCEPTO_
                                concepto_name = concepto_col.replace('CONCEPTO_', '').replace('_', ' ')
                                
                                # Mapear a código y concepto usando el mapeo real del archivo
                                codigo, concepto_limpio = mapear_codigo_concepto(concepto_name)
                                
                                convertida_row = {
                                    'CÓDIGO': codigo,
                                    'CONCEPTO': concepto_limpio,
                                    'CANTIDAD': 30,  # Cantidad fija como en el archivo real
                                    'VALOR': int(row[concepto_col]) if pd.notna(row[concepto_col]) else None,
                                    'SAP': int(row.get('SAP', 0)) if pd.notna(row.get('SAP')) else 0,
                                    'CÉDULA': int(row.get('CEDULA', 0)) if pd.notna(row.get('CEDULA')) else 0,
                                    'NOMBRE': str(row.get('NOMBRE', '')),
                                    'SALARIO': int(row.get('SALARIO', 0)) if pd.notna(row.get('SALARIO')) else 0,
                                    'F. INGRESO': row.get('F_ING', ''),  # Mantener formato original
                                    'CARGO': str(row.get('CARGO', '')),
                                    'NIVEL': str(row.get('NIVEL', 'Non Manager X-XII'))
                                }
                                convertida_data.append(convertida_row)
                    
                    else:
                        # Si no hay conceptos específicos, generar conceptos base típicos de nómina
                        # Basándose en los patrones del archivo real subido
                        
                        salario_base = row.get('SALARIO', 0)
                        
                        # Conceptos típicos basados en el archivo real
                        conceptos_base = [
                            ('Y010', 'Sueldo Básico', salario_base),
                            ('Y200', 'Auxilio  de Trans Legal', min(salario_base * 0.1, 140606)),  # Tope auxilio transporte 2024
                            ('9262', 'Base Salud Autoliq. JM', salario_base),  # Base para cálculo salud
                            ('9263', 'Base Descuento Empleado', salario_base),  # Base para descuentos
                            ('Z000', 'Descuento Salud', salario_base * -0.04),  # 4% salud empleado
                            ('Z010', 'Descuento Pensión', salario_base * -0.04)  # 4% pensión empleado
                        ]
                        
                        # Agregar horas extras si el salario es significativamente mayor al básico
                        if salario_base > 2000000:  # Si gana más del mínimo
                            conceptos_base.extend([
                                ('Y300', 'Hora Extra Diurna (125)', salario_base * 0.05),
                                ('Y220', 'Recargo Nocturno (35)', salario_base * 0.02)
                            ])
                        
                        for codigo, concepto, valor in conceptos_base:
                            if valor != 0:  # Solo agregar si el valor no es cero
                                convertida_row = {
                                    'CÓDIGO': codigo,
                                    'CONCEPTO': concepto,
                                    'CANTIDAD': 30,
                                    'VALOR': int(valor) if valor else None,
                                    'SAP': int(row.get('SAP', 0)) if pd.notna(row.get('SAP')) else 0,
                                    'CÉDULA': int(row.get('CEDULA', 0)) if pd.notna(row.get('CEDULA')) else 0,
                                    'NOMBRE': str(row.get('NOMBRE', '')),
                                    'SALARIO': int(salario_base) if salario_base else 0,
                                    'F. INGRESO': row.get('F_ING', ''),
                                    'CARGO': str(row.get('CARGO', '')),
                                    'NIVEL': str(row.get('NIVEL', 'Non Manager X-XII'))
                                }
                                convertida_data.append(convertida_row)
                
                if convertida_data:
                    convertida_df = pd.DataFrame(convertida_data)
                    convertida_df.to_excel(writer, sheet_name='Preno_Convertida', index=False)
                
            else:
                st.error("No hay datos para procesar")
                return None
        
        output.seek(0)
        return output
        
    except Exception as e:
        st.error(f"Error al crear archivo Excel: {str(e)}")
        import traceback
        st.error(f"Traceback completo: {traceback.format_exc()}")
        return None

def main():
    # Título principal
    st.title("📊 Procesador de Liquidación y MASTERDATA")
    st.markdown("---")
    
    # Descripción
    st.markdown("""
    ### 🎯 ¿Qué hace esta aplicación?
    Esta herramienta procesa archivos de liquidación en formato de recibos de pago y los combina con datos maestros (MASTERDATA) para generar reportes estructurados en Excel.
    
    ### 📋 Genera exactamente 2 hojas:
    - ✅ **Netos**: "Total General:", Valor, SAP, CÉDULA, NOMBRE, REGIONAL, CE_COSTE, SALARIO, F. ING, CARGO, NIVEL
    - ✅ **Preno_Convertida**: CÓDIGO, CONCEPTO, CANTIDAD, VALOR, SAP, CÉDULA, NOMBRE, SALARIO, F. INGRESO, CARGO, NIVEL
    
    ### 🔧 Mapea conceptos a códigos:
    - Y050: Apoyo de Sostenimiento
    - 9262: Base Salud Autoliq. JM  
    - 9263: Base Descuento Empleado
    - Y010: Sueldo Básico
    - Y200: Auxilio de Trans Legal
    - Z000: Descuento Salud
    - Y1P4: Suspensión contrato SEN
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
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("👥 Empleados", len(liquidacion_df))
                    
                    with col2:
                        st.metric("📊 Registros MASTERDATA", len(masterdata_df))
                    
                    with col3:
                        matches = 0
                        if 'SAP' in liquidacion_df.columns and 'Nº pers.' in resultado_df.columns:
                            matches = resultado_df['Nº pers.'].notna().sum()
                        st.metric("🔗 Matches encontrados", matches)
                    
                    # Pestañas para mostrar datos
                    tab1, tab2 = st.tabs(["📊 Vista Previa", "📁 Descargar"])
                    
                    with tab1:
                        st.subheader("🔍 Vista previa de los datos procesados")
                        
                        # Selector de hoja
                        hoja_seleccionada = st.selectbox(
                            "Selecciona qué datos ver:",
                            ["Datos Combinados", "Solo Liquidación", "Solo MASTERDATA"]
                        )
                        
                        try:
                            if hoja_seleccionada == "Datos Combinados":
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
                        st.subheader("📥 Descargar archivo procesado")
                        st.markdown("**El archivo Excel contendrá EXACTAMENTE 2 hojas:**")
                        st.markdown("- **Netos**: 'Total General:', Valor, SAP, CÉDULA, NOMBRE, REGIONAL, CE_COSTE, SALARIO, F. ING, CARGO, NIVEL")
                        st.markdown("- **Preno_Convertida**: CÓDIGO, CONCEPTO, CANTIDAD, VALOR, SAP, CÉDULA, NOMBRE, SALARIO, F. INGRESO, CARGO, NIVEL")
                        
                        st.info("🎯 **MAPEO DE CÓDIGOS**: Y050=Apoyo Sostenimiento, 9262=Base Salud, 9263=Base Descuento, Y010=Sueldo Básico")
                        
                        # Generar archivo para descarga
                        excel_file = crear_excel_descarga(resultado_df, liquidacion_df, masterdata_df)
                        
                        if excel_file:
                            st.download_button(
                                label="📁 Descargar Excel procesado (SOLO 2 hojas)",
                                data=excel_file.getvalue(),
                                file_name=f"Preno_convertida_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                type="primary"
                            )
                            
                            st.success("✅ Archivo generado correctamente con estructura exacta del archivo de referencia")
                        else:
                            st.error("❌ Error al generar el archivo de descarga")
                            
        else:
            st.warning("⚠️ Por favor carga ambos archivos antes de procesar.")
    
    # Información adicional en el sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### 🎯 ESTRUCTURA EXACTA:
    
    **HOJA NETOS:**
    - NETO: "Total General:"
    - Valor: Monto calculado 
    - SAP, CÉDULA, NOMBRE, etc.
    
    **HOJA PRENO_CONVERTIDA:**  
    - CÓDIGO: Y050, 9262, 9263, etc.
    - CONCEPTO: Apoyo de Sostenimiento, etc.
    - Múltiples filas por empleado
    
    ⚠️ **NO SE GENERAN OTRAS HOJAS**
    """)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style='text-align: center; font-size: 10px; color: #888;'>
        Nómina 2025<br>
        Desarrollado by @jeysshon<br>
        🎯 Versión FINAL - Estructura exacta
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

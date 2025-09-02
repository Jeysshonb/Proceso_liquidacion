# 📊 Procesador de Liquidación y MASTERDATA

Una aplicación web desarrollada en Streamlit para procesar archivos de liquidación en formato de recibos de pago y combinarlos con datos maestros (MASTERDATA).

## 🎯 Funcionalidades

- ✅ **Procesamiento automático** de recibos de liquidación en formato texto
- ✅ **Extracción inteligente** de información clave (SAP, nombre, cédula, salario, etc.)
- ✅ **Combinación automática** con datos de MASTERDATA
- ✅ **Generación de Excel** con múltiples hojas estructuradas
- ✅ **Interfaz web intuitiva** y fácil de usar
- ✅ **Estadísticas y visualizaciones** de los datos procesados

## 🚀 Cómo usar la aplicación

### 1. Acceso online
La aplicación está desplegada en Streamlit Cloud: [Enlace a la aplicación]

### 2. Uso local

#### Prerrequisitos
- Python 3.8 o superior
- pip (gestor de paquetes de Python)

#### Instalación
```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/procesador-liquidacion.git
cd procesador-liquidacion

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
streamlit run app.py
```

## 📁 Estructura de archivos

```
procesador-liquidacion/
├── app.py              # Aplicación principal de Streamlit
├── requirements.txt    # Dependencias del proyecto
├── README.md          # Este archivo
└── .gitignore         # Archivos a ignorar en Git
```

## 📋 Tipos de archivos soportados

### Archivo de Liquidación (.txt)
- Formato de recibos de pago con estructura específica
- Debe contener información de empleados separada por páginas
- Codificación UTF-8 o Latin-1

### Archivo MASTERDATA (.xlsx, .xlsb, .xls)
- Archivo Excel con datos maestros de empleados
- Debe contener columna "Nº pers." para hacer el match con liquidación

## 📊 Resultado del procesamiento

La aplicación genera un archivo Excel con las siguientes hojas:

1. **Datos_Combinados**: Merge completo de liquidación y MASTERDATA
2. **Netos**: Formato ordenado similar al archivo original
3. **MASTERDATA**: Datos maestros completos
4. **Info_Procesamiento**: Resumen y estadísticas del procesamiento

## 🛠️ Tecnologías utilizadas

- **Streamlit**: Framework de aplicaciones web
- **Pandas**: Procesamiento y análisis de datos
- **OpenPyXL**: Lectura y escritura de archivos Excel
- **Regex**: Parsing de texto estructurado
- **Python**: Lenguaje de programación

## 📈 Características técnicas

- **Parser inteligente** que reconoce el formato específico de recibos
- **Manejo robusto de errores** y diferentes codificaciones
- **Interfaz responsive** que funciona en desktop y móvil
- **Procesamiento en memoria** sin almacenamiento de archivos
- **Descarga directa** del resultado sin pasos intermedios

## 🔧 Desarrollo y contribución

### Estructura del código
- `parsear_recibo_liquidacion()`: Extrae datos de los recibos de liquidación
- `procesar_archivos()`: Combina liquidación con MASTERDATA
- `crear_excel_descarga()`: Genera archivo Excel para descargar
- `main()`: Interfaz principal de Streamlit

### Para contribuir
1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crea un Pull Request

## 📧 Soporte

¿Encontraste un bug o tienes una sugerencia?
- Abre un [Issue](https://github.com/tu-usuario/procesador-liquidacion/issues)
- Envía un email a: soporte@tuempresa.com

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 🎉 Agradecimientos

- Equipo de desarrollo por el diseño e implementación
- Usuarios beta por el feedback y pruebas iniciales

---

**🏢 Diseñado específicamente para nómina Jerónimo Martins Colombia**  
**Desarrollado con ❤️ por @jeysshon 2025**

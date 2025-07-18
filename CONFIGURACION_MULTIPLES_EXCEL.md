# Configuración para Múltiples Archivos Excel

## Descripción

Esta actualización permite procesar múltiples archivos Excel (de 1 a 3 máximo) en una sola ejecución de los scrapers de LinkedIn y SEMrush. Esto es útil cuando necesitas extraer datos para diferentes carreras o proyectos que están organizados en archivos Excel separados.

## Configuración

### 1. Variables de Entorno

Edita el archivo `.env` y configura las rutas de los archivos Excel:

```properties
# Múltiples rutas de Excel (separadas por comas)
EXCEL_PATHS=db/DisenoDeModas.xlsx,db/MarketingDigital.xlsx,db/PsicologiaOrganizacional.xlsx

# Ruta única (para compatibilidad hacia atrás)
EXCEL_PATH=db/DisenoDeModas.xlsx
```

### 2. Opciones de Configuración

#### Opción 1: Un solo archivo Excel
```properties
EXCEL_PATHS=db/DisenoDeModas.xlsx
```

#### Opción 2: Dos archivos Excel
```properties
EXCEL_PATHS=db/DisenoDeModas.xlsx,db/MarketingDigital.xlsx
```

#### Opción 3: Tres archivos Excel (máximo)
```properties
EXCEL_PATHS=db/DisenoDeModas.xlsx,db/MarketingDigital.xlsx,db/PsicologiaOrganizacional.xlsx
```

### 3. Fallback (Compatibilidad)

Si no se define `EXCEL_PATHS` o si hay algún error, el sistema automáticamente usará `EXCEL_PATH` como respaldo.

## Cómo Funciona

### Para SEMrush

1. **Inicia sesión una sola vez** en SEMrush
2. **Para cada archivo Excel**:
   - Extrae la carrera desde la tabla `carreraSemrush`
   - Busca información en SEMrush para esa carrera
   - Guarda los resultados en el archivo Excel correspondiente
3. **Cierra el navegador** al finalizar todos los archivos

### Para LinkedIn

1. **Inicia sesión una sola vez** en LinkedIn
2. **Para cada archivo Excel**:
   - Extrae los reportes desde la tabla `reporteLinkedin`
   - Busca cada carpeta y proyecto en LinkedIn
   - Extrae datos para las ubicaciones configuradas (Ecuador, América Latina)
   - Guarda los resultados en el archivo Excel correspondiente
3. **Cierra el navegador** al finalizar todos los archivos

## Estructura Requerida en Cada Excel

Cada archivo Excel debe tener la estructura esperada:

### Hoja "Input"
- **Para SEMrush**: Tabla `carreraSemrush` con la carrera a buscar
- **Para LinkedIn**: Tabla `reporteLinkedin` con columnas "Carpeta" y "Proyecto"

### Hojas de Resultados
- **Para SEMrush**: Hoja `Semrush` con tabla `datoSemrush`
- **Para LinkedIn**: Hoja `LinkedIn` con tabla `datoLinkedin`

## Ejemplo de Uso

Si tienes estos archivos Excel configurados:
1. `db/DisenoDeModas.xlsx` - para la carrera de Diseño de Modas
2. `db/MarketingDigital.xlsx` - para la carrera de Marketing Digital
3. `db/PsicologiaOrganizacional.xlsx` - para la carrera de Psicología Organizacional

Al ejecutar el scraper de SEMrush:
1. Se iniciará sesión una vez
2. Procesará "Diseño de Modas" y guardará en el primer archivo
3. Procesará "Marketing Digital" y guardará en el segundo archivo
4. Procesará "Psicología Organizacional" y guardará en el tercer archivo
5. Cerrará el navegador

## Ventajas

✅ **Eficiencia**: Inicia sesión solo una vez para procesar múltiples archivos
✅ **Organización**: Mantiene los datos separados por carrera/proyecto
✅ **Flexibilidad**: Funciona con 1, 2 o 3 archivos Excel
✅ **Compatibilidad**: Mantiene la funcionalidad anterior como respaldo

## Logs de Ejecución

Durante la ejecución verás logs como:

```
📂 Se procesarán 3 archivo(s) Excel:
   1. db/DisenoDeModas.xlsx
   2. db/MarketingDigital.xlsx
   3. db/PsicologiaOrganizacional.xlsx

============================================================
📊 Procesando archivo 1/3: DisenoDeModas.xlsx
============================================================
🔍 Carrera a buscar: Diseño de Modas
...
✅ Datos guardados correctamente para DisenoDeModas.xlsx

🎉 Proceso SEMrush finalizado. Se procesaron 3 archivo(s).
```

## Solución de Problemas

### Error: "No se encontraron rutas de Excel válidas"
- Verifica que las rutas en `EXCEL_PATHS` sean correctas
- Asegúrate de que los archivos existen en las rutas especificadas
- Usa rutas relativas desde la carpeta del proyecto

### Error: "No se encontró la carrera/reportes"
- Verifica que cada Excel tenga la estructura correcta
- Asegúrate de que las tablas `carreraSemrush` o `reporteLinkedin` existan
- Revisa que los datos estén en la hoja "Input"

### Advertencia: "Archivo no encontrado"
- El sistema ignorará archivos que no existan
- Solo procesará los archivos válidos encontrados

### Errores de Selenium (SEMrush)
Si ves errores como "Message: Stacktrace: GetHandleVerifier..." en SEMrush:
- **Causa**: Elementos no encontrados en la página web
- **Solución**: El código ahora maneja estos errores automáticamente
- **Resultado**: Se guardarán valores de 0 para los datos que no se pudieron extraer
- **Mejoras implementadas**:
  - Tiempos de espera aumentados
  - Limpieza completa del campo de búsqueda entre carreras
  - Manejo robusto de errores por carrera individual
  - Guardado de datos parciales cuando falla algún elemento

### Errores de Banner en LinkedIn
Si aparecen banners de error o "0 resultados" en LinkedIn:
- **Reintentos de banner**: 3 intentos automáticos con recarga de página
- **Reintentos generales**: 5 intentos totales para aplicar filtros
- **Mensajes mejorados**: Indicadores claros del progreso de intentos
- **Comportamiento**:
  - Se refresca la página automáticamente
  - Se re-aplican los filtros tras cada refresco
  - Continúa con el siguiente reporte si falla definitivamente

### Comportamiento con Errores
- ✅ **SEMrush**: Si falla extraer datos → se guarda 0
- ✅ **LinkedIn**: Si falla aplicar filtro → 5 intentos con mensajes claros
- ✅ **LinkedIn**: Si aparece banner error → 3 intentos de recarga automática
- ✅ El proceso continúa con el siguiente archivo Excel
- ✅ Mensajes informativos sobre el progreso de cada intento

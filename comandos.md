# 📈 Scraping-Tendencias

Proyecto de scraping de datos desde LinkedIn y otras plataformas como SEMrush. Automatiza la recolección de información usando **Selenium** y muestra resultados mediante una interfaz construida con **Streamlit**.

---

## 📦 Requisitos

- Python 3.10 o superior  
- Google Chrome instalado  
- Ambiente virtual (recomendado)  
- Archivo `.env` con credenciales configuradas  

---

## 🔐 Variables de entorno

Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido:

```env
LINKEDIN_USER=tu_correo@ejemplo.com
LINKEDIN_PASS=tu_contraseña_segura
SEMRUSH_USER=tu_correo@ejemplo.com
SEMRUSH_PASS=tu_contraseña_semrush

# Rutas de archivos Excel (separadas por comas)
# Puedes definir tantos archivos como necesites
EXCEL_PATHS=db/archivo1.xlsx,db/archivo2.xlsx,db/archivo3.xlsx

---Ejemplo---
EXCEL_PATHS=db/SeguridadInformaticaProteccionDeDatos.xlsx, db/Informatica.xlsx
```

---

## 🧪 Verificar configuración

Para verificar que los archivos Excel están correctamente configurados:

```bash
python -c "from scrapers.utils import obtener_rutas_excel; print('Archivos configurados:', obtener_rutas_excel())"
```

---

## 🗂️ Crear perfil de Chrome personalizado

Para mantener la sesión de LinkedIn activa entre ejecuciones del scraper, se utiliza un perfil de usuario dedicado de Chrome.

### 1. Crear la carpeta de perfil

```bash
mkdir "profile"
```

### 2. Abrir Chrome con ese perfil

```bash
start chrome --user-data-dir="C:\Users\User\Documents\TRABAJO - UDLA\Scraping-Tendencias\profile"
```

Una vez abierta la ventana de Chrome:

- Inicia sesión manualmente en LinkedIn.  
- **No cierres sesión.**  
- Cierra esa ventana cuando termines. Esta sesión será reutilizada por Selenium.

> ⚠️ **Importante**: No abras el navegador manualmente mientras el scraper está corriendo. Podría generar conflictos con el perfil.

---

## 🚀 Ejecutar el scraper

Para iniciar el proceso de scraping desde la terminal:

```bash
python scraper.py
```

Este script se encarga de:

- Iniciar sesión en LinkedIn automáticamente (o reutilizar una sesión previa)
- Buscar carpetas y proyectos guardados
- Aplicar filtros por ubicación (Ecuador, América Latina, etc.)
- Exportar los resultados en formato Excel

---

## 📊 Ejecutar la aplicación web con Streamlit

Puedes visualizar o trabajar con los datos generados usando una interfaz gráfica web. Para iniciar la app de Streamlit:

```bash
streamlit run app.py
```

Esto abrirá automáticamente una pestaña en tu navegador con la aplicación web.

---

## 🧑‍💻 Autor

Este proyecto fue desarrollado con fines educativos y de análisis de tendencias para instituciones académicas.

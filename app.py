import streamlit as st
import pandas as pd
import os
from pathlib import Path
from data_process.mercado import calc_mercado
from data_process.linkedin import calc_linkedin
from data_process.busquedaWeb import calc_busquedaWeb
from data_process.competencia import calc_competencia_presencial, calc_competencia_virtual
from scrapers.utils import obtener_rutas_excel

# Configuración de la página
st.set_page_config(
    page_title="Certificaciones - Análisis Multi-Excel", 
    page_icon="📊",
    layout="wide"
)

# Función para obtener el nombre del archivo sin extensión
def obtener_nombre_archivo(ruta):
    return Path(ruta).stem

# Función para verificar si un archivo Excel existe
def verificar_archivo_excel(ruta):
    return os.path.exists(ruta)

# Obtener todas las rutas de Excel configuradas
try:
    rutas_excel = obtener_rutas_excel()
    rutas_validas = [ruta for ruta in rutas_excel if verificar_archivo_excel(ruta)]
    
    if not rutas_validas:
        st.error("❌ No se encontraron archivos Excel válidos.")
        st.stop()
        
except Exception as e:
    st.error(f"❌ Error al cargar configuración: {e}")
    st.stop()

# Crear nombres para las pestañas
nombres_pestanas = [obtener_nombre_archivo(ruta) for ruta in rutas_validas]

# Título principal
st.title("📊 Certificaciones - Análisis Multi-Excel")
st.markdown(f"**Archivos configurados:** {len(rutas_validas)}")

# Crear las pestañas
tabs = st.tabs(nombres_pestanas)

# Lista de parámetros
parametros = ["Búsqueda Web", "LinkedIN", "Competencia", "Mercado", "Total"]

# Distribución deseada
distribucion_valores = {
    "Búsqueda Web": 0.35,
    "LinkedIN": 0.25,
    "Competencia": 0.25,
    "Mercado": 0.15,
}

# Función para calcular la distribución
def calcular_distribucion(parametro):
    return (
        sum(distribucion_valores.values())
        if parametro == "Total"
        else distribucion_valores.get(parametro, 0)
    )

# Función general para presencialidad y virtualidad cuando comparten lógica
def calcular_valor_general(parametro, ruta_excel):
    try:
        if parametro == "Búsqueda Web":
            return calc_busquedaWeb(ruta_excel)
        elif parametro == "LinkedIN":
            return calc_linkedin(ruta_excel)
        elif parametro == "Mercado":
            return calc_mercado(ruta_excel)
        return 0
    except Exception as e:
        st.error(f"Error calculando {parametro}: {e}")
        return 0

# Funciones específicas para "Competencia"
def calcular_presencial_competencia(ruta_excel):
    try:
        return calc_competencia_presencial(ruta_excel)
    except Exception as e:
        st.error(f"Error calculando competencia presencial: {e}")
        return 0

def calcular_virtual_competencia(ruta_excel):
    try:
        return calc_competencia_virtual(ruta_excel)
    except Exception as e:
        st.error(f"Error calculando competencia virtual: {e}")
        return 0

# Función para procesar un archivo Excel específico
def procesar_excel(ruta_excel, nombre_archivo):
    st.subheader(f"📋 Evaluación: {nombre_archivo}")
    st.markdown(f"**Archivo:** `{ruta_excel}`")
    
    # Diccionarios para mapear resultados
    presencialidad_resultados = []
    virtualidad_resultados = []

    # Mostrar progress bar
    progress_bar = st.progress(0)
    
    for i, parametro in enumerate(parametros):
        progress_bar.progress((i + 1) / len(parametros))
        
        if parametro == "Competencia":
            presencialidad_resultados.append(calcular_presencial_competencia(ruta_excel))
            virtualidad_resultados.append(calcular_virtual_competencia(ruta_excel))
        elif parametro == "Total":
            total_presencial = round(sum(presencialidad_resultados), 2)
            total_virtual = round(sum(virtualidad_resultados), 2)
            presencialidad_resultados.append(total_presencial)
            virtualidad_resultados.append(total_virtual)
        else:
            resultado = calcular_valor_general(parametro, ruta_excel)
            presencialidad_resultados.append(resultado)
            virtualidad_resultados.append(resultado)
    
    progress_bar.empty()

    # Construcción del DataFrame
    datos = {
        "Parámetros": parametros,
        "Distribución": [
            (
                f"{calcular_distribucion(p) * 100:.0f}%"
                if p != "Total"
                else f"{calcular_distribucion(p) * 100:.0f}%"
            )
            for p in parametros
        ],
        "Presencialidad": presencialidad_resultados,
        "Virtualidad": virtualidad_resultados,
    }

    df = pd.DataFrame(datos)

    def resaltar_filas(row):
        return (
            ["background-color: #C10230; color: white"] * len(row)
            if row["Parámetros"] == "Total"
            else ["background-color: white"] * len(row)
        )

    styled_df = (
        df.style.apply(resaltar_filas, axis=1)
        .set_table_styles([{"selector": "th", "props": [("color", "black")]}])
        .format({"Presencialidad": lambda x: f"{x:.0f}%", "Virtualidad": lambda x: f"{x:.0f}%"})
    )

    st.dataframe(styled_df, use_container_width=True, hide_index=True)

# Procesar cada archivo en su pestaña correspondiente
for i, (tab, ruta_excel, nombre_archivo) in enumerate(zip(tabs, rutas_validas, nombres_pestanas)):
    with tab:
        procesar_excel(ruta_excel, nombre_archivo)

# Mostrar rango de evaluación en todas las pestañas (información general)
st.markdown("---")
st.subheader("📊 Rango Evaluación Final")

df_rango = pd.DataFrame(
    {
        "Rango": ["0% - 60%", "61% - 70%", "71% - 100%"],
        "Evaluación": [
            "Definitivamente No Viable",
            "Para revisión adicional",
            "Viable",
        ],
    }
)

st.dataframe(df_rango, use_container_width=True, hide_index=True)

import streamlit as st
import pandas as pd
from data_process.mercado import calc_mercado
from data_process.linkedin import calc_linkedin
from data_process.busquedaWeb import calc_busquedaWeb

st.title("Certificaciones")
st.subheader("Evaluación")

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
def calcular_valor_general(parametro):
    if parametro == "Búsqueda Web":
        return calc_busquedaWeb()
    elif parametro == "LinkedIN":
        return calc_linkedin()
    elif parametro == "Mercado":
        return calc_mercado()
    return 0


# Funciones específicas para "Competencia"
def calcular_presencial_competencia():
    return 0


def calcular_virtual_competencia():
    return 0


# Diccionarios para mapear resultados
presencialidad_resultados = []
virtualidad_resultados = []

for parametro in parametros:
    if parametro == "Competencia":
        presencialidad_resultados.append(calcular_presencial_competencia())
        virtualidad_resultados.append(calcular_virtual_competencia())
    elif parametro == "Total":
        total_presencial = sum(presencialidad_resultados)
        total_virtual = sum(virtualidad_resultados)
        presencialidad_resultados.append(total_presencial)
        virtualidad_resultados.append(total_virtual)
    else:
        resultado = calcular_valor_general(parametro)
        presencialidad_resultados.append(resultado)
        virtualidad_resultados.append(resultado)

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
    .format({"Presencialidad": lambda x: x, "Virtualidad": lambda x: x})
)

st.dataframe(styled_df, use_container_width=True, hide_index=True)

# Rango de evaluación
st.subheader("Rango Evaluación Final")

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

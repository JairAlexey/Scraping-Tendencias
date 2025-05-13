import pandas as pd
from scrapers.utils import (
    extraer_datos_tabla,
    obtener_id_carrera,
    obtener_codigos_por_id_carrera,
)

MERCADO = 0.15
ARCHIVO_MERCADO = "db/mercado.xlsx"
HOJAS = ["Total Ingresos", "Ventas 12", "Ventas 0"]


def calc_mercado():
    # Obtener carrera de referencia
    carrera_referencia = extraer_datos_tabla("carreraReferencia")
    if not carrera_referencia:
        return


    # ID de carrera
    try:
        id_carrera = obtener_id_carrera(carrera_referencia)
    except ValueError as e:
        return

    # Códigos asociados a la carrera
    try:
        codigos = obtener_codigos_por_id_carrera(id_carrera)
    except ValueError as e:
        return

    # Procesar cada hoja del archivo Excel
    resultados_carreraReferencia = {}
    for hoja in HOJAS:
        try:
            df = pd.read_excel(ARCHIVO_MERCADO, sheet_name=hoja)
        except Exception as e:
            resultados_carreraReferencia[hoja] = 0
            continue

        if "ACTIVIDAD ECONÓMICA" not in df.columns or "2024" not in df.columns:
            resultados_carreraReferencia[hoja] = 0
            continue

        df_filtrado = df[df["ACTIVIDAD ECONÓMICA"].isin(codigos)]
        total = df_filtrado["2024"].sum()
        resultados_carreraReferencia[hoja] = total

    # Datos de la carrera a consultar
    resultados_carreraConsultar = extraer_datos_tabla("mercado")
    if not resultados_carreraConsultar:
        return

    datos_consultar = resultados_carreraConsultar[0]
    resultados_carreraConsultar_normalizado = {
        key.replace("%", "").strip(): value for key, value in datos_consultar.items()
    }

    # Calcular el promedio
    total = 0
    cantidad = 0
    for hoja in HOJAS:
        valor_ref = resultados_carreraReferencia.get(hoja, 0)
        valor_consultar = resultados_carreraConsultar_normalizado.get(hoja, 0)

        if valor_ref:
            resultado = (valor_consultar * MERCADO / valor_ref) * 100
            total += resultado
            cantidad += 1

    promedio = round(total / cantidad, 2) if cantidad else 0

    if promedio >= 15:
        promedio = 15

    return promedio

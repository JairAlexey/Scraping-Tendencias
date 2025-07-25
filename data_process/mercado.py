import pandas as pd
from scrapers.utils import (
    extraer_datos_tabla,
    obtener_id_carrera,
    obtener_codigos_por_id_carrera,
)

MERCADO = 0.15
ARCHIVO_MERCADO = "db/mercado.xlsx"
HOJAS = ["Total Ingresos", "Ventas 12", "Ventas 0"]

def calc_mercado(ruta_excel=None):
    # Obtener carrera de referencia
    carrera_referencia = extraer_datos_tabla("carreraReferencia", ruta_excel)
    if not carrera_referencia:
        print("ERROR: No se pudieron obtener datos de la carrera de referencia.")
        return

    # ID de carrera
    try:
        id_carrera = obtener_id_carrera(carrera_referencia)
    except ValueError as e:
        print(f"ERROR: No se pudo obtener el ID de la carrera: {e}.")
        return

    # Códigos asociados a la carrera
    try:
        codigos_sucios = obtener_codigos_por_id_carrera(id_carrera)
        codigos = [c.strip() for c in codigos_sucios]
    except ValueError as e:
        print(f"ERROR: No se pudieron obtener los códigos de la carrera: {e}.")
        return
    
    # Procesar cada hoja del archivo Excel
    resultados_carreraReferencia = {}
    for hoja in HOJAS:
        try:
            df = pd.read_excel(ARCHIVO_MERCADO, sheet_name=hoja)
        except Exception as e:
            print(f"ERROR: Fallo al leer la hoja '{hoja}' del archivo '{ARCHIVO_MERCADO}': {e}.")
            resultados_carreraReferencia[hoja] = 0
            continue

        if "ACTIVIDAD ECONÓMICA" not in df.columns or "2024" not in df.columns:
            print(f"ERROR: Columnas esperadas ('ACTIVIDAD ECONÓMICA' o '2024') no encontradas en la hoja '{hoja}'.")
            resultados_carreraReferencia[hoja] = 0
            continue
        
        # Asegurarse de que la columna de actividad económica también esté limpia
        if df["ACTIVIDAD ECONÓMICA"].dtype == 'object':
            df["ACTIVIDAD ECONÓMICA"] = df["ACTIVIDAD ECONÓMICA"].astype(str).str.strip()

        df_filtrado = df[df["ACTIVIDAD ECONÓMICA"].isin(codigos)]
        total = df_filtrado["2024"].sum()
        resultados_carreraReferencia[hoja] = total

    # Datos de la carrera a consultar
    resultados_carreraConsultar = extraer_datos_tabla("mercado")
    if not resultados_carreraConsultar:
        print("ERROR: No se pudieron obtener datos de la carrera a consultar.")
        return

    datos_consultar = resultados_carreraConsultar[0]
    if not isinstance(datos_consultar, dict):
        print(f"ERROR: datos_consultar is not a dict: {datos_consultar}")
        return

    resultados_carreraConsultar_normalizado = {
        key.replace("%", "").strip(): value for key, value in datos_consultar.items()
    }

    # Calcular el promedio
    total = 0
    cantidad = 0
    for hoja in HOJAS:
        valor_ref = resultados_carreraReferencia.get(hoja, 0)
        valor_consultar = resultados_carreraConsultar_normalizado.get(hoja, 0)

        try:
            valor_ref = float(valor_ref)
            valor_consultar = float(valor_consultar)
        except (ValueError, TypeError):
            print(f"ERROR: valor_ref o valor_consultar no es numérico en hoja '{hoja}': valor_ref={valor_ref}, valor_consultar={valor_consultar}")
            continue

        if valor_ref:
            resultado = (valor_consultar * MERCADO / valor_ref) * 100
            total += resultado
            cantidad += 1
        else:
            pass # No imprimir nada si no hay un error crítico aquí

    promedio = round(total / cantidad, 2) if cantidad else 0
    print(f"Promedio calculado: {promedio}")

    if promedio >= 15:
        promedio = 15

    return promedio

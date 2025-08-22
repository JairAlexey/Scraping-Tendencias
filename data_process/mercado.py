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
    print(f"\n=== INFORMACIÓN DE ARCHIVOS ===")
    print(f"Archivo de datos de mercado (referencia): {ARCHIVO_MERCADO}")
    print(f"Archivo de datos a consultar: {ruta_excel if ruta_excel else 'Base de datos interna'}")
    
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
    print(f"\n=== PROCESANDO DATOS DE REFERENCIA ===")
    print(f"Fuente: {ARCHIVO_MERCADO}")
    print(f"Carrera de referencia: {carrera_referencia}")
    print(f"ID carrera: {id_carrera}")
    print(f"Códigos de actividad económica: {codigos}")
    
    resultados_carreraReferencia = {}
    for hoja in HOJAS:
        print(f"\n--- Procesando hoja: {hoja} ---")
        try:
            df = pd.read_excel(ARCHIVO_MERCADO, sheet_name=hoja)
            print(f"Filas totales en la hoja: {len(df)}")
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
        print(f"Filas que coinciden con los códigos: {len(df_filtrado)}")
        if len(df_filtrado) > 0:
            print(f"Códigos encontrados: {df_filtrado['ACTIVIDAD ECONÓMICA'].tolist()}")
            print(f"Valores 2024 encontrados: {df_filtrado['2024'].tolist()}")
        
        total = df_filtrado["2024"].sum()
        print(f"Total para {hoja}: {total}")
        resultados_carreraReferencia[hoja] = total

    # Datos de la carrera a consultar
    print(f"\n=== DATOS DE LA CARRERA A CONSULTAR ===")
    print(f"Fuente: {ruta_excel if ruta_excel else 'Base de datos interna (tabla mercado)'}")
    
    if ruta_excel:
        # Si se proporciona un archivo Excel, extraer datos de él
        print(f"Extrayendo datos del archivo Excel: {ruta_excel}")
        resultados_carreraConsultar = extraer_datos_tabla("mercado", ruta_excel)
    else:
        # Si no se proporciona archivo, usar la base de datos interna
        print(f"Extrayendo datos de la base de datos interna")
        resultados_carreraConsultar = extraer_datos_tabla("mercado")
    
    if not resultados_carreraConsultar:
        print("ERROR: No se pudieron obtener datos de la carrera a consultar.")
        return

    print(f"Datos brutos de consulta: {resultados_carreraConsultar}")
    print(f"Tipo de datos: {type(resultados_carreraConsultar)}")
    print(f"Cantidad de registros: {len(resultados_carreraConsultar)}")
    
    datos_consultar = resultados_carreraConsultar[0]
    if not isinstance(datos_consultar, dict):
        print(f"ERROR: datos_consultar is not a dict: {datos_consultar}")
        return

    print(f"Primer elemento (datos_consultar): {datos_consultar}")
    print(f"Claves disponibles: {list(datos_consultar.keys())}")
    
    # Verificar si los valores coinciden con lo esperado
    print(f"\n=== VERIFICACIÓN DE VALORES EXTRAÍDOS ===")
    for key, value in datos_consultar.items():
        print(f"  {key}: {value} (tipo: {type(value)})")
        if isinstance(value, (int, float)) and value > 1000000:
            print(f"    -> Valor parece correcto (millones)")
        elif value is None:
            print(f"    -> Valor es None - puede ser un problema")
        elif isinstance(value, (int, float)) and value < 100000:
            print(f"    -> Valor parece bajo para datos de marketing")
    
    resultados_carreraConsultar_normalizado = {
        key.replace("%", "").strip(): value for key, value in datos_consultar.items()
    }
    print(f"Datos normalizados: {resultados_carreraConsultar_normalizado}")
    
    # Validar correspondencia de hojas
    print(f"\n=== VALIDACIÓN DE CORRESPONDENCIA ===")
    for hoja in HOJAS:
        valor_ref = resultados_carreraReferencia.get(hoja)
        valor_consultar = resultados_carreraConsultar_normalizado.get(hoja)
        print(f"Hoja '{hoja}':")
        print(f"  - Valor referencia disponible: {valor_ref is not None} (valor: {valor_ref})")
        print(f"  - Valor consultar disponible: {valor_consultar is not None} (valor: {valor_consultar})")
        print(f"  - Ambos valores numéricos: {isinstance(valor_ref, (int, float)) and valor_consultar is not None and str(valor_consultar).replace('.', '').isdigit()}")

    print(f"\n=== RESUMEN DE VALORES ===")
    print(f"Resultados carrera de referencia: {resultados_carreraReferencia}")
    print(f"Resultados carrera a consultar: {resultados_carreraConsultar_normalizado}")
    print(f"Factor MERCADO: {MERCADO}")

    # Calcular el promedio
    print(f"\n=== PROCESO DE CÁLCULO ===")
    total = 0
    cantidad = 0
    hojas_procesadas = []
    hojas_omitidas = []
    
    for hoja in HOJAS:
        print(f"\n--- Calculando para hoja: {hoja} ---")
        valor_ref = resultados_carreraReferencia.get(hoja, 0)
        valor_consultar = resultados_carreraConsultar_normalizado.get(hoja, 0)

        print(f"Valor referencia ({hoja}): {valor_ref} (tipo: {type(valor_ref)})")
        print(f"Valor consultar ({hoja}): {valor_consultar} (tipo: {type(valor_consultar)})")

        # Validar si los valores son None o vacíos
        if valor_consultar is None:
            print(f"ADVERTENCIA: Valor consultar es None para hoja '{hoja}' - Esta hoja será omitida del cálculo")
            hojas_omitidas.append(f"{hoja} (valor_consultar=None)")
            continue
        
        if valor_ref is None or valor_ref == 0:
            print(f"ADVERTENCIA: Valor referencia es None o 0 para hoja '{hoja}' - Esta hoja será omitida del cálculo")
            hojas_omitidas.append(f"{hoja} (valor_ref={valor_ref})")
            continue

        try:
            valor_ref = float(valor_ref)
            valor_consultar = float(valor_consultar)
            print(f"Valores convertidos a float - Ref: {valor_ref}, Consultar: {valor_consultar}")
        except (ValueError, TypeError) as e:
            print(f"ERROR: valor_ref o valor_consultar no es numérico en hoja '{hoja}': valor_ref={valor_ref}, valor_consultar={valor_consultar} - Error: {e}")
            hojas_omitidas.append(f"{hoja} (error conversión)")
            continue

        if valor_ref:
            resultado = (valor_consultar * MERCADO / valor_ref) * 100
            print(f"Cálculo: ({valor_consultar} * {MERCADO} / {valor_ref}) * 100 = {resultado}")
            total += resultado
            cantidad += 1
            hojas_procesadas.append(hoja)
            print(f"Total acumulado: {total}, Cantidad: {cantidad}")
        else:
            print(f"Valor de referencia es 0 o None, saltando esta hoja")
            hojas_omitidas.append(f"{hoja} (valor_ref=0)")

    print(f"\n=== RESULTADO FINAL ===")
    print(f"Hojas procesadas exitosamente: {hojas_procesadas}")
    print(f"Hojas omitidas: {hojas_omitidas}")
    print(f"Total suma de resultados: {total}")
    print(f"Cantidad de hojas procesadas: {cantidad}")
    
    promedio = round(total / cantidad, 2) if cantidad else 0
    print(f"Promedio calculado: {promedio}")

    if promedio >= 15:
        print(f"Promedio >= 15, limitando a 15")
        promedio = 15
    
    print(f"Promedio final retornado: {promedio}")
    
    # Resumen final de diagnóstico
    if len(hojas_omitidas) > 0:
        print(f"\n=== DIAGNÓSTICO ===")
        print(f"Se omitieron {len(hojas_omitidas)} de {len(HOJAS)} hojas:")
        for hoja_omitida in hojas_omitidas:
            print(f"  - {hoja_omitida}")
        print(f"Esto puede indicar:")
        print(f"  - Datos faltantes en la fuente de consulta")
        print(f"  - Problemas de mapeo entre nombres de hojas/columnas")
        print(f"  - Datos no numéricos en las fuentes")

    return promedio

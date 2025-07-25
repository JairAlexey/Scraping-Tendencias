import pandas as pd
import os
from scrapers.utils import obtener_id_carrera, extraer_datos_tabla

SEMRUSH = 0.15
TRENDS = 0.20

def calc_busquedaWeb(ruta_excel=None):

    # Extraer carrera refereencia
    carreraReferencia = extraer_datos_tabla("carreraReferencia", ruta_excel)
    if not carreraReferencia:
        print("No se pudo obtener la carrera de referencia.")
        return None

    # Obtener ID Carrera referencia
    idCarrera = obtener_id_carrera(carreraReferencia)

    # Ubicacion archivo - usar ruta específica o fallback a variable de entorno
    if ruta_excel is None:
        archivo = os.getenv("EXCEL_PATH")
    else:
        archivo = ruta_excel

    # Lectura archivo
    data = pd.read_excel(archivo, sheet_name=None)

    # --- SEMRUSH ---
    hjSemrushBase = data["SemrushBase"]
    hjSemrush = data["Semrush"]

    # --- CALCULO SEMRUSH ---
    # Filtrar en SemrushBase el ID Carrera por el id de la carrera referencia
    filtroCarrera = hjSemrushBase["ID Carrera"] == idCarrera
    datosSemrushCarrera = hjSemrushBase[filtroCarrera]
    datosSemrushCarrera_dict = datosSemrushCarrera[['Visión General', 'Palabras', 'Volumen']].iloc[0].to_dict()

    # Guardar en un diccionario datos semrush consultados
    datosSemrushConsulta_dict = hjSemrush.iloc[0].to_dict()

    # Calculos
    # Vision general
    visionGeneralBase = datosSemrushCarrera_dict['Visión General']
    visionGeneralConsulta = datosSemrushConsulta_dict['Visión General']

    if visionGeneralBase != 0:
        resVisionGeneral = ((visionGeneralConsulta * SEMRUSH) / visionGeneralBase) * 100
    else:
        resVisionGeneral = 0  # O algún valor por defecto, o puedes lanzar un warning

    # Palabras
    palabrasBase = datosSemrushCarrera_dict['Palabras']
    palabrasConsulta = datosSemrushConsulta_dict['Palabras']

    if palabrasBase != 0:
        resPalabras = ((palabrasConsulta * SEMRUSH) / palabrasBase) * 100
    else:
        resPalabras = 0

    # Volumen
    volumenBase = datosSemrushCarrera_dict['Volumen']
    volumenConsulta = datosSemrushConsulta_dict['Volumen']

    if volumenBase != 0:
        resVolumen = ((volumenConsulta * SEMRUSH) / volumenBase) * 100
    else:
        resVolumen = 0

    # Calcular el promedio de las 3 columnas
    promedioSemrush = round(((resVisionGeneral + resPalabras + resVolumen) / 3), 2)

    # --- TRENDS ---
    hjTrendsBase = data["GoogleTrendsBase"]
    hjTrends = pd.DataFrame(extraer_datos_tabla("palabrasTrends"))

    # 🔧 Normalizar columna 'Cantidad'
    hjTrends["Cantidad"] = hjTrends["Cantidad"].astype(str).str.replace(",", ".", regex=False)
    hjTrends["Cantidad"] = pd.to_numeric(hjTrends["Cantidad"], errors="coerce")

    # Extraer palabras trends base segun id
    palabrasCarreraBase = hjTrendsBase.loc[hjTrendsBase["ID Carrera"] == idCarrera]

    # Obtener el promedio de los 6 valores más altos de la columna 'Cantidad'
    promedio_basePalabras = palabrasCarreraBase["Cantidad"].nlargest(6).mean()
    promedio_consultaPalabras = hjTrends["Cantidad"].nlargest(6).mean()

    # Sumar los promedios
    if promedio_basePalabras != 0:
        promedioTrends = round(((promedio_consultaPalabras * TRENDS) / promedio_basePalabras) * 100, 2)
    else:
        promedioTrends = 0

    # --- CALCULO TOTAL ---
    # Suma promedios plataformas semrush y trends

    if promedioSemrush >= 15:
        promedioSemrush = 15

    if promedioTrends >= 20:
        promedioTrends = 20

    resBusqueda = round(promedioSemrush + promedioTrends, 2)

    return resBusqueda

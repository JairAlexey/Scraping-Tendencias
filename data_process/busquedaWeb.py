import pandas as pd
from scrapers.utils import obtener_id_carrera, extraer_datos_tabla

SEMRUSH = 0.15
TRENDS = 0.20

def calc_busquedaWeb():

    # Extraer carrera refereencia
    carreraReferencia = extraer_datos_tabla("carreraReferencia")
    if not carreraReferencia:
        print("No se pudo obtener la carrera de referencia.")
        return None

    # Obtener ID Carrera referencia
    idCarrera = obtener_id_carrera(carreraReferencia)

    # Ubicacion archivo
    archivo = 'db/data.xlsx'

    # Lectura archivo
    data = pd.read_excel(archivo, sheet_name=None)

    # Definir dataframes (hojas) a utilizar
    # --- SEMRUSH ---
    hjSemrushBase = data["SemrushBase"]
    hjSemrush = data["Semrush"]

    # --- TRENDS ---
    hjTrendsBase = data["GoogleTrendsBase"]
    hjTrends = data["GoogleTrends"]

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

    resVisionGeneral = ((visionGeneralConsulta * SEMRUSH) / visionGeneralBase) * 100

    # Palabras
    palabrasBase = datosSemrushCarrera_dict['Palabras']
    palabrasConsulta = datosSemrushConsulta_dict['Palabras']

    resPalabras = ((palabrasConsulta * SEMRUSH) / palabrasBase) * 100

    # Volumen
    volumenBase = datosSemrushCarrera_dict['Volumen']
    volumenConsulta = datosSemrushConsulta_dict['Volumen']

    resVolumen = ((volumenConsulta * SEMRUSH) / volumenBase) * 100

    # Calcular el promedio de las 3 columnas
    promedioSemrush = round(((resVisionGeneral + resPalabras + resVolumen) / 3), 2)

    # --- CALCULO TRENDS ---

    

    # Suma promedios plataformas semrush y trends
    resBusqueda = promedioSemrush

    return resBusqueda

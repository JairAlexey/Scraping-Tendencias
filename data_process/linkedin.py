import pandas as pd
import os

ECU = 0.15
LATAM = 0.10

def calc_linkedin(ruta_excel=None):

    # Archivo excel - usar ruta específica o fallback a variable de entorno
    if ruta_excel is None:
        archivo = os.getenv("EXCEL_PATH")
    else:
        archivo = ruta_excel
        print(f"Usando ruta específica: {archivo}")

    # Cargar el archivo y utillizar hoja de 'Linkedin'
    data = pd.read_excel(archivo, sheet_name='LinkedIn')

    # Separar datos por region
    # ECUADOR
    filtroEC = data["Region"] == "Ecuador"
    data_ecuador = data[filtroEC]

    # referencia
    data_ecuadorRef = data_ecuador.loc[data["Tipo"] == "Referencia"].reset_index(drop=True)

    # consulta
    data_ecuadorCon = data_ecuador.loc[data["Tipo"] == "Consulta"].reset_index(drop=True)

    # CALCULOS ECUADOR
    # Referencia
    profesionalesRefEc = data_ecuadorRef["Profesionales"][0]
    empleoRefEc = data_ecuadorRef["Anuncios de empleo"][0]
    anuncios_profesionalesRefEc = data_ecuadorRef["%Anuncios/Profesionales"][0]

    # Consulta
    profesionalesConEc = data_ecuadorCon["Profesionales"][0]
    empleoConEc = data_ecuadorCon["Anuncios de empleo"][0]
    anuncios_profesionalesConEc = data_ecuadorCon["%Anuncios/Profesionales"][0]

    # Promedio
    resProfesionalesEc = ((profesionalesConEc * ECU) / profesionalesRefEc) * 100
    resEmpleoEc = ((empleoConEc * ECU) / empleoRefEc) * 100
    resAnunEmpEc = ((anuncios_profesionalesConEc * ECU) / anuncios_profesionalesRefEc) * 100

    resPromedioEc = round((resProfesionalesEc + resEmpleoEc + resAnunEmpEc) / 3, 2)

    # LATAM
    filtroLATAM = data["Region"] == "América Latina"
    data_latam = data[filtroLATAM]

    # referencia
    data_latamRef = data_latam.loc[data["Tipo"] == "Referencia"].reset_index(drop=True)

    # consulta
    data_latamCon = data_latam.loc[data["Tipo"] == "Consulta"].reset_index(drop=True)

    # CALCULOS LATAM
    # Referencia
    profesionalesRefLat = data_latamRef["Profesionales"][0]
    empleoRefLat = data_latamRef["Anuncios de empleo"][0]
    anuncios_profesionalesRefLat = data_latamRef["%Anuncios/Profesionales"][0]

    # Consulta
    profesionalesConLat = data_latamCon["Profesionales"][0]
    empleoConLat = data_latamCon["Anuncios de empleo"][0]
    anuncios_profesionalesConLat = data_latamCon["%Anuncios/Profesionales"][0]

    # Promedio
    resProfesionalesLat = ((profesionalesConLat * LATAM) / profesionalesRefLat) * 100
    resEmpleoLat = ((empleoConLat * LATAM) / empleoRefLat) * 100
    resAnunEmpLat = (
        (anuncios_profesionalesConLat * LATAM) / anuncios_profesionalesRefLat
    ) * 100

    resPromedioLat = round((resProfesionalesLat + resEmpleoLat + resAnunEmpLat) / 3, 2)

    if resPromedioEc >= 15:
        resPromedioEc = 15

    if resPromedioLat >= 10:
        resPromedioLat = 10

    # Suma promedios
    promGeneral = resPromedioEc + resPromedioLat

    return promGeneral

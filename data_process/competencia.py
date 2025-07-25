import pandas as pd
from data_process.busquedaWeb import calc_busquedaWeb
from scrapers.utils import extraer_datos_tabla

# Calcular resultado para competencia virtual y presencial
def obtener_resultado(busqueda, competencia):
    if busqueda >= 25:
        if competencia < 5:
            return 25
        else:
            return 20
    else:
        if competencia >= 5:
            return 15
        else:
            return 10


def calc_competencia_virtual(ruta_excel=None):
    # Calculo busqueda web para este archivo específico
    busquedaWeb = calc_busquedaWeb(ruta_excel)
    
    # Extrayendo ofertas para este archivo específico
    dataOfertas = extraer_datos_tabla("ofertaCarrera", ruta_excel)

    # oferta virtual
    competencia_virtual = dataOfertas[0]["Virtualidad"]

    resVirtual = obtener_resultado(busquedaWeb, competencia_virtual)

    if resVirtual >= 25:
        resVirtual = 25

    return resVirtual


def calc_competencia_presencial(ruta_excel=None):
    # Calculo busqueda web para este archivo específico
    busquedaWeb = calc_busquedaWeb(ruta_excel)
    
    # Extrayendo ofertas para este archivo específico
    dataOfertas = extraer_datos_tabla("ofertaCarrera", ruta_excel)

    # oferta presencial
    competencia_presencial = dataOfertas[0]["Presencialidad"]

    resPresencial = obtener_resultado(busquedaWeb, competencia_presencial)

    if resPresencial >= 25:
        resPresencial = 25

    return resPresencial

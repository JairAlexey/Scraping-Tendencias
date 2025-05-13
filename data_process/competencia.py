import pandas as pd
from data_process.busquedaWeb import calc_busquedaWeb
from scrapers.utils import extraer_datos_tabla

# Calculo busqueda web
busquedaWeb = calc_busquedaWeb()

# Extrayendo ofertas
dataOfertas = extraer_datos_tabla("ofertaCarrera")

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


def calc_competencia_virtual():

    # oferta virtual
    competencia_virtual = dataOfertas[0]["Virtualidad"]

    resVirtual = obtener_resultado(busquedaWeb, competencia_virtual)

    if resVirtual >= 25:
        resVirtual = 25

    return resVirtual


def calc_competencia_presencial():

    # oferta presencial
    competencia_presencial = dataOfertas[0]["Presencialidad"]

    resPresencial = obtener_resultado(busquedaWeb, competencia_presencial)

    if resPresencial >= 25:
        resPresencial = 25

    return resPresencial

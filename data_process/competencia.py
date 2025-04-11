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
            return 20
        else:
            return 15
    else:
        if competencia >= 5:
            return 5
        else:
            return 0


def calc_competencia_virtual():

    # oferta virtual
    competencia_virtual = dataOfertas[0]["Virtualidad"]

    return obtener_resultado(busquedaWeb, competencia_virtual)


def calc_competencia_presencial():

    # oferta presencial
    competencia_presencial = dataOfertas[0]["Presencialidad"]

    return obtener_resultado(busquedaWeb, competencia_presencial)

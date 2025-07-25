import xlwings as xw
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

def obtener_rutas_excel():
    """
    Obtiene las rutas de archivos Excel desde las variables de entorno.
    Soporta EXCEL_PATHS (múltiples rutas separadas por comas) o EXCEL_PATH (una sola ruta).
    Devuelve una lista de rutas válidas (mínimo 1).
    """
    # Intentar obtener múltiples rutas primero
    excel_paths = os.getenv("EXCEL_PATHS")
    if excel_paths:
        rutas = [ruta.strip() for ruta in excel_paths.split(",") if ruta.strip()]
        
        # Verificar que los archivos existen
        rutas_validas = []
        for ruta in rutas:
            if os.path.exists(ruta):
                rutas_validas.append(ruta)
            else:
                print(f"⚠️ Archivo no encontrado: {ruta}")
        
        if rutas_validas:
            return rutas_validas
    
    # Si no hay EXCEL_PATHS válidas, usar EXCEL_PATH como fallback
    excel_path = os.getenv("EXCEL_PATH")
    if excel_path and os.path.exists(excel_path):
        return [excel_path]
    
    raise ValueError("❌ No se encontraron rutas de Excel válidas en las variables de entorno.")

def extraer_datos_tabla(nombre_tabla, ruta_excel=None):
    """
    Extrae datos de una tabla específica de un archivo Excel.
    Si no se especifica ruta_excel, usa la primera ruta disponible.
    """
    if ruta_excel is None:
        rutas = obtener_rutas_excel()
        ruta_excel = rutas[0]
    
    # Abrir Excel en modo invisible
    app = xw.App(visible=False)
    wb = app.books.open(ruta_excel)
    sht = wb.sheets["Input"]

    try:
        tabla = sht.tables[nombre_tabla]
        df = tabla.range.options(pd.DataFrame, expand="table", index=False).value

        if nombre_tabla in ["reporteLinkedin", "mercado", "palabrasTrends", "ofertaCarrera"]:
            # Devolver todo el dataframe como lista de diccionarios
            resultado = df.to_dict(orient="records") if not df.empty else []

        elif nombre_tabla in ["carreraSemrush", "carreraReferencia"]:
            # Devolver el único valor de la tabla (una sola celda)
            if df.shape == (1, 1):
                resultado = df.iat[0, 0]
            else:
                raise ValueError("La tabla 'carreraSemrush' no tiene el formato esperado (1x1).")

        else:
            raise ValueError(f"Tabla '{nombre_tabla}' no está permitida.")

    except KeyError:
        resultado = f"La tabla '{nombre_tabla}' no existe."
    finally:
        wb.close()
        app.quit()

    return resultado

def guardar_datos_excel(data, plataforma, ruta_excel=None):
    """
    Inserta resultados en la hoja y tabla correspondientes, dependiendo de la plataforma.
    Si no se especifica ruta_excel, usa la primera ruta disponible.

    - LinkedIn:
        Hoja: 'LinkedIn'
        Tabla: 'datoLinkedin'
        Se aplican columnas: "Tipo", "Region", "Profesionales", ...
        (dos primeros registros: "Referencia", resto: "Consulta")

    - Semrush:
        Hoja: 'Semrush'
        Tabla: 'datoSemrush'
        Columnas: "Visión General", "Palabras", "Volumen"
        (no se usan "Referencia"/"Consulta")
    """

    if not data:
        print("⚠️ No hay datos para guardar.")
        return

    if ruta_excel is None:
        rutas = obtener_rutas_excel()
        ruta_excel = rutas[0]

    print(f"📁 Guardando datos en: {ruta_excel}")

    # Abrir Excel en segundo plano
    app = xw.App(visible=False)
    wb = app.books.open(ruta_excel)

    # Lógica de plataformas
    if plataforma.lower() == "linkedin":
        hoja_destino = "LinkedIn"
        tabla_destino = "datoLinkedin"

        # --------------------------------------------------------------------------------------
        # Transformación para LinkedIn
        # --------------------------------------------------------------------------------------

        # Asignar tipo: Referencia (2 primeros), Consulta (resto)
        tipos = ["Referencia"] * 2 + ["Consulta"] * max(0, len(data) - 2)
        for i, item in enumerate(data):
            item["Tipo"] = tipos[i]
            # Normalizar el valor de anuncios_empleo si es '--', None, o vacío
            anuncios = item.get("anuncios_empleo", "")
            if anuncios is None or str(anuncios).strip() in ["--", ""]:
                item["anuncios_empleo"] = "1"

        # Convertir a DataFrame
        df = pd.DataFrame(data)
        # Renombrar a las columnas esperadas en LinkedIn
        df.rename(
            columns={
                "ubicacion": "Region",
                "profesionales": "Profesionales",
                "anuncios_empleo": "Anuncios de empleo",
                "demanda_contratacion": "Demanda de contratacion",
            },
            inplace=True,
        )

        # Calcular columna adicional: %Anuncios/Profesionales
        try:
            df["Anuncios de empleo"] = df["Anuncios de empleo"].str.replace(".", "").str.replace(",", "").astype(float)
            df["Profesionales"] = df["Profesionales"].str.replace(".", "").str.replace(",", "").astype(float)
            df["%Anuncios/Profesionales"] = ((df["Anuncios de empleo"] / df["Profesionales"]) * 100).round(2)
        except:
            df["%Anuncios/Profesionales"] = None

        # Reordenar columnas según tabla destino
        df = df[
            [
                "Tipo",
                "Region",
                "Profesionales",
                "Anuncios de empleo",
                "%Anuncios/Profesionales",
                "Demanda de contratacion",
            ]
        ]

    elif plataforma.lower() == "semrush":
        hoja_destino = "Semrush"
        tabla_destino = "datoSemrush"

        # --------------------------------------------------------------------------------------
        # Transformación para Semrush
        # --------------------------------------------------------------------------------------
        # En tu scraping, devuelves keys como:
        #   "vision_general", "palabras", "volumen"
        # Queremos guardarlas en la tabla con columnas: "Visión General", "Palabras", "Volumen"

        df = pd.DataFrame(data)
        # Renombrar las columnas a las definitivas en la hoja de Excel
        df.rename(
            columns={
                "vision_general": "Visión General",
                "palabras": "Palabras",
                "volumen": "Volumen",
            },
            inplace=True,
        )

        # Reordenar por si acaso (en caso la tabla de Excel tenga el orden: Visión General, Palabras, Volumen)
        df = df[["Visión General", "Palabras", "Volumen"]]

    else:
        # Plataforma no reconocida, cerramos Excel y salimos
        wb.close()
        app.quit()
        raise ValueError(f"Plataforma '{plataforma}' no está configurada.")

    # ------------------------------------------------------------------------------------------
    # INSERCIÓN EN EXCEL
    # ------------------------------------------------------------------------------------------
    sht = wb.sheets[hoja_destino]
    tabla = sht.tables[tabla_destino]

    # Insertar en la primera fila de datos (debajo de la cabecera):
    start_row = tabla.range.row + 1
    sht.range(f"A{start_row}").value = df.values.tolist()

    wb.save()
    wb.close()
    app.quit()
    print(f"📊 Datos guardados en Excel correctamente (plataforma: {plataforma}, archivo: {os.path.basename(ruta_excel)}).")

def obtener_id_carrera(nombre_carrera, ruta_excel=None):
    if ruta_excel is None:
        rutas = obtener_rutas_excel()
        ruta_excel = rutas[0]
        
    try:
        df = pd.read_excel(ruta_excel, sheet_name="Carreras", engine="openpyxl")
        carrera_filtrada = df[df["Carrera"] == nombre_carrera]

        if carrera_filtrada.empty:
            raise ValueError(f"No se encontró ninguna carrera para '{nombre_carrera}'.")

        return carrera_filtrada.iloc[0]["ID"]

    except Exception as e:
        raise ValueError(f"Error al obtener ID de carrera: {e}")

def obtener_codigos_por_id_carrera(id_carrera, ruta_excel=None):
    if ruta_excel is None:
        rutas = obtener_rutas_excel()
        ruta_excel = rutas[0]
        
    try:
        df = pd.read_excel(ruta_excel, sheet_name="Codigos", engine="openpyxl")
        codigos_filtrados = df[df["ID Carrera"] == id_carrera]

        if codigos_filtrados.empty:
            raise ValueError(f"No se encontraron códigos para ID '{id_carrera}'.")

        return codigos_filtrados["Codigo"].dropna().tolist()

    except Exception as e:
        raise ValueError(f"Error al obtener códigos por ID de carrera: {e}")

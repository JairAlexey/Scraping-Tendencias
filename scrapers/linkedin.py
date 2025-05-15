import undetected_chromedriver as uc
from scrapers.utils import extraer_datos_tabla, guardar_datos_excel
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv
import os
import time


# -----------------------------------------------------------------------------
# FUNCIÓN: Buscar carpeta en la página actual
# -----------------------------------------------------------------------------
def buscar_carpeta_en_pagina(driver, carpeta_buscar):
    """
    Recorre los elementos de carpeta (articles) de la página actual y
    si encuentra la carpeta buscada, navega a su URL y retorna True.
    """
    folder_cards = driver.find_elements(By.CSS_SELECTOR, "article.saved-folder-card")
    for card in folder_cards:
        try:
            link_title = card.find_element(
                By.CSS_SELECTOR, "a.saved-folder-card__link-title"
            )
            nombre_carpeta = link_title.text.strip()
            href_carpeta = link_title.get_attribute("href")
            if nombre_carpeta.lower() == carpeta_buscar.lower():
                print(f"✅ Carpeta encontrada: {nombre_carpeta}")
                driver.get(href_carpeta)
                time.sleep(4)
                return True
        except Exception as e:
            print("Error al leer la carpeta:", e)
            continue
    return False


# -----------------------------------------------------------------------------
# FUNCIÓN: Extraer datos de un reporte dado un filtro de ubicación
# -----------------------------------------------------------------------------
def extraer_datos_reporte(driver, UBICACION, carpeta_nombre, proyecto_nombre):
    """
    Aplica el filtro de ubicación y extrae los datos (profesionales, anuncios y demanda)
    de la página de un reporte.
    Devuelve un diccionario con los datos extraídos.
    """
    datos = {}
    try:
        # Localizar el div del filtro de ubicación
        div_ubicacion = driver.find_element(
            By.CSS_SELECTOR, 'div.query-facet[data-query-type="LOCATION"]'
        )

        # Desplazar la vista hasta el div
        driver.execute_script("arguments[0].scrollIntoView(true);", div_ubicacion)
        time.sleep(3)

        try:
            # Intentar borrar filtros previos
            boton_borrar = div_ubicacion.find_element(
                By.CSS_SELECTOR, "button[data-test-clear-all]"
            )
            boton_borrar.click()
            print("🧹 Filtros borrados")
            time.sleep(5)
        except:
            print("ℹ️ No había filtros que borrar")

        # Desplegar el input de ubicación
        try:
            btn_mostrar_input = div_ubicacion.find_element(
                By.CSS_SELECTOR, "button.query-facet__add-button"
            )
            btn_mostrar_input.click()
            print("➕ Botón '+' de añadir filtro clickeado")
            time.sleep(5)
        except Exception as e:
            print("⚠️ No se pudo hacer clic en el botón '+':", e)

        # Ingresar la ubicación en el input
        input_field = div_ubicacion.find_element(
            By.CSS_SELECTOR, "input.artdeco-typeahead__input"
        )
        input_field.clear()
        input_field.send_keys(UBICACION)
        time.sleep(5)

        # Buscar y seleccionar la sugerencia correspondiente
        sugerencias = div_ubicacion.find_elements(
            By.CSS_SELECTOR, "ul.artdeco-typeahead__results-list li"
        )
        match = False
        for sug in sugerencias:
            txt_sug = sug.text.strip().lower()
            if UBICACION.lower() in txt_sug:
                time.sleep(3)
                sug.click()
                print(f"📌 Ubicación seleccionada: {txt_sug}")
                match = True
                break
        if not match:
            print(f"❌ No se encontró sugerencia para: {UBICACION}")
            return None

        time.sleep(3)
        try:
            # Confirmar la selección de la ubicación
            btn_confirmar = div_ubicacion.find_element(
                By.CSS_SELECTOR, "button.artdeco-pill__button"
            )
            btn_confirmar.click()
            print("✅ Confirmación con botón '+'")
            time.sleep(3)
        except:
            print("⚠️ Botón '+' no encontrado")

        try:
            # Aplicar el filtro
            btn_aplicar = driver.find_element(
                By.CSS_SELECTOR, "button[data-test-search-filters-apply-btn]"
            )
            btn_aplicar.click()
            print("🎯 Filtro aplicado")
        except:
            print("❌ Botón 'Aplicar' no encontrado")
            return None

        time.sleep(15)
        print(f"⏳ Extrayendo datos para {UBICACION}...")

        # Extraer datos de las tarjetas superiores
        top_cards = driver.find_elements(
            By.CSS_SELECTOR, "li.overview-layout__top-card"
        )
        profesionales = anuncios_empleo = None
        for card in top_cards:
            try:
                tipo = (
                    card.find_element(
                        By.CSS_SELECTOR, ".overview-layout__top-card-type"
                    )
                    .text.strip()
                    .lower()
                )
                valor = card.find_element(
                    By.CSS_SELECTOR, ".overview-layout__top-card-value"
                ).text.strip()
                if "profesionales" == tipo:
                    profesionales = valor
                elif "anuncios de empleo" in tipo:
                    anuncios_empleo = valor
            except Exception as e:
                print("⚠️ Error al extraer datos de una tarjeta:", e)
                continue

        # Intentar extraer la demanda de contratación; si no se encuentra, se asigna None
        try:
            span_demanda = driver.find_element(
                By.CSS_SELECTOR,
                "div.overview-layout__hdi--reading span.overview-layout__hdi--value",
            )
            demanda_contratacion = span_demanda.text.strip()
        except Exception as e:
            print("⚠️ No se encontró el elemento de demanda de contratación:", e)
            demanda_contratacion = None

        # Construir el diccionario con los datos
        datos = {
            "carpeta": carpeta_nombre,
            "proyecto": proyecto_nombre,
            "ubicacion": UBICACION,
            "profesionales": profesionales,
            "anuncios_empleo": anuncios_empleo,
            "demanda_contratacion": demanda_contratacion,
        }
        print(
            f"📥 Datos guardados para {UBICACION}: profesionales={profesionales}, anuncios={anuncios_empleo}"
        )
        time.sleep(10)
        return datos

    except Exception as e:
        print(f"❌ Error inesperado en extraer_datos_reporte para {UBICACION}: {e}")
        return None


# -----------------------------------------------------------------------------
# FUNCIÓN: Buscar el proyecto (reporte) en la página actual de la carpeta
# -----------------------------------------------------------------------------
def buscar_proyecto_en_pagina(
    driver, proyecto_buscar, ubicaciones, carpeta_nombre, resultados_finales
):
    """
    Recorre las filas (reportes) de la tabla en la página actual.
    Si encuentra el reporte cuyo nombre coincide con 'proyecto_buscar',
    navega a su URL, y para cada ubicación definida llama a extraer_datos_reporte().
    Devuelve True si se encontró y procesó el proyecto.
    """
    rows = driver.find_elements(By.CSS_SELECTOR, "tr.artdeco-models-table-row")
    # Desplazar la vista hasta vista completa tabla
    rows = driver.find_elements(By.CSS_SELECTOR, "tr.artdeco-models-table-row")
    if rows:
        driver.execute_script("arguments[0].scrollIntoView(true);", rows[0])

    for row in rows:
        try:
            span = row.find_element(
                By.CSS_SELECTOR,
                "td.saved-reports-table__table-cell--display-name a div span",
            )
            texto = span.text.strip()
            print("🔍 Revisando reporte:", texto)
            if texto.lower() == proyecto_buscar.lower():
                print("✅ Proyecto encontrado:", texto)
                enlace = row.find_element(
                    By.CSS_SELECTOR,
                    "td.saved-reports-table__table-cell--display-name a",
                )
                href = enlace.get_attribute("href")
                print("🔗 Navegando a:", href)
                driver.get(href)
                time.sleep(5)
                # Lista temporal para almacenar resultados de cada ubicación
                resultados = []
                for UBICACION in ubicaciones:
                    print(f"\n🌍 Aplicando ubicación: {UBICACION}")
                    datos = extraer_datos_reporte(
                        driver, UBICACION, carpeta_nombre, texto
                    )
                    if datos:
                        resultados.append(datos)
                resultados_finales.extend(resultados)
                return True
        except Exception as e:
            print("⚠️ Error revisando fila de reporte:", e)
            continue
    return False


def linkedin_scraper():
    # -----------------------------------------------------------------------------
    # CONFIGURACIÓN: Cargar variables de entorno y definir parámetros iniciales
    # -----------------------------------------------------------------------------
    load_dotenv()
    EMAIL = os.getenv("LINKEDIN_USER")
    PASSWORD = os.getenv("LINKEDIN_PASS")

    # Extraemos la tabla de reportes; se espera que cada elemento tenga las claves "Carpeta" y "Proyecto"
    reportes = extraer_datos_tabla("reporteLinkedin")
    # Lista de ubicaciones a filtrar
    UBICACIONES = ["Ecuador", "América Latina"]

    # CONFIGURACIÓN
    user_data_dir = r"C:\Users\andrei.flores\Documents\Trabajo\Scraping-Tendencias\profile"
    profile_directory = "Default"

    # LIMPIEZA DEL LOCK
    full_profile_path = os.path.join(user_data_dir, profile_directory)
    singleton_lock = os.path.join(full_profile_path, "SingletonLock")
    if os.path.exists(singleton_lock):
        print("🧯 Eliminando archivo de bloqueo previo (SingletonLock)...")
        os.remove(singleton_lock)

    # OPCIONES DE CHROME
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument(f"--profile-directory={profile_directory}")

    # LANZAR EL DRIVER
    driver = uc.Chrome(options=options)

    # -------------------------------------------------------------------------
    # INICIAR SESIÓN EN LINKEDIN
    # -------------------------------------------------------------------------
    print("🌐 Abriendo LinkedIn Login...")
    driver.get("https://www.linkedin.com/login")
    time.sleep(3)

    if "login" in driver.current_url:
        print("🔐 Iniciando sesión en LinkedIn...")

        try:
            driver.find_element(By.ID, "username").send_keys(EMAIL)
            driver.find_element(By.ID, "password").send_keys(PASSWORD + Keys.RETURN)
            time.sleep(60)

            if "linkedin.com/feed" in driver.current_url:
                print("✅ Sesión iniciada correctamente.")
            else:
                print(
                    "❌ No se redirigió al feed. Login fallido o requiere verificación."
                )
                driver.quit()
                return

        except Exception as e:
            print(f"❌ Error durante el login: {e}")
            driver.quit()
            return
    else:
        print("✅ Ya estabas logueado. Redirigido automáticamente.")

    # -------------------------------------------------------------------------
    # ACCEDER A INSIGHTS
    # -------------------------------------------------------------------------
    url = "https://www.linkedin.com/insights/saved?reportType=talent&tab=folders"
    driver.get(url)
    time.sleep(5)

    # Lista para almacenar los resultados finales
    resultados_finales = []

    # -----------------------------------------------------------------------------
    # PROCESAR CADA ELEMENTO DEL REPORTE (Carpeta + Proyecto)
    # -----------------------------------------------------------------------------
    for elemento in reportes:
        # Se esperan las claves "Carpeta" y "Proyecto" en cada elemento
        carpeta_buscar = elemento.get("Carpeta")
        proyecto_buscar = elemento.get("Proyecto")

        print(
            f"\n=== Buscando carpeta '{carpeta_buscar}' y proyecto '{proyecto_buscar}' ==="
        )
        try:
            paginacion_carpetas = driver.find_elements(
                By.CSS_SELECTOR,
                ".saved-folders-layout .artdeco-pagination ul.artdeco-pagination__pages li",
            )
        except:
            paginacion_carpetas = []

        encontrada = buscar_carpeta_en_pagina(driver, carpeta_buscar)

        # Si no se encontró en la página inicial, se recorre la paginación de reportes
        if not encontrada and paginacion_carpetas:
            for li in paginacion_carpetas:
                if "selected" in li.get_attribute("class"):
                    continue
                try:
                    btn = li.find_element(By.TAG_NAME, "button")
                    ActionChains(driver).move_to_element(btn).click().perform()
                    time.sleep(3)
                    if buscar_carpeta_en_pagina(driver, carpeta_buscar):
                        encontrada = True
                        break
                except Exception as e:
                    print("⚠️ Error al cambiar página de carpetas:", e)
                    continue

        if not encontrada:
            print(f"❌ No se encontró la carpeta '{carpeta_buscar}'")
            driver.get(url)
            time.sleep(3)
            continue

        # Una vez dentro de la carpeta, se busca el proyecto (reporte)
        try:
            layout = driver.find_element(By.CLASS_NAME, "saved-reports-layout")
            paginacion_reports = driver.find_elements(
                By.CSS_SELECTOR,
                "div.artdeco-models-table-pagination__pagination-cmpt ul.artdeco-pagination__pages li",
            )
        except Exception as e:
            print("❌ Error al localizar la sección de reportes:", e)
            paginacion_reports = []

        proyecto_encontrado = buscar_proyecto_en_pagina(
            driver, proyecto_buscar, UBICACIONES, carpeta_buscar, resultados_finales
        )

        # Si no se encontró en la página inicial, se recorre la paginación de reportes
        if not proyecto_encontrado and paginacion_reports:
            num_pag = len(paginacion_reports)
            for i in range(num_pag):
                paginacion_reports = driver.find_elements(
                    By.CSS_SELECTOR,
                    "div.artdeco-models-table-pagination__pagination-cmpt ul.artdeco-pagination__pages li",
                )
                li = paginacion_reports[i]
                if "selected" in li.get_attribute("class"):
                    continue
                try:
                    btn = li.find_element(By.TAG_NAME, "button")
                    ActionChains(driver).move_to_element(btn).click().perform()
                    time.sleep(3)
                    if buscar_proyecto_en_pagina(
                        driver,
                        proyecto_buscar,
                        UBICACIONES,
                        carpeta_buscar,
                        resultados_finales,
                    ):
                        proyecto_encontrado = True
                        break
                except Exception as e:
                    print("⚠️ Error al cambiar página de reportes:", e)
                    continue

        if not proyecto_encontrado:
            print(
                f"❌ No se encontró el proyecto '{proyecto_buscar}' dentro de la carpeta '{carpeta_buscar}'."
            )

        # Volver a la vista de carpetas para continuar con el siguiente elemento
        driver.get(url)
        time.sleep(20)

    # -----------------------------------------------------------------------------
    # Exportar resultados a Excel
    # -----------------------------------------------------------------------------
    if resultados_finales:
        guardar_datos_excel(resultados_finales, plataforma="LinkedIn")
    else:
        print("ℹ️ No se obtuvieron resultados.")

    driver.quit()  # Descomenta para cerrar el navegador al finalizar

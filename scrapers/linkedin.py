import undetected_chromedriver as uc
from scrapers.utils import extraer_datos_tabla, guardar_datos_excel
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv
import os
import time
import unicodedata

# === NUEVO ===  (soporta espera/refresco si aparece el banner de error)
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------------------------------------------------------------------
# === NUEVO ===  utilidades para detectar y reintentar cuando aparece
#                el aviso “Para ver el informe, modifica la búsqueda…”
# ---------------------------------------------------------------------
ERROR_SELECTORS = [
    "div.artdeco-toast-item[data-test-artdeco-toast-item-type='error']",
    "div.search-filters__notice-v2"
]

# === CONFIGURACIÓN GLOBAL DE TIEMPOS ===
TIEMPO_ESPERA_CORTO = 2   # segundos para esperas cortas
TIEMPO_ESPERA_MEDIO = 4   # segundos para esperas medias
TIEMPO_ESPERA_LARGO = 6  # segundos para esperas largas
TIEMPO_ESPERA_BANNER = 40 # espera cuando aparece el banner de error
TIEMPO_ESPERA_PAGINA = 8 # espera larga para recarga de página

def hay_banner_error(driver, timeout=TIEMPO_ESPERA_CORTO):
    """
    Devuelve True si alguno de los selectores de ERROR está visible
    (no solo presente en el DOM).
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: any(
                el.is_displayed()             # 👈 visibilidad real
                for sel in ERROR_SELECTORS
                for el in d.find_elements(By.CSS_SELECTOR, sel)
            )
        )
        return True
    except TimeoutException:
        return False

def esperar_elemento(driver, by, selector, timeout=TIEMPO_ESPERA_LARGO):
    try:
        return WebDriverWait(driver, timeout).until(
            lambda d: d.find_element(by, selector)
        )
    except TimeoutException:
        return None

def esperar_elemento_visible(driver, by, selector, timeout=TIEMPO_ESPERA_LARGO):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, selector))
        )
    except TimeoutException:
        return None

def esperar_y_refrescar_si_banner(driver, max_intentos=3, espera_seg=TIEMPO_ESPERA_BANNER, ubicacion=None, re_aplicar_filtro=None):
    """
    Si aparece el banner, espera `espera_seg` segundos, refresca y reintenta.
    Después de refrescar, verifica y re-aplica el filtro de ubicación si es necesario.
    Devuelve True  -> el banner desapareció (OK para continuar)
             False -> persiste tras `max_intentos` (hay que omitir el reporte)
    """
    intento = 0
    while hay_banner_error(driver) and intento < max_intentos:
        intento += 1
        print(f"⚠️ Banner de 0 resultados visto. "
              f"Esperando {espera_seg}s y refrescando… (intento {intento}/{max_intentos})")
        time.sleep(espera_seg)
        driver.refresh()
        # Esperar a que el filtro de ubicación esté presente tras el refresh
        filtro_ok = False
        for _ in range(3):
            div_ubicacion = esperar_elemento(driver, By.CSS_SELECTOR, 'div.query-facet[data-query-type="LOCATION"]', timeout=TIEMPO_ESPERA_LARGO)
            if div_ubicacion:
                filtro_ok = True
                break
            print("⏳ Esperando a que el filtro de ubicación esté disponible tras el refresh...")
            time.sleep(TIEMPO_ESPERA_MEDIO)
        if not filtro_ok:
            print("❌ No se encontró el filtro de ubicación tras el refresh. Se omite este reporte.")
            return False
        # Si se provee función para re-aplicar filtro, verificar y re-aplicar
        if re_aplicar_filtro and ubicacion:
            if not re_aplicar_filtro(driver, ubicacion):
                print("❌ No se pudo re-aplicar el filtro tras el refresh. Se omite este reporte.")
                return False
            time.sleep(TIEMPO_ESPERA_MEDIO)
    return not hay_banner_error(driver)

def esperar_resultados_o_banner(driver, timeout=TIEMPO_ESPERA_LARGO):
    """
    Espera a que aparezcan resultados (tarjetas o tabla) o que el banner de error persista.
    Devuelve 'resultados' si aparecen datos, 'banner' si persiste el banner, o 'timeout' si no hay nada.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        # ¿Hay tarjetas de resultados?
        top_cards = driver.find_elements(By.CSS_SELECTOR, "li.overview-layout__top-card")
        if top_cards:
            return 'resultados'
        # ¿Hay tabla de resultados?
        tabla = driver.find_elements(By.CSS_SELECTOR, "tr.artdeco-models-table-row")
        if tabla:
            return 'resultados'
        # ¿Sigue el banner de error?
        if hay_banner_error(driver, timeout=TIEMPO_ESPERA_CORTO):
            return 'banner'
        time.sleep(TIEMPO_ESPERA_CORTO)
    return 'timeout'

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
                time.sleep(TIEMPO_ESPERA_MEDIO)
                return True
        except Exception as e:
            print("Error al leer la carpeta:", e)
            continue
    return False

def normalizar_texto(texto):
    # Quitar tildes, pasar a minúsculas y quitar espacios extra
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto.strip().lower()

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
    def aplicar_filtro(driver, UBICACION):
        try:
            div_ubicacion = None
            for _ in range(2):
                try:
                    div_ubicacion = esperar_elemento(driver, By.CSS_SELECTOR, 'div.query-facet[data-query-type="LOCATION"]', timeout=TIEMPO_ESPERA_LARGO)
                    if div_ubicacion:
                        break
                except StaleElementReferenceException:
                    continue
            if not div_ubicacion:
                print("❌ No se encontró el filtro de ubicación para aplicar.")
                return False
            driver.execute_script("arguments[0].scrollIntoView(true);", div_ubicacion)
            time.sleep(TIEMPO_ESPERA_MEDIO)
            # --- Comprobar si la ubicación ya está aplicada ---
            chips_aplicados = []
            for _ in range(2):
                try:
                    chips_aplicados = div_ubicacion.find_elements(By.CSS_SELECTOR, "div.facet-pill__pill-text")
                    break
                except StaleElementReferenceException:
                    continue
            # Si no hay chips, esperar y reintentar una vez
            if not chips_aplicados:
                print("⏳ No se detectaron chips aplicados, esperando para reintentar...")
                time.sleep(TIEMPO_ESPERA_CORTO)
                try:
                    chips_aplicados = div_ubicacion.find_elements(By.CSS_SELECTOR, "div.facet-pill__pill-text")
                except Exception:
                    chips_aplicados = []
            ubicaciones_aplicadas = []
            for chip in chips_aplicados:
                try:
                    raw_text = chip.text.strip()
                    clean_text = normalizar_texto(raw_text)
                    ubicaciones_aplicadas.append(clean_text)
                except Exception:
                    continue
            ub_comparar = normalizar_texto(UBICACION)
            print(f"🔎 Chips detectados: {ubicaciones_aplicadas} | Buscando: '{ub_comparar}'")
            if ub_comparar in ubicaciones_aplicadas:
                print(f"✅ La ubicación '{UBICACION}' ya está aplicada. No se modifica el filtro.")
                return True
            # --- Solo borrar filtros si la ubicación no está aplicada ---
            try:
                boton_borrar = None
                for _ in range(2):
                    try:
                        boton_borrar = div_ubicacion.find_element(By.CSS_SELECTOR, "button[data-test-clear-all]")
                        break
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue
                if boton_borrar:
                    boton_borrar.click()
                    print("🧹 Filtros borrados")
                    time.sleep(TIEMPO_ESPERA_MEDIO)
            except Exception:
                pass  # Silenciar si no hay botón de borrar
            try:
                btn_mostrar_input = None
                for _ in range(2):
                    try:
                        btn_mostrar_input = div_ubicacion.find_element(By.CSS_SELECTOR, "button.query-facet__add-button")
                        break
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue
                if btn_mostrar_input:
                    btn_mostrar_input.click()
                    print("➕ Botón '+' de añadir filtro clickeado")
                    time.sleep(TIEMPO_ESPERA_MEDIO)
            except Exception:
                pass  # Silenciar si no hay botón
            try:
                input_field = None
                for _ in range(2):
                    try:
                        input_field = div_ubicacion.find_element(By.CSS_SELECTOR, "input.artdeco-typeahead__input")
                        break
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue
                if not input_field:
                    print(f"❌ No se encontró el input para la ubicación '{UBICACION}'")
                    return False
                input_field.clear()
                input_field.send_keys(UBICACION)
                time.sleep(TIEMPO_ESPERA_MEDIO)
            except Exception:
                print(f"❌ No se pudo interactuar con el input de ubicación para '{UBICACION}'")
                return False
            sugerencias = []
            for _ in range(2):
                try:
                    sugerencias = div_ubicacion.find_elements(By.CSS_SELECTOR, "ul.artdeco-typeahead__results-list li")
                    break
                except StaleElementReferenceException:
                    continue
            match = False
            for sug in sugerencias:
                try:
                    txt_sug = sug.text.strip().lower()
                    if UBICACION.lower() in txt_sug:
                        time.sleep(TIEMPO_ESPERA_CORTO)
                        sug.click()
                        print(f"📌 Ubicación seleccionada: {txt_sug}")
                        match = True
                        break
                except Exception:
                    continue
            if not match:
                print(f"❌ No se encontró sugerencia para: {UBICACION}")
                return False
            time.sleep(TIEMPO_ESPERA_MEDIO)
            try:
                btn_confirmar = None
                for _ in range(2):
                    try:
                        btn_confirmar = div_ubicacion.find_element(By.CSS_SELECTOR, "button.artdeco-pill__button")
                        break
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue
                if btn_confirmar:
                    btn_confirmar.click()
                    print("✅ Confirmación con botón '+'")
                    time.sleep(TIEMPO_ESPERA_LARGO)
            except Exception:
                pass  # Silenciar si no hay botón
            # Esperar a que el botón 'Aplicar' esté habilitado
            try:
                WebDriverWait(driver, TIEMPO_ESPERA_LARGO).until(
                    lambda d: (
                        (btn := d.find_element(By.CSS_SELECTOR, "button[data-test-search-filters-apply-btn]")) and
                        btn.is_enabled() and btn.get_attribute("disabled") is None
                    )
                )
                btn_aplicar = None
                for _ in range(2):
                    try:
                        btn_aplicar = driver.find_element(By.CSS_SELECTOR, "button[data-test-search-filters-apply-btn]")
                        break
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue
                if not btn_aplicar:
                    print(f"❌ No se encontró el botón 'Aplicar' para '{UBICACION}'")
                    return 'recargar'
                btn_aplicar.click()
                print("🎯 Filtro aplicado")
                resultado = esperar_resultados_o_banner(driver, timeout=TIEMPO_ESPERA_LARGO)
                if resultado == 'resultados':
                    print("✅ Resultados detectados tras aplicar el filtro.")
                    return True
                elif resultado == 'banner':
                    print("⚠️ Banner de 0 resultados persiste tras aplicar el filtro.")
                    return False
                else:
                    print("⚠️ Timeout esperando resultados tras aplicar el filtro.")
                    return False
            except (TimeoutException, ElementClickInterceptedException, NoSuchElementException, StaleElementReferenceException):
                print(f"❌ Botón 'Aplicar' no clickeable o no habilitado para '{UBICACION}'")
                return 'recargar'
            return True
        except Exception as e:
            print(f"❌ Error aplicando filtro de ubicación: {e}")
            return False
    try:
        intentos = 0
        max_intentos = 3
        exito = False
        while intentos < max_intentos:
            print(f"\n🔁 Intento {intentos+1}/{max_intentos} para aplicar el filtro de ubicación '{UBICACION}'")
            resultado_filtro = aplicar_filtro(driver, UBICACION)
            if resultado_filtro is True:
                # Verificar que realmente se puedan extraer datos (hay resultados)
                top_cards = driver.find_elements(By.CSS_SELECTOR, "li.overview-layout__top-card")
                if top_cards:
                    exito = True
                    break
                else:
                    print(f"⚠️ Filtro '{UBICACION}' parece aplicado pero no hay resultados, esperando {TIEMPO_ESPERA_BANNER}s antes de reintentar...")
                    time.sleep(TIEMPO_ESPERA_BANNER)
                    intentos += 1
                    continue
            elif resultado_filtro == 'recargar':
                print(f"🔄 Intentando recargar y re-aplicar filtro para '{UBICACION}' (intento {intentos+1}/{max_intentos})")
                if not esperar_y_refrescar_si_banner(driver, max_intentos=1, espera_seg=TIEMPO_ESPERA_BANNER, ubicacion=UBICACION, re_aplicar_filtro=aplicar_filtro):
                    intentos += 1
                    continue
                # Tras recargar, volver a intentar aplicar el filtro
                intentos += 1
                continue
            else:
                intentos += 1
        if not exito:
            print(f"🔴 No se pudo aplicar el filtro para '{UBICACION}' tras {max_intentos} intentos. Se omite este reporte.")
            return None
        # Confirmar que no hay banner de error antes de extraer datos
        if not esperar_y_refrescar_si_banner(driver, max_intentos=3, espera_seg=TIEMPO_ESPERA_BANNER, ubicacion=UBICACION, re_aplicar_filtro=aplicar_filtro):
            print(f"🔴 Persisten 0 resultados para '{UBICACION}'. Se omite este reporte.")
            return None
        time.sleep(TIEMPO_ESPERA_MEDIO)
        print(f"⏳ Extrayendo datos para {UBICACION}...")
        top_cards = driver.find_elements(By.CSS_SELECTOR, "li.overview-layout__top-card")
        profesionales = anuncios_empleo = None
        for card in top_cards:
            try:
                tipo = card.find_element(By.CSS_SELECTOR, ".overview-layout__top-card-type").text.strip().lower()
                valor = card.find_element(By.CSS_SELECTOR, ".overview-layout__top-card-value").text.strip()
                if "profesionales" == tipo:
                    profesionales = valor
                elif "anuncio de empleo" in tipo or "anuncios de empleo" in tipo:
                    anuncios_empleo = valor
            except Exception as e:
                print("⚠️ Error al extraer datos de una tarjeta:", e)
                continue
        try:
            span_demanda = driver.find_element(By.CSS_SELECTOR, "div.overview-layout__hdi--reading span.overview-layout__hdi--value")
            demanda_contratacion = span_demanda.text.strip()
        except Exception as e:
            print("⚠️ No se encontró el elemento de demanda de contratación:", e)
            demanda_contratacion = None
        datos = {
            "carpeta": carpeta_nombre,
            "proyecto": proyecto_nombre,
            "ubicacion": UBICACION,
            "profesionales": profesionales,
            "anuncios_empleo": anuncios_empleo,
            "demanda_contratacion": demanda_contratacion,
        }
        print(f"📥 Datos guardados para {UBICACION}: profesionales={profesionales}, anuncios={anuncios_empleo}")
        time.sleep(TIEMPO_ESPERA_LARGO)
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
                time.sleep(TIEMPO_ESPERA_MEDIO)
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

    if not EMAIL or not PASSWORD:
        print("❌ Faltan credenciales de LinkedIn. Verifica las variables de entorno LINKEDIN_USER y LINKEDIN_PASS.")
        return

    # Extraemos la tabla de reportes; se espera que cada elemento tenga las claves "Carpeta" y "Proyecto"
    reportes = extraer_datos_tabla("reporteLinkedin")
    # Lista de ubicaciones a filtrar
    UBICACIONES = ["Ecuador", "América Latina"]

    # CONFIGURACIÓN
    user_data_dir = r"C:\Users\User\Documents\TRABAJO - UDLA\Scraping-Tendencias\profile"
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
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-features=EnableChromeSignin")
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    options.add_experimental_option("prefs", prefs)

    driver = uc.Chrome(options=options)

    # -------------------------------------------------------------------------
    # INICIAR SESIÓN EN LINKEDIN
    # -------------------------------------------------------------------------
    print("🌐 Abriendo LinkedIn Login...")
    driver.get("https://www.linkedin.com/login")
    time.sleep(TIEMPO_ESPERA_CORTO)

    if "login" in driver.current_url:
        print("🔐 Iniciando sesión en LinkedIn...")

        try:
            campo_usuario = driver.find_element(By.ID, "username")
            campo_contrasena = driver.find_element(By.ID, "password")

            campo_usuario.clear()
            campo_usuario.send_keys(EMAIL)
            campo_contrasena.clear()
            campo_contrasena.send_keys(PASSWORD + Keys.RETURN)
            time.sleep(TIEMPO_ESPERA_CORTO)

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
    time.sleep(TIEMPO_ESPERA_MEDIO)

    # Lista para almacenar los resultados finales
    resultados_finales = []

    # -----------------------------------------------------------------------------
    # PROCESAR CADA ELEMENTO DEL REPORTE (Carpeta + Proyecto)
    # -----------------------------------------------------------------------------
    for elemento in reportes:
        # Se esperan las claves "Carpeta" y "Proyecto" en cada elemento
        if isinstance(elemento, dict):
            carpeta_buscar = elemento.get("Carpeta")
            proyecto_buscar = elemento.get("Proyecto")
        else:
            print(f"❌ Formato inesperado en elemento de reportes: {elemento}")
            continue

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
                class_attr = li.get_attribute("class")
                if class_attr and "selected" in class_attr:
                    continue
                try:
                    btn = li.find_element(By.TAG_NAME, "button")
                    ActionChains(driver).move_to_element(btn).click().perform()
                    time.sleep(TIEMPO_ESPERA_CORTO)
                    if buscar_carpeta_en_pagina(driver, carpeta_buscar):
                        encontrada = True
                        break
                except Exception as e:
                    print("⚠️ Error al cambiar página de carpetas:", e)
                    continue

        if not encontrada:
            print(f"❌ No se encontró la carpeta '{carpeta_buscar}'")
            driver.get(url)
            time.sleep(TIEMPO_ESPERA_CORTO)
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
                class_attr = li.get_attribute("class")
                if class_attr and "selected" in class_attr:
                    continue
                try:
                    btn = li.find_element(By.TAG_NAME, "button")
                    ActionChains(driver).move_to_element(btn).click().perform()
                    time.sleep(TIEMPO_ESPERA_CORTO)
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
        time.sleep(TIEMPO_ESPERA_PAGINA)

    # -----------------------------------------------------------------------------
    # Exportar resultados a Excel
    # -----------------------------------------------------------------------------
    if resultados_finales:
        guardar_datos_excel(resultados_finales, plataforma="LinkedIn")
    else:
        print("ℹ️ No se obtuvieron resultados.")

    driver.quit()  # Descomenta para cerrar el navegador al finalizar

import undetected_chromedriver as uc
from scrapers.utils import extraer_datos_tabla, guardar_datos_excel, obtener_rutas_excel
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
    "div[data-test-artdeco-toast-item-type='error']",
    "div.search-filters__notice-v2"
]

# === CONFIGURACIÓN GLOBAL DE TIEMPOS ===
TIEMPO_ESPERA_CORTO = 1   # segundos para esperas cortas  
TIEMPO_ESPERA_MEDIO = 2   # segundos para esperas medias
TIEMPO_ESPERA_LARGO = 4   # segundos para esperas largas
TIEMPO_ESPERA_BANNER = 40 # espera cuando aparece el banner de error (reducido considerablemente)
TIEMPO_ESPERA_PAGINA = 3  # espera larga para recarga de página

def hay_banner_error(driver, timeout=TIEMPO_ESPERA_CORTO):
    """
    Devuelve True si hay un banner de error de LinkedIn presente.
    Detecta el banner específico que aparece con el mensaje de modificar búsqueda.
    """
    try:
        # Buscar el banner de error específico que aparece
        banner_error = driver.find_element(By.CSS_SELECTOR, 'div[data-test-artdeco-toast-item-type="error"]')
        if banner_error and banner_error.is_displayed():
            # Verificar que contenga el mensaje de error de búsqueda
            mensaje = banner_error.text.lower()
            if "modifica la búsqueda" in mensaje or "modify your search" in mensaje or "informe" in mensaje:
                return True
    except (NoSuchElementException, StaleElementReferenceException):
        pass
    
    # Fallback: verificar selectores adicionales
    try:
        for selector in ERROR_SELECTORS:
            elementos = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elementos:
                if el.is_displayed():
                    texto = el.text.lower()
                    if "modifica la búsqueda" in texto or "modify your search" in texto:
                        return True
    except Exception:
        pass
    
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
        print(f"🔄 Banner error - Refrescando... ({intento}/{max_intentos})")
        time.sleep(espera_seg)
        driver.refresh()
        
        # Esperar más tiempo para que la página se cargue completamente
        time.sleep(TIEMPO_ESPERA_PAGINA * 2)  # Esperar el doble de tiempo
        
        # Verificar que el banner ya no esté presente después del refresh
        if hay_banner_error(driver):
            print(f"⚠️ Banner aún presente después del refresh {intento}")
            continue
        
        # Esperar a que el filtro de ubicación esté presente tras el refresh
        filtro_ok = False
        for intento_filtro in range(5):  # Aumentar intentos de verificación
            div_ubicacion = esperar_elemento(driver, By.CSS_SELECTOR, 'div.query-facet[data-query-type="LOCATION"]', timeout=TIEMPO_ESPERA_LARGO)
            if div_ubicacion:
                # Verificar que el elemento esté realmente visible e interactuable
                try:
                    if div_ubicacion.is_displayed() and div_ubicacion.is_enabled():
                        filtro_ok = True
                        break
                except:
                    pass
            time.sleep(TIEMPO_ESPERA_MEDIO)
        
        if not filtro_ok:
            print(f"❌ Filtro de ubicación no disponible después de refresh {intento}")
            return False
        
        # Después del refresh, limpiar cualquier filtro que pueda haberse quedado
        try:
            time.sleep(TIEMPO_ESPERA_MEDIO)
            # Intentar diferentes métodos para limpiar filtros
            boton_borrar = div_ubicacion.find_element(By.CSS_SELECTOR, "button[data-test-clear-all]")
            if boton_borrar and boton_borrar.is_displayed():
                print(f"🧹 Limpiando filtros tras refresh")
                boton_borrar.click()
                time.sleep(TIEMPO_ESPERA_MEDIO)
        except NoSuchElementException:
            # Si no hay botón de limpiar todo, intentar limpiar chips individuales
            try:
                chips_remove = div_ubicacion.find_elements(By.CSS_SELECTOR, "button.facet-pill__remove")
                if chips_remove:
                    print(f"🧹 Limpiando filtros individualmente tras refresh")
                    for chip_remove in chips_remove:
                        if chip_remove.is_displayed():
                            chip_remove.click()
                            time.sleep(0.5)
                else:
                    print(f"ℹ️ No hay filtros que limpiar tras refresh")
            except Exception as e:
                print(f"⚠️ No se pudieron limpiar filtros tras refresh: {e}")
        except Exception as e:
            print(f"⚠️ Error general limpiando filtros tras refresh: {e}")
            
        # Si se provee función para re-aplicar filtro, verificar y re-aplicar
        if re_aplicar_filtro and ubicacion:
            # Verificar que no haya banner antes de re-aplicar
            if hay_banner_error(driver):
                print(f"⚠️ Banner detectado antes de re-aplicar filtro")
                return False
            
            if not re_aplicar_filtro(driver, ubicacion):
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
        # Primero verificar si hay banner de error
        if hay_banner_error(driver, timeout=0.5):
            print("🚨 Banner de error detectado")
            return 'banner'
            
        # ¿Hay tarjetas de resultados?
        top_cards = driver.find_elements(By.CSS_SELECTOR, "li.overview-layout__top-card")
        if top_cards and len(top_cards) > 0:
            # Verificar que las tarjetas tienen contenido real
            for card in top_cards:
                try:
                    valor = card.find_element(By.CSS_SELECTOR, ".overview-layout__top-card-value")
                    if valor and valor.text.strip():
                        return 'resultados'
                except:
                    continue
        
        # ¿Hay tabla de resultados?
        tabla = driver.find_elements(By.CSS_SELECTOR, "tr.artdeco-models-table-row")
        if tabla and len(tabla) > 0:
            return 'resultados'
            
        time.sleep(0.5)
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
            # VERIFICACIÓN INICIAL DE BANNER antes de cualquier interacción
            if hay_banner_error(driver):
                print(f"🚨 Banner detectado al inicio de aplicar_filtro para '{UBICACION}'")
                return False
            
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
            
            # VERIFICACIÓN DE BANNER después de localizar elementos
            if hay_banner_error(driver):
                print(f"🚨 Banner detectado después de localizar filtro para '{UBICACION}'")
                return False
            # --- Comprobar si la ubicación ya está aplicada ---
            # Verificar solo en la barra de filtros (método más confiable)
            ubicaciones_aplicadas = []
            ub_comparar = normalizar_texto(UBICACION)
            
            print(f"🔍 Verificando barra de filtros para '{UBICACION}'...")
            
            # Múltiples intentos para leer elementos de la barra de filtros
            filters_bar_elements = []
            for intento_lectura in range(5):  # Hasta 5 intentos
                try:
                    # Esperar antes de cada intento
                    time.sleep(TIEMPO_ESPERA_MEDIO)
                    
                    filters_bar_elements = driver.find_elements(By.CSS_SELECTOR, 'span.filters-bar__filter-item[data-test-talent-filters-bar-location-filter]')
                    print(f"   Intento {intento_lectura + 1}: Encontrados {len(filters_bar_elements)} elementos")
                    
                    if filters_bar_elements:
                        # Verificar si al menos uno tiene texto no vacío
                        elementos_con_texto = 0
                        for elem in filters_bar_elements:
                            try:
                                if elem.text.strip():
                                    elementos_con_texto += 1
                            except:
                                continue
                        
                        if elementos_con_texto > 0:
                            print(f"   ✅ {elementos_con_texto} elementos con texto encontrados")
                            break
                        else:
                            print(f"   ⚠️ Elementos encontrados pero todos están vacíos, esperando más...")
                            if intento_lectura < 4:  # No esperar en el último intento
                                time.sleep(TIEMPO_ESPERA_LARGO)
                    else:
                        print(f"   ⚠️ No se encontraron elementos, esperando más...")
                        if intento_lectura < 4:  # No esperar en el último intento
                            time.sleep(TIEMPO_ESPERA_LARGO)
                            
                except Exception as e:
                    print(f"   ⚠️ Error en intento {intento_lectura + 1}: {e}")
                    if intento_lectura < 4:
                        time.sleep(TIEMPO_ESPERA_MEDIO)
                    continue
            
            # Procesar elementos encontrados
            if filters_bar_elements:
                for i, filter_elem in enumerate(filters_bar_elements):
                    try:
                        # Intentar leer el texto con múltiples intentos
                        filter_text = ""
                        for intento_texto in range(3):
                            try:
                                time.sleep(TIEMPO_ESPERA_CORTO)
                                filter_text = filter_elem.text.strip()
                                if filter_text:  # Si encontró texto, salir del loop
                                    break
                                elif intento_texto < 2:  # Si no hay texto, esperar un poco más
                                    time.sleep(TIEMPO_ESPERA_MEDIO)
                            except:
                                if intento_texto < 2:
                                    time.sleep(TIEMPO_ESPERA_MEDIO)
                                continue
                        
                        print(f"   Elemento {i+1}: '{filter_text}'")
                        
                        if filter_text:
                            clean_text = normalizar_texto(filter_text)
                            # Verificar coincidencia exacta con la ubicación buscada
                            if ub_comparar == clean_text:
                                print(f"   ✅ Coincidencia exacta encontrada: '{filter_text}' = '{UBICACION}'")
                                ubicaciones_aplicadas.append(clean_text)
                            else:
                                print(f"   ❌ No coincide: '{clean_text}' ≠ '{ub_comparar}'")
                        else:
                            print(f"   ⚠️ Elemento {i+1} está vacío después de múltiples intentos")
                            
                    except Exception as e:
                        print(f"   ⚠️ Error procesando elemento {i+1}: {e}")
                        continue
            else:
                print(f"   ❌ No se encontraron elementos de barra de filtros después de múltiples intentos")
            
            # Mostrar filtros detectados para debugging
            if ubicaciones_aplicadas:
                print(f"🔎 Filtros aplicados: {ubicaciones_aplicadas}")
            else:
                print(f"🔎 Filtros aplicados: [''] (ningún filtro detectado)")
            
            # SIEMPRE limpiar filtros antes de aplicar uno nuevo (excepto si es exactamente el mismo)
            if len(ubicaciones_aplicadas) == 1 and ub_comparar in ubicaciones_aplicadas:
                print(f"✅ Filtro '{UBICACION}' ya aplicado correctamente")
                return True
            else:
                # VERIFICACIÓN DE BANNER antes de limpiar filtros
                if hay_banner_error(driver):
                    print(f"🚨 Banner detectado antes de limpiar filtros para '{UBICACION}'")
                    return False
                
                # Limpiar TODOS los filtros existentes
                print(f"🧹 Limpiando filtros existentes antes de aplicar '{UBICACION}'")
                try:
                    boton_borrar = div_ubicacion.find_element(By.CSS_SELECTOR, "button[data-test-clear-all]")
                    if boton_borrar and boton_borrar.is_displayed():
                        boton_borrar.click()
                        time.sleep(TIEMPO_ESPERA_MEDIO)
                        print(f"✅ Filtros limpiados")
                except NoSuchElementException:
                    print(f"ℹ️ No se encontró botón de limpiar todo, intentando limpiar individualmente")
                    # Intentar método alternativo: hacer clic en las X de cada chip
                    try:
                        chips_remove = div_ubicacion.find_elements(By.CSS_SELECTOR, "button.facet-pill__remove")
                        if chips_remove:
                            for chip_remove in chips_remove:
                                if chip_remove.is_displayed():
                                    chip_remove.click()
                                    time.sleep(0.5)
                            print(f"✅ Filtros limpiados individualmente")
                        else:
                            print(f"ℹ️ No hay filtros que limpiar")
                    except Exception as e2:
                        print(f"⚠️ No se pudieron limpiar filtros individualmente: {e2}")
                except Exception as e:
                    print(f"⚠️ Error general limpiando filtros: {e}")
                    # Intentar método alternativo: hacer clic en las X de cada chip
                    try:
                        chips_remove = div_ubicacion.find_elements(By.CSS_SELECTOR, "button.facet-pill__remove")
                        if chips_remove:
                            for chip_remove in chips_remove:
                                if chip_remove.is_displayed():
                                    chip_remove.click()
                                    time.sleep(0.5)
                            print(f"✅ Filtros limpiados individualmente")
                    except Exception as e2:
                        print(f"⚠️ No se pudieron limpiar filtros individualmente: {e2}")
            
            # Asegurar que el input esté limpio y visible
            try:
                btn_mostrar_input = div_ubicacion.find_element(By.CSS_SELECTOR, "button.query-facet__add-button")
                if btn_mostrar_input and btn_mostrar_input.is_displayed():
                    btn_mostrar_input.click()
                    time.sleep(TIEMPO_ESPERA_MEDIO)
            except Exception:
                pass
            
            # VERIFICACIÓN DE BANNER antes de intentar escribir en el campo
            if hay_banner_error(driver):
                print(f"🚨 Banner detectado antes de escribir en campo para '{UBICACION}'")
                return False
            
            # Limpiar e ingresar nueva ubicación
            try:
                input_field = div_ubicacion.find_element(By.CSS_SELECTOR, "input.artdeco-typeahead__input")
                if not input_field:
                    print(f"❌ No se encontró el campo de entrada")
                    return False
                
                # Asegurar que el campo esté completamente limpio
                input_field.clear()
                time.sleep(0.5)
                input_field.send_keys(Keys.CONTROL + "a")  # Seleccionar todo
                input_field.send_keys(Keys.DELETE)  # Borrar
                time.sleep(0.5)
                
                print(f"📝 Escribiendo '{UBICACION}' en el campo de ubicación")
                input_field.send_keys(UBICACION)
                time.sleep(TIEMPO_ESPERA_MEDIO)
            except NoSuchElementException:
                print(f"❌ Campo de entrada no encontrado, posible problema de carga de página")
                # Verificar si hay banner que esté causando el problema
                if hay_banner_error(driver):
                    print(f"🚨 Banner detectado cuando falta campo de entrada")
                    return False
                # Si no hay banner, podría ser un problema de timing, devolver False para reintentar
                return False
            except Exception as e:
                print(f"❌ Error al interactuar con el campo de entrada: {e}")
                return False
            
            # Buscar y seleccionar sugerencia
            try:
                # Esperar a que aparezcan las sugerencias
                WebDriverWait(driver, TIEMPO_ESPERA_LARGO).until(
                    lambda d: d.find_elements(By.CSS_SELECTOR, "ul.artdeco-typeahead__results-list li")
                )
                
                sugerencias = div_ubicacion.find_elements(By.CSS_SELECTOR, "ul.artdeco-typeahead__results-list li")
                match = False
                
                print(f"🔍 Buscando coincidencia para '{UBICACION}' entre {len(sugerencias)} sugerencias")
                
                for i, sug in enumerate(sugerencias):
                    try:
                        txt_sug = sug.text.strip().lower()
                        print(f"   {i+1}. '{txt_sug}'")
                        
                        # Coincidencia exacta o si la ubicación está contenida en la sugerencia
                        if UBICACION.lower() == txt_sug or UBICACION.lower() in txt_sug:
                            print(f"✅ Coincidencia encontrada: '{txt_sug}'")
                            time.sleep(TIEMPO_ESPERA_CORTO)
                            
                            # Seleccionar sugerencia con ActionChains
                            try:
                                ActionChains(driver).move_to_element(sug).click().perform()
                                time.sleep(TIEMPO_ESPERA_MEDIO)
                                match = True
                            except Exception as e:
                                print(f"❌ Error seleccionando sugerencia: {e}")
                                continue
                            
                            break
                    except Exception as e:
                        print(f"   Error procesando sugerencia {i+1}: {e}")
                        continue
                
                if not match:
                    print(f"❌ No se encontró coincidencia para '{UBICACION}'")
                    return False
                    
                print(f"✅ Sugerencia seleccionada para '{UBICACION}'")
                
                # Buscar y hacer clic en cualquier botón de confirmación que pueda aparecer
                try:
                    # Esperar un momento para que aparezca el botón de confirmación si existe
                    time.sleep(TIEMPO_ESPERA_MEDIO)
                    
                    # Buscar diferentes tipos de botones de confirmación
                    botones_confirmacion = [
                        "button.artdeco-pill__button",
                        "button[data-test-typeahead-result-add-btn]",
                        "button.artdeco-typeahead__add-button",
                        "button.facet-pill__confirm-button",
                        "button[aria-label*='Add']",
                        "button[title*='Add']"
                    ]
                    
                    confirmacion_encontrada = False
                    for selector_boton in botones_confirmacion:
                        try:
                            btn_confirmar_inmediato = div_ubicacion.find_element(By.CSS_SELECTOR, selector_boton)
                            if btn_confirmar_inmediato and btn_confirmar_inmediato.is_displayed() and btn_confirmar_inmediato.is_enabled():
                                print(f"🔄 Confirmando selección con botón: {selector_boton}")
                                btn_confirmar_inmediato.click()
                                time.sleep(TIEMPO_ESPERA_MEDIO)
                                confirmacion_encontrada = True
                                break
                        except Exception:
                            continue
                    
                    if not confirmacion_encontrada:
                        # Estrategia alternativa: Presionar ENTER en el input si aún está visible
                        try:
                            input_field = div_ubicacion.find_element(By.CSS_SELECTOR, "input.artdeco-typeahead__input")
                            if input_field.is_displayed():
                                input_field.send_keys(Keys.ENTER)
                                time.sleep(TIEMPO_ESPERA_MEDIO)
                        except Exception:
                            pass
                            
                except Exception:
                    pass
            except TimeoutException:
                print(f"⏱️ Timeout esperando sugerencias para '{UBICACION}'")
                return False
            except Exception as e:
                print(f"❌ Error al seleccionar sugerencia: {e}")
                return False
            
            time.sleep(TIEMPO_ESPERA_LARGO)  # Esperar para que se procese la selección
            
            # Si después de la selección no hay filtros, intentar una estrategia manual
            try:
                chips_verificacion_final = div_ubicacion.find_elements(By.CSS_SELECTOR, "div.facet-pill__pill-text")
                if not chips_verificacion_final:
                    # Buscar específicamente el texto de la ubicación en toda la sección y hacer clic
                    elementos_con_texto = div_ubicacion.find_elements(By.XPATH, f".//*[contains(text(), '{UBICACION}') or contains(text(), '{UBICACION.lower()}')]")
                    for elem in elementos_con_texto:
                        try:
                            if elem.is_displayed():
                                driver.execute_script("arguments[0].click();", elem)
                                time.sleep(TIEMPO_ESPERA_MEDIO)
                                # Verificar si apareció el chip
                                chips_post_manual = div_ubicacion.find_elements(By.CSS_SELECTOR, "div.facet-pill__pill-text")
                                if chips_post_manual:
                                    break
                        except Exception:
                            continue
            except Exception:
                pass
            
            # Confirmar ubicación (si existe el botón de confirmación principal)
            try:
                btn_confirmar = div_ubicacion.find_element(By.CSS_SELECTOR, "button.artdeco-pill__button")
                if btn_confirmar and btn_confirmar.is_displayed():
                    print(f"🔄 Confirmando selección de '{UBICACION}' con botón principal")
                    btn_confirmar.click()
                    time.sleep(TIEMPO_ESPERA_LARGO)
            except Exception:
                # No siempre existe el botón de confirmación, continuar
                pass
            
            # Verificar que el filtro se aplicó correctamente antes de proceder
            print(f"🔄 Verificando que el filtro '{UBICACION}' se aplicó correctamente...")
            filtro_aplicado_correctamente = False
            
            # Intentar verificar hasta 5 veces con esperas incrementales
            for intento_verificacion in range(5):
                try:
                    time.sleep(TIEMPO_ESPERA_MEDIO)  # Esperar antes de cada verificación
                    
                    # Re-obtener el div_ubicacion por si se ha actualizado
                    div_ubicacion_verificacion = esperar_elemento(driver, By.CSS_SELECTOR, 'div.query-facet[data-query-type="LOCATION"]', timeout=TIEMPO_ESPERA_LARGO)
                    if not div_ubicacion_verificacion:
                        continue
                        
                    chips_verificacion = div_ubicacion_verificacion.find_elements(By.CSS_SELECTOR, "div.facet-pill__pill-text")
                    ubicaciones_verificacion = []
                    
                    for chip in chips_verificacion:
                        try:
                            raw_text = chip.text.strip()
                            if raw_text:
                                clean_text = normalizar_texto(raw_text)
                                ubicaciones_verificacion.append(clean_text)
                        except Exception:
                            continue
                    
                    ub_verificar = normalizar_texto(UBICACION)
                    print(f"   Intento {intento_verificacion + 1}: Filtros actuales: {ubicaciones_verificacion}")
                    
                    if ub_verificar in ubicaciones_verificacion:
                        print(f"✅ Filtro '{UBICACION}' aplicado correctamente")
                        filtro_aplicado_correctamente = True
                        break
                    else:
                        # Si no se aplicó, esperar más tiempo antes del siguiente intento
                        if intento_verificacion < 4:  # No esperar en el último intento
                            time.sleep(TIEMPO_ESPERA_MEDIO)
                        
                except Exception as e:
                    print(f"   Error en verificación {intento_verificacion + 1}: {e}")
                    continue
            
            if not filtro_aplicado_correctamente:
                print(f"❌ Filtro '{UBICACION}' no se aplicó correctamente después de 5 verificaciones")
                return False
            # Aplicar filtro
            try:
                WebDriverWait(driver, TIEMPO_ESPERA_LARGO).until(
                    lambda d: (
                        (btn := d.find_element(By.CSS_SELECTOR, "button[data-test-search-filters-apply-btn]")) and
                        btn.is_enabled() and btn.get_attribute("disabled") is None
                    )
                )
                btn_aplicar = driver.find_element(By.CSS_SELECTOR, "button[data-test-search-filters-apply-btn]")
                if not btn_aplicar:
                    return False
                
                btn_aplicar.click()
                time.sleep(TIEMPO_ESPERA_MEDIO)
                
                # Esperar un poco más para que se procese la búsqueda
                resultado = esperar_resultados_o_banner(driver, timeout=TIEMPO_ESPERA_LARGO * 2)
                if resultado == 'resultados':
                    return True
                elif resultado == 'banner':
                    print(f"🚨 Error en búsqueda para '{UBICACION}' - Banner detectado")
                    return False
                else:
                    print(f"⏱️ Timeout esperando resultados para '{UBICACION}'")
                    return False
            except (TimeoutException, ElementClickInterceptedException, NoSuchElementException, StaleElementReferenceException):
                return False
            
            return True
        except Exception as e:
            print(f"❌ Error aplicando filtro de ubicación: {e}")
            return False
    try:
        intentos = 0
        max_intentos = 5
        exito = False
        
        while intentos < max_intentos:
            intentos += 1
            print(f"� Aplicando '{UBICACION}' (Intento {intentos}/{max_intentos})")
            
            resultado_filtro = aplicar_filtro(driver, UBICACION)
            
            if resultado_filtro is True:
                # Verificar que haya datos disponibles
                top_cards = driver.find_elements(By.CSS_SELECTOR, "li.overview-layout__top-card")
                if top_cards and len(top_cards) > 0:
                    # Verificar que las tarjetas tienen datos reales
                    tiene_datos = False
                    for card in top_cards:
                        try:
                            valor = card.find_element(By.CSS_SELECTOR, ".overview-layout__top-card-value")
                            if valor and valor.text.strip() and valor.text.strip() != "--":
                                tiene_datos = True
                                break
                        except:
                            continue
                    if tiene_datos:
                        exito = True
                        break
                    else:
                        print(f"⚠️ Sin datos válidos para '{UBICACION}', esperando {TIEMPO_ESPERA_BANNER}s, refrescando y reintentando...")
                        time.sleep(TIEMPO_ESPERA_BANNER)
                        print(f"🔄 Refrescando página tras espera...")
                        driver.refresh()
                        time.sleep(TIEMPO_ESPERA_PAGINA)
                        
                        # Verificar que el filtro de ubicación esté disponible tras refresh
                        div_ubicacion_check = esperar_elemento(driver, By.CSS_SELECTOR, 'div.query-facet[data-query-type="LOCATION"]', timeout=TIEMPO_ESPERA_LARGO)
                        if not div_ubicacion_check:
                            print(f"❌ Filtro de ubicación no disponible tras refresh")
                            continue
                else:
                    print(f"⚠️ Sin resultados para '{UBICACION}', esperando {TIEMPO_ESPERA_BANNER}s, refrescando y reintentando...")
                    time.sleep(TIEMPO_ESPERA_BANNER)
                    print(f"🔄 Refrescando página tras espera...")
                    driver.refresh()
                    time.sleep(TIEMPO_ESPERA_PAGINA)
                    
                    # Verificar que el filtro de ubicación esté disponible tras refresh
                    div_ubicacion_check = esperar_elemento(driver, By.CSS_SELECTOR, 'div.query-facet[data-query-type="LOCATION"]', timeout=TIEMPO_ESPERA_LARGO)
                    if not div_ubicacion_check:
                        print(f"❌ Filtro de ubicación no disponible tras refresh")
                        continue
                continue
            else:
                print(f"❌ Fallo en intento {intentos}")
                # Si hay banner de error, esperar 40s antes de refrescar
                if hay_banner_error(driver):
                    print(f"🚨 Banner detectado tras fallo, esperando {TIEMPO_ESPERA_BANNER}s antes de refrescar...")
                    if not esperar_y_refrescar_si_banner(driver, max_intentos=1, espera_seg=TIEMPO_ESPERA_BANNER, ubicacion=UBICACION, re_aplicar_filtro=aplicar_filtro):
                        continue
        
        if not exito:
            print(f"🔴 OMITIDO: '{UBICACION}' tras {max_intentos} intentos")
            return None
            
        # Verificación final de banner antes de extraer datos
        if hay_banner_error(driver):
            print(f"🚨 Banner detectado antes de extraer datos, esperando {TIEMPO_ESPERA_BANNER}s antes de refrescar...")
            if not esperar_y_refrescar_si_banner(driver, max_intentos=2, espera_seg=TIEMPO_ESPERA_BANNER, ubicacion=UBICACION, re_aplicar_filtro=aplicar_filtro):
                print(f"🔴 OMITIDO: '{UBICACION}' por errores persistentes")
                return None
        
        time.sleep(TIEMPO_ESPERA_CORTO)
        print(f"📊 Extrayendo datos para '{UBICACION}'...")
        
        # Verificar una vez más que no aparezca el banner durante la extracción
        if hay_banner_error(driver):
            print(f"🔴 OMITIDO: '{UBICACION}' - Banner aparece durante extracción")
            return None
        
        # Extraer datos de las tarjetas
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
            except Exception:
                continue

        # Extraer demanda de contratación
        try:
            span_demanda = driver.find_element(By.CSS_SELECTOR, "div.overview-layout__hdi--reading span.overview-layout__hdi--value")
            demanda_contratacion = span_demanda.text.strip()
        except Exception:
            demanda_contratacion = None

        datos = {
            "carpeta": carpeta_nombre,
            "proyecto": proyecto_nombre,
            "ubicacion": UBICACION,
            "profesionales": profesionales,
            "anuncios_empleo": anuncios_empleo,
            "demanda_contratacion": demanda_contratacion,
        }
        
        # Verificar que todos los datos esenciales fueron extraídos
        datos_extraidos = []
        datos_faltantes = []
        
        if profesionales is not None and profesionales != "--":
            datos_extraidos.append(f"profesionales: {profesionales}")
        else:
            datos_faltantes.append("profesionales")
            
        # Para anuncios_empleo, consideramos válido cualquier valor (incluido None, "", "--")
        # porque se normaliza automáticamente a "1" en utils.py
        if anuncios_empleo is not None and anuncios_empleo != "--":
            datos_extraidos.append(f"anuncios: {anuncios_empleo}")
        else:
            datos_extraidos.append(f"anuncios: 1 (normalizado)")  # Mostrar que se normalizará
            
        if demanda_contratacion is not None and demanda_contratacion != "--":
            datos_extraidos.append(f"demanda: {demanda_contratacion}")
        else:
            datos_faltantes.append("demanda_contratacion")
        
        # Resultado final de la extracción
        if datos_extraidos:
            print(f"✅ EXTRACCIÓN EXITOSA '{UBICACION}': {', '.join(datos_extraidos)}")
            if datos_faltantes:
                print(f"⚠️ Datos faltantes: {', '.join(datos_faltantes)}")
        else:
            print(f"❌ EXTRACCIÓN FALLIDA '{UBICACION}': No se obtuvieron datos válidos")
            
        time.sleep(TIEMPO_ESPERA_CORTO)
        return datos
        
    except Exception as e:
        print(f"❌ ERROR: {UBICACION} - {str(e)[:50]}...")
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
                resultados_ubicacion = []
                ubicaciones_exitosas = 0
                
                for UBICACION in ubicaciones:
                    print(f"\n🌍 Aplicando ubicación: {UBICACION}")
                    datos = extraer_datos_reporte(
                        driver, UBICACION, carpeta_nombre, texto
                    )
                    if datos:
                        resultados_ubicacion.append(datos)
                        ubicaciones_exitosas += 1
                
                # Solo agregar resultados si al menos una ubicación fue exitosa
                if resultados_ubicacion:
                    resultados_finales.extend(resultados_ubicacion)
                    if ubicaciones_exitosas < len(ubicaciones):
                        print(f"⚠️ Solo {ubicaciones_exitosas}/{len(ubicaciones)} ubicaciones procesadas exitosamente para '{texto}'")
                else:
                    print(f"❌ Ninguna ubicación pudo ser procesada para '{texto}'")
                
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

    # Obtener todas las rutas de Excel configuradas
    try:
        rutas_excel = obtener_rutas_excel()
        print(f"📂 Se procesarán {len(rutas_excel)} archivo(s) Excel:")
        for i, ruta in enumerate(rutas_excel, 1):
            print(f"   {i}. {ruta}")
    except ValueError as e:
        print(e)
        return

    # Lista de ubicaciones a filtrar
    UBICACIONES = ["Ecuador", "América Latina"]

    # CONFIGURACIÓN DEL NAVEGADOR
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

    # Procesar cada archivo Excel
    for i, ruta_excel in enumerate(rutas_excel, 1):
        print(f"\n{'='*60}")
        print(f"📊 Procesando archivo {i}/{len(rutas_excel)}: {os.path.basename(ruta_excel)}")
        print(f"{'='*60}")

        # Extraer reportes para este archivo específico
        reportes = extraer_datos_tabla("reporteLinkedin", ruta_excel)
        if not reportes:
            print(f"❌ No se encontraron reportes en el archivo {ruta_excel}")
            continue

        # Lista para almacenar los resultados finales de este archivo
        resultados_finales = []
        elementos_fallidos = []  # Nueva lista para rastrear elementos que fallaron

        # -----------------------------------------------------------------------------
        # PROCESAR CADA ELEMENTO DEL REPORTE (Carpeta + Proyecto) para este archivo
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
                # Agregar a elementos fallidos si no se encuentra la carpeta
                elementos_fallidos.append({
                    'elemento': elemento,
                    'carpeta': carpeta_buscar,
                    'proyecto': proyecto_buscar,
                    'razon': f"Carpeta '{carpeta_buscar}' no encontrada"
                })
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
                # Agregar a elementos fallidos si no se encuentra el proyecto
                elementos_fallidos.append({
                    'elemento': elemento,
                    'carpeta': carpeta_buscar,
                    'proyecto': proyecto_buscar,
                    'razon': f"Proyecto '{proyecto_buscar}' no encontrado en carpeta '{carpeta_buscar}'"
                })

            # Volver a la vista de carpetas para continuar con el siguiente elemento
            driver.get(url)
            time.sleep(TIEMPO_ESPERA_PAGINA)

        # -----------------------------------------------------------------------------
        # REINTENTO DE ELEMENTOS FALLIDOS (segunda oportunidad)
        # -----------------------------------------------------------------------------
        if elementos_fallidos:
            print(f"\n🔄 REINTENTANDO {len(elementos_fallidos)} elemento(s) que fallaron:")
            for i, fallido in enumerate(elementos_fallidos.copy(), 1):  # Usar copy() para evitar problemas de modificación durante iteración
                elemento = fallido['elemento']
                carpeta_buscar = fallido['carpeta']
                proyecto_buscar = fallido['proyecto']
                razon = fallido['razon']
                
                print(f"\n🔄 Reintento {i}/{len(elementos_fallidos)}: {carpeta_buscar} -> {proyecto_buscar}")
                print(f"   Razón del fallo anterior: {razon}")
                
                # Navegar a la página principal de carpetas
                driver.get(url)
                time.sleep(TIEMPO_ESPERA_MEDIO)
                
                # Intentar buscar la carpeta nuevamente
                try:
                    paginacion_carpetas = driver.find_elements(
                        By.CSS_SELECTOR,
                        ".saved-folders-layout .artdeco-pagination ul.artdeco-pagination__pages li",
                    )
                except:
                    paginacion_carpetas = []

                encontrada = buscar_carpeta_en_pagina(driver, carpeta_buscar)

                # Si no se encontró en la página inicial, recorrer paginación
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
                            print("⚠️ Error al cambiar página de carpetas en reintento:", e)
                            continue

                if not encontrada:
                    print(f"❌ Reintento fallido: Carpeta '{carpeta_buscar}' sigue sin encontrarse")
                    continue

                # Buscar el proyecto dentro de la carpeta
                try:
                    layout = driver.find_element(By.CLASS_NAME, "saved-reports-layout")
                    paginacion_reports = driver.find_elements(
                        By.CSS_SELECTOR,
                        "div.artdeco-models-table-pagination__pagination-cmpt ul.artdeco-pagination__pages li",
                    )
                except Exception as e:
                    print("❌ Error al localizar la sección de reportes en reintento:", e)
                    paginacion_reports = []

                proyecto_encontrado = buscar_proyecto_en_pagina(
                    driver, proyecto_buscar, UBICACIONES, carpeta_buscar, resultados_finales
                )

                # Si no se encontró en la página inicial, recorrer paginación de reportes
                if not proyecto_encontrado and paginacion_reports:
                    num_pag = len(paginacion_reports)
                    for j in range(num_pag):
                        paginacion_reports = driver.find_elements(
                            By.CSS_SELECTOR,
                            "div.artdeco-models-table-pagination__pagination-cmpt ul.artdeco-pagination__pages li",
                        )
                        li = paginacion_reports[j]
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
                            print("⚠️ Error al cambiar página de reportes en reintento:", e)
                            continue

                if proyecto_encontrado:
                    print(f"✅ Reintento exitoso: '{proyecto_buscar}' procesado correctamente")
                    # Remover de la lista de fallidos ya que fue exitoso
                    elementos_fallidos.remove(fallido)
                else:
                    print(f"❌ Reintento fallido: '{proyecto_buscar}' sigue sin encontrarse")

        # -----------------------------------------------------------------------------
        # Exportar resultados a Excel para este archivo
        # -----------------------------------------------------------------------------
        if resultados_finales:
            guardar_datos_excel(resultados_finales, plataforma="LinkedIn", ruta_excel=ruta_excel)
            print(f"✅ Datos guardados correctamente para {os.path.basename(ruta_excel)}")
        else:
            print(f"ℹ️ No se obtuvieron resultados para {os.path.basename(ruta_excel)}.")
        
        # Resumen final del archivo procesado
        total_elementos = len(reportes)
        elementos_exitosos = total_elementos - len(elementos_fallidos)
        if elementos_fallidos:
            print(f"\n📊 RESUMEN para {os.path.basename(ruta_excel)}:")
            print(f"   ✅ Exitosos: {elementos_exitosos}/{total_elementos}")
            print(f"   ❌ Fallidos: {len(elementos_fallidos)}/{total_elementos}")
            print(f"   📋 Elementos que no se pudieron procesar:")
            for fallido in elementos_fallidos:
                print(f"      - {fallido['carpeta']} -> {fallido['proyecto']} ({fallido['razon']})")
        else:
            print(f"\n🎉 Todos los elementos procesados exitosamente para {os.path.basename(ruta_excel)} ({elementos_exitosos}/{total_elementos})")

    # RESUMEN FINAL COMPLETO DE TODO EL PROCESAMIENTO
    print(f"\n{'='*80}")
    print(f"📋 RESUMEN FINAL DEL PROCESAMIENTO LINKEDIN")
    print(f"{'='*80}")
    
    archivos_exitosos = 0
    archivos_con_errores = 0
    total_proyectos_procesados = 0
    total_proyectos_fallidos = 0
    total_ubicaciones_exitosas = 0
    total_ubicaciones_fallidas = 0
    errores_detallados = []
    
    for i, ruta_excel in enumerate(rutas_excel, 1):
        print(f"\n📊 ARCHIVO {i}: {os.path.basename(ruta_excel)}")
        
        # Extraer reportes para obtener estadísticas
        try:
            reportes = extraer_datos_tabla("reporteLinkedin", ruta_excel)
            if not reportes:
                print(f"   ❌ Sin reportes configurados")
                archivos_con_errores += 1
                continue
                
            total_elementos = len(reportes)
            
            # Verificar si hay datos guardados
            try:
                import pandas as pd
                df = pd.read_excel(ruta_excel, sheet_name="LinkedIn")
                datos_procesados = len(df) if not df.empty else 0
                
                # Verificar que los datos se guardaron correctamente
                if datos_procesados > 0:
                    # Contar ubicaciones únicas procesadas (en la columna "Region")
                    ubicaciones_procesadas = df['Region'].nunique() if 'Region' in df.columns else 0
                    
                    # Calcular proyectos procesados basado en datos esperados
                    # Cada proyecto debería tener 2 ubicaciones (Ecuador y América Latina)
                    # Total de registros = proyectos * 2 ubicaciones
                    proyectos_estimados = datos_procesados // 2 if datos_procesados >= 2 else 1
                    
                    print(f"   ✅ Registros extraídos: {datos_procesados}")
                    print(f"   ✅ Ubicaciones únicas: {ubicaciones_procesadas}")
                    print(f"   ✅ Proyectos procesados: {proyectos_estimados}/{total_elementos}")
                    
                    # Si se procesaron todos los proyectos esperados
                    if datos_procesados >= total_elementos * 2:  # 2 ubicaciones por proyecto
                        archivos_exitosos += 1
                        total_proyectos_procesados += total_elementos
                        total_ubicaciones_exitosas += datos_procesados
                        print(f"   🎉 Todos los proyectos procesados exitosamente")
                    else:
                        archivos_con_errores += 1
                        proyectos_parciales = datos_procesados // 2
                        total_proyectos_procesados += proyectos_parciales
                        total_proyectos_fallidos += (total_elementos - proyectos_parciales)
                        total_ubicaciones_exitosas += datos_procesados
                        total_ubicaciones_fallidas += (total_elementos * 2 - datos_procesados)
                        print(f"   ⚠️ Procesamiento parcial: {proyectos_parciales}/{total_elementos} proyectos")
                else:
                    print(f"   ❌ Sin datos guardados")
                    archivos_con_errores += 1
                    total_proyectos_fallidos += total_elementos
                    total_ubicaciones_fallidas += total_elementos * 2
                    
            except Exception as e:
                print(f"   ❌ Error verificando datos guardados: {e}")
                archivos_con_errores += 1
                total_proyectos_fallidos += total_elementos
                total_ubicaciones_fallidas += total_elementos * 2
                
        except Exception as e:
            print(f"   ❌ Error procesando archivo: {e}")
            archivos_con_errores += 1
    
    # RESUMEN GLOBAL
    print(f"\n🎯 ESTADÍSTICAS GLOBALES:")
    print(f"   📁 Archivos procesados: {len(rutas_excel)}")
    print(f"   ✅ Archivos exitosos: {archivos_exitosos}")
    print(f"   ❌ Archivos con errores: {archivos_con_errores}")
    print(f"   📊 Total proyectos procesados: {total_proyectos_procesados}")
    print(f"   ❌ Total proyectos fallidos: {total_proyectos_fallidos}")
    print(f"   🌍 Total ubicaciones exitosas: {total_ubicaciones_exitosas}")
    print(f"   ❌ Total ubicaciones fallidas: {total_ubicaciones_fallidas}")
    
    # RESULTADO FINAL
    if archivos_con_errores == 0:
        print(f"\n🎉 ¡PROCESAMIENTO COMPLETAMENTE EXITOSO!")
        print(f"   ✅ Todos los archivos, proyectos y ubicaciones fueron procesados correctamente")
    else:
        print(f"\n⚠️ PROCESAMIENTO COMPLETADO CON ERRORES")
        print(f"   ❌ {archivos_con_errores} archivo(s) tuvieron problemas")
        if total_proyectos_fallidos > 0:
            print(f"   ❌ {total_proyectos_fallidos} proyecto(s) no pudieron ser procesados")
        if total_ubicaciones_fallidas > 0:
            print(f"   ❌ {total_ubicaciones_fallidas} ubicación(es) fallaron")

    print(f"\n🎉 Proceso LinkedIn finalizado. Se procesaron {len(rutas_excel)} archivo(s).")
    driver.quit()

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import os
import time

from scrapers.utils import extraer_datos_tabla, guardar_datos_excel, obtener_rutas_excel


def parse_k_notation(valor_str: str) -> float:
    """
    Convierte cadenas como '3,6K' => 3600, '1,3K' => 1300, '9.290' => 9290, etc.
    Retorna un float (puedes cambiarlo a int si prefieres).
    """
    original_str = valor_str  # Guardar el original para debugging
    
    try:
        valor_str = valor_str.strip().upper().replace(".", "").replace(",", ".")
        
        print(f"    🔍 parse_k_notation: '{original_str}' -> '{valor_str}'")
        
        if "K" in valor_str:
            # Ejemplo: '3.6K' => '3.6', multiplicamos *1000
            valor_str = valor_str.replace("K", "")
            print(f"    🔍 Después de quitar K: '{valor_str}'")
            try:
                resultado = float(valor_str) * 1000
                print(f"    ✅ Resultado K: {resultado}")
                return resultado
            except ValueError as e:
                print(f"    ❌ Error convirtiendo '{valor_str}' a float: {e}")
                return 0
        else:
            # Sin K, solo convertir directamente
            try:
                resultado = float(valor_str)
                print(f"    ✅ Resultado directo: {resultado}")
                return resultado
            except ValueError as e:
                print(f"    ❌ Error convirtiendo '{valor_str}' a float: {e}")
                return 0
    except Exception as e:
        print(f"    ❌ Error general en parse_k_notation con '{original_str}': {e}")
        return 0


def buscar_carrera_semrush(driver, carrera):
    """
    Función auxiliar para buscar una carrera específica en Semrush
    Retorna True si la búsqueda fue exitosa, False en caso contrario
    """
    try:
        print(f"🔍 Localizando campo de búsqueda...")
        time.sleep(4)  # Esperar a que la página cargue completamente
        # Localizar el div con contenteditable
        input_div = driver.find_element(
            By.CSS_SELECTOR, 'div[data-slate-editor="true"]'
        )
        input_div.click()
        time.sleep(1)
        
        print(f"✏️ Escribiendo carrera: '{carrera}'")
        # Limpiar el campo primero
        input_div.send_keys(Keys.CONTROL + 'a')
        time.sleep(0.5)
        input_div.send_keys(Keys.DELETE)
        time.sleep(0.5)

        # Escribir la carrera caracter por caracter
        for ch in carrera:
            input_div.send_keys(ch)
            time.sleep(0.05)  # pequeño delay para cada caracter

        time.sleep(1)
        print(f"📝 Texto escrito: '{input_div.text.strip()}'")

        # Buscar el botón "Buscar" con diferentes métodos
        print(f"🔍 Buscando botón de búsqueda...")
        boton_buscar = None
        
        # Método 1: Por texto del span
        try:
            boton_buscar = driver.find_element(By.XPATH, "//span[contains(text(), 'Buscar')]")
            print("✅ Botón encontrado por texto 'Buscar'")
        except:
            pass
        
        # Método 2: Por tipo de botón
        if not boton_buscar:
            try:
                boton_buscar = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
                print("✅ Botón encontrado por tipo submit")
            except:
                pass
        
        # Método 3: Por clase o atributo
        if not boton_buscar:
            try:
                boton_buscar = driver.find_element(By.CSS_SELECTOR, '[class*="search"] button, [class*="submit"] button')
                print("✅ Botón encontrado por clase")
            except:
                pass
        
        if boton_buscar:
            boton_buscar.click()
            print(f"📤 Búsqueda iniciada para: {carrera}")
        else:
            # Si no encontramos el botón, intentar con Enter
            print("⚠️ No se encontró botón, intentando con Enter...")
            input_div.send_keys(Keys.RETURN)
            
        # Esperar a que la página actualice
        time.sleep(5)
        
        # Verificar que la búsqueda se realizó
        current_url = driver.current_url
        if "keyword" in current_url.lower() or len(current_url) > 60:  # URL cambió
            print(f"✅ Búsqueda completada - URL: {current_url[:80]}...")
            return True
        else:
            print(f"⚠️ La URL no cambió mucho, puede que la búsqueda no se haya completado")
            return False
            
    except Exception as e:
        print("❌ No se pudo enviar la carrera o hacer clic en 'Buscar':", e)
        return False


def extraer_datos_semrush(driver, carrera):
    """
    Extrae los datos de Semrush de forma directa y fluida:
    - Visión General: span.kwo-widget-total[data-testid="volume-total"]
    - Si hay valor, navega a Magic Tool y extrae:
        - Palabras: div.sm-keywords-table-header__item-value[data-testid="all-keywords"]
        - Volumen: div.sm-keywords-table-header__item-value[data-testid="total-volume"]
    """
    time.sleep(6)  # Esperar carga inicial

    # 1. VISIÓN GENERAL
    vision_general = 0
    try:
        elem = driver.find_element(By.CSS_SELECTOR, 'span.kwo-widget-total[data-testid="volume-total"]')
        vision_general_str = elem.text.strip()
        if not vision_general_str or vision_general_str.lower() in ['n/d', 'n/a', '-', '--', '', 'sin datos', 'no data']:
            print("⚠️ Visión General no disponible o N/D, pero continuando con Magic Tool...")
            vision_general = 0
        else:
            vision_general = parse_k_notation(vision_general_str)
            print(f"✅ Visión General: {vision_general_str} -> {vision_general}")
    except Exception as e:
        print(f"⚠️ No se encontró Visión General ({str(e)[:50]}...), pero continuando con Magic Tool...")
        vision_general = 0

    # 2. NAVEGAR A MAGIC TOOL (SIEMPRE, independientemente de Visión General)
    print("🔗 Navegando a Magic Tool para verificar otros datos...")
    try:
        magic_tool_button = driver.find_element(
            By.CSS_SELECTOR, 'srf-sidebar-list-item[label="Keyword Magic Tool"]'
        )
        magic_tool_href = magic_tool_button.get_attribute("href")
        if magic_tool_href:
            driver.get(magic_tool_href)
            print("➡️ Navegando a Keyword Magic Tool...")
        else:
            print("⚠️ No se encontró href de Magic Tool")
            # No devolver aquí, intentar con la URL actual
    except Exception as e:
        print(f"❌ No se pudo encontrar/enlazar al 'Keyword Magic Tool': {e}")
        print("🔄 Intentando continuar en la página actual...")

    time.sleep(6)  # Esperar carga Magic Tool

    # 3. PALABRAS Y VOLUMEN TOTAL
    palabras = 0
    volumen = 0
    
    # Intentar extraer Palabras
    try:
        palabras_elem = driver.find_element(
            By.CSS_SELECTOR, 'div.sm-keywords-table-header__item-value[data-testid="all-keywords"]'
        )
        palabras_str = palabras_elem.text.strip()
        if palabras_str and any(char.isdigit() for char in palabras_str):
            palabras = parse_k_notation(palabras_str)
            print(f"✅ Palabras: {palabras_str} -> {palabras}")
        else:
            print(f"⚠️ Palabras encontradas pero valor no válido: '{palabras_str}'")
    except Exception as e:
        print(f"⚠️ No se pudo extraer Palabras: {str(e)[:50]}...")

    # Intentar extraer Volumen
    try:
        volumen_elem = driver.find_element(
            By.CSS_SELECTOR, 'div.sm-keywords-table-header__item-value[data-testid="total-volume"]'
        )
        volumen_str = volumen_elem.text.strip()
        if volumen_str and any(char.isdigit() for char in volumen_str):
            volumen = parse_k_notation(volumen_str)
            print(f"✅ Volumen: {volumen_str} -> {volumen}")
        else:
            print(f"⚠️ Volumen encontrado pero valor no válido: '{volumen_str}'")
    except Exception as e:
        print(f"⚠️ No se pudo extraer Volumen: {str(e)[:50]}...")

    # 4. VERIFICACIÓN FINAL Y LOGGING DETALLADO
    datos_encontrados = []
    if vision_general > 0:
        datos_encontrados.append(f"Visión General: {vision_general}")
    if palabras > 0:
        datos_encontrados.append(f"Palabras: {palabras}")
    if volumen > 0:
        datos_encontrados.append(f"Volumen: {volumen}")

    if datos_encontrados:
        print(f"✅ DATOS EXTRAÍDOS EXITOSAMENTE: {', '.join(datos_encontrados)}")
    else:
        print("⚠️ ADVERTENCIA: No se encontraron datos válidos en ninguna métrica")
        print("🔍 Intentando búsqueda de emergencia en la página actual...")
        
        # BÚSQUEDA DE EMERGENCIA - buscar cualquier número relevante en la página
        try:
            # Buscar elementos que podrían contener datos numéricos
            all_numeric_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'K') or contains(text(), '.') or contains(text(), ',')]")
            emergency_candidates = []
            
            for elem in all_numeric_elements[:15]:  # Limitar la búsqueda
                try:
                    text = elem.text.strip()
                    if (text and any(char.isdigit() for char in text) and 
                        len(text) < 20 and ('K' in text.upper() or '.' in text or ',' in text)):
                        emergency_candidates.append(text)
                except:
                    continue
            
            if emergency_candidates:
                print(f"🚨 Posibles datos encontrados en búsqueda de emergencia: {emergency_candidates[:5]}")
                print("💡 Sugerencia: Verificar manualmente si estos valores son relevantes")
            else:
                print("🚨 Búsqueda de emergencia no encontró candidatos numéricos")
                
        except Exception as emergency_e:
            print(f"🚨 Error en búsqueda de emergencia: {emergency_e}")

    print(f"\n📊 RESUMEN DE DATOS EXTRAÍDOS:")
    print(f"   🔢 Visión General: {vision_general}")
    print(f"   📝 Palabras: {palabras}")
    print(f"   📈 Volumen: {volumen}")

    return vision_general, palabras, volumen


def semrush_scraper():
    load_dotenv()
    EMAIL = os.getenv("SEMRUSH_USER")
    PASSWORD = os.getenv("SEMRUSH_PASS")

    # 1. OBTENER TODAS LAS RUTAS DE EXCEL CONFIGURADAS
    try:
        rutas_excel = obtener_rutas_excel()
        print(f"📂 Se procesarán {len(rutas_excel)} archivo(s) Excel:")
        for i, ruta in enumerate(rutas_excel, 1):
            print(f"   {i}. {os.path.basename(ruta)}")
    except ValueError as e:
        print(e)
        return

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

    # LANZAR EL DRIVER (UNA SOLA VEZ)
    driver = uc.Chrome(options=options)

    try:
        # 2. INICIAR SESIÓN EN SEMRUSH (UNA SOLA VEZ)
        driver.get("https://es.semrush.com/login/?src=header&redirect_to=%2F")
        time.sleep(1.5)

        if "login" not in driver.current_url:
            print("✅ Sesión ya iniciada (no hace falta login).")
        else:
            print("🔐 Iniciando sesión en Semrush...")
            try:
                input_email = driver.find_element(By.ID, "email")
                input_password = driver.find_element(By.ID, "password")

                input_email.clear()
                input_email.send_keys(EMAIL)
                input_password.clear()
                input_password.send_keys(PASSWORD)

                input_password.send_keys(Keys.RETURN)
                time.sleep(10)

                if "login" in driver.current_url:
                    print("⚠️ Parece que no se pudo iniciar sesión. Revisa tus credenciales.")
                    return
                else:
                    print("✅ Sesión iniciada correctamente.")
            except Exception as e:
                print("❌ Error al intentar loguearse:", e)
                return

        # 3. PROCESAR CADA ARCHIVO EXCEL
        for i, ruta_excel in enumerate(rutas_excel, 1):
            print(f"\n{'='*60}")
            print(f"📊 Procesando archivo {i}/{len(rutas_excel)}: {os.path.basename(ruta_excel)}")
            print(f"{'='*60}")

            # Extraer carrera para este archivo específico
            carrera = extraer_datos_tabla("carreraSemrush", ruta_excel)
            if not carrera:
                print(f"❌ No se encontró la carrera en la tabla 'carreraSemrush' del archivo {ruta_excel}")
                continue
            print(f"🔍 Carrera a buscar: {carrera}")

            # Procesar esta carrera específica
            try:
                # 4. IR A LA PÁGINA DE KEYWORD OVERVIEW
                driver.get("https://es.semrush.com/analytics/keywordoverview/?db=ec")
                time.sleep(2)

                # 5. BUSCAR LA CARRERA
                if not buscar_carrera_semrush(driver, carrera):
                    print(f"❌ No se pudo buscar la carrera '{carrera}' para {os.path.basename(ruta_excel)}")
                    continue

                # 6. EXTRAER DATOS
                vision_general, palabras, volumen = extraer_datos_semrush(driver, carrera)
                
                # 7. GUARDAR DATOS EN EL ARCHIVO EXCEL CORRESPONDIENTE
                datos_para_guardar = [
                    {
                        "vision_general": f"{vision_general}",
                        "palabras": f"{palabras}",
                        "volumen": f"{volumen}",
                    }
                ]

                try:
                    guardar_datos_excel(datos_para_guardar, plataforma="semrush", ruta_excel=ruta_excel)
                    print(f"✅ Datos guardados correctamente para {os.path.basename(ruta_excel)}")
                except Exception as e:
                    print(f"⚠️ Error guardando datos en Excel para {ruta_excel}: {e}")

            except Exception as e:
                print(f"❌ Error procesando {os.path.basename(ruta_excel)}: {e}")
                continue

    except Exception as main_e:
        print(f"❌ Error general en el scraper: {main_e}")
    
    finally:
        try:
            driver.quit()
            print(f"\n🎉 Proceso SEMrush finalizado. Se procesaron {len(rutas_excel)} archivo(s).")
        except:
            pass
        'div.sm-keywords-table-header__item-value[data-testid="all-keywords"]',
        'div[data-testid="all-keywords"]',
        '[data-testid="all-keywords"]'
    
    print("🔍 Buscando elemento de Palabras (all-keywords)...")
    selectores_palabras = [
        'div.sm-keywords-table-header__item-value[data-testid="all-keywords"]',
        'div[data-testid="all-keywords"]',
        '[data-testid="all-keywords"]'
    ]
    for i, selector in enumerate(selectores_palabras, 1):
        try:
            print(f"  Intentando selector {i}: {selector}")
            
            # Esperar un poco más antes de cada intento
            if i > 1:
                time.sleep(3)
                
            palabras_element = driver.find_element(By.CSS_SELECTOR, selector)
            palabras_str = palabras_element.text.strip()
            
            # Verificar que el texto contenga números
            if palabras_str and any(char.isdigit() for char in palabras_str):
                palabras = parse_k_notation(palabras_str)
                print(f"✅ Palabras encontradas con selector {i}: '{palabras_str}' = {palabras}")
                break
            else:
                print(f"  Selector {i} encontrado pero texto no válido: '{palabras_str}'")
        except Exception as e:
            print(f"  Selector {i} falló: {str(e)[:60]}...")
            continue
    
    if palabras == 0:
        print("⚠️ No se pudo extraer las Palabras del Magic Tool")

    # 4. EXTRAER "total-volume" (VOLUMEN) del Magic Tool
    volumen = 0
    selectores_volumen = [
        'div.sm-keywords-table-header__item-value[data-testid="total-volume"]',
        'div[data-testid="total-volume"]',
        '[data-testid="total-volume"]'
    ]
    
    print("🔍 Buscando elemento de Volumen (total-volume)...")
    for i, selector in enumerate(selectores_volumen, 1):
        try:
            print(f"  Intentando selector {i}: {selector}")
            
            # Esperar un poco más antes de cada intento
            if i > 1:
                time.sleep(3)
                
            volumen_element = driver.find_element(By.CSS_SELECTOR, selector)
            volumen_str = volumen_element.text.strip()
            
            # Verificar que el texto contenga números
            if volumen_str and any(char.isdigit() for char in volumen_str):
                volumen = parse_k_notation(volumen_str)
                print(f"✅ Volumen encontrado con selector {i}: '{volumen_str}' = {volumen}")
                break
            else:
                print(f"  Selector {i} encontrado pero texto no válido: '{volumen_str}'")
        except Exception as e:
            print(f"  Selector {i} falló: {str(e)[:60]}...")
            continue
    
    if volumen == 0:
        print("⚠️ No se pudo extraer el Volumen del Magic Tool")
    
    # 5. MOSTRAR RESUMEN DE DATOS EXTRAÍDOS
    print(f"\n📊 RESUMEN DE DATOS EXTRAÍDOS:")
    print(f"   🔢 Visión General: {vision_general}")
    print(f"   📝 Palabras: {palabras}")
    print(f"   📈 Volumen: {volumen}")

    return vision_general, palabras, volumen


def semrush_scraper():
    load_dotenv()
    EMAIL = os.getenv("SEMRUSH_USER")
    PASSWORD = os.getenv("SEMRUSH_PASS")

    # 1. OBTENER TODAS LAS RUTAS DE EXCEL CONFIGURADAS
    try:
        rutas_excel = obtener_rutas_excel()
        print(f"📂 Se procesarán {len(rutas_excel)} archivo(s) Excel:")
        for i, ruta in enumerate(rutas_excel, 1):
            print(f"   {i}. {os.path.basename(ruta)}")
    except ValueError as e:
        print(e)
        return

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

    # LANZAR EL DRIVER (UNA SOLA VEZ)
    driver = uc.Chrome(options=options)

    try:
        # 2. INICIAR SESIÓN EN SEMRUSH (UNA SOLA VEZ)
        driver.get("https://es.semrush.com/login/?src=header&redirect_to=%2F")
        time.sleep(1.5)

        if "login" not in driver.current_url:
            print("✅ Sesión ya iniciada (no hace falta login).")
        else:
            print("🔐 Iniciando sesión en Semrush...")
            try:
                input_email = driver.find_element(By.ID, "email")
                input_password = driver.find_element(By.ID, "password")

                input_email.clear()
                input_email.send_keys(EMAIL)
                input_password.clear()
                input_password.send_keys(PASSWORD)

                input_password.send_keys(Keys.RETURN)
                time.sleep(10)

                if "login" in driver.current_url:
                    print("⚠️ Parece que no se pudo iniciar sesión. Revisa tus credenciales.")
                    return
                else:
                    print("✅ Sesión iniciada correctamente.")
            except Exception as e:
                print("❌ Error al intentar loguearse:", e)
                return

        # 3. PROCESAR CADA ARCHIVO EXCEL
        for i, ruta_excel in enumerate(rutas_excel, 1):
            print(f"\n{'='*60}")
            print(f"📊 Procesando archivo {i}/{len(rutas_excel)}: {os.path.basename(ruta_excel)}")
            print(f"{'='*60}")

            # Extraer carrera para este archivo específico
            carrera = extraer_datos_tabla("carreraSemrush", ruta_excel)
            if not carrera:
                print(f"❌ No se encontró la carrera en la tabla 'carreraSemrush' del archivo {ruta_excel}")
                continue
            print(f"🔍 Carrera a buscar: {carrera}")

            # Procesar esta carrera específica
            try:
                # 4. IR A LA PÁGINA DE KEYWORD OVERVIEW
                driver.get("https://es.semrush.com/analytics/keywordoverview/?db=ec")
                time.sleep(2)

                # 5. BUSCAR LA CARRERA
                if not buscar_carrera_semrush(driver, carrera):
                    print(f"❌ No se pudo buscar la carrera '{carrera}' para {os.path.basename(ruta_excel)}")
                    continue

                # 6. EXTRAER DATOS
                vision_general, palabras, volumen = extraer_datos_semrush(driver, carrera)
                
                # 7. GUARDAR DATOS EN EL ARCHIVO EXCEL CORRESPONDIENTE
                datos_para_guardar = [
                    {
                        "vision_general": f"{vision_general}",
                        "palabras": f"{palabras}",
                        "volumen": f"{volumen}",
                    }
                ]

                try:
                    guardar_datos_excel(datos_para_guardar, plataforma="semrush", ruta_excel=ruta_excel)
                    print(f"✅ Datos guardados correctamente para {os.path.basename(ruta_excel)}")
                except Exception as e:
                    print(f"⚠️ Error guardando datos en Excel para {ruta_excel}: {e}")

            except Exception as e:
                print(f"❌ Error procesando {os.path.basename(ruta_excel)}: {e}")
                continue

    except Exception as main_e:
        print(f"❌ Error general en el scraper: {main_e}")
    
    finally:
        try:
            driver.quit()
            print(f"\n🎉 Proceso SEMrush finalizado. Se procesaron {len(rutas_excel)} archivo(s).")
        except:
            pass

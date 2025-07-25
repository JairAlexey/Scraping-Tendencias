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
    Función auxiliar para extraer los datos de Semrush
    Retorna una tupla (vision_general, palabras, volumen)
    """
    # 1. EXTRAER VISIÓN GENERAL (Keyword Overview)
    print("⏳ Esperando a que carguen los resultados...")
    time.sleep(8)  # Tiempo adicional para que cargue completamente

    vision_general = 0
    selectores_vision_general = [
        # Selector específico para el widget de "Volumen" (NO "Volumen global")
        'div.kwo-volume-widget-layout .kwo-na',  # Buscar kwo-na dentro del widget de volumen específico
        '.kwo-volume-widget-layout .kwo-na',     # Alternativo sin div
        'span.kwo-widget-total[data-testid="volume-total"]',  # Por si tiene datos reales
        'span[data-testid="volume-total"]',  # Selector alternativo
        'div.kwo-na',  # Selector genérico como respaldo
        '.kwo-na',     # Selector alternativo sin div
    ]
    
    print("🔍 Buscando elemento de Visión General...")
    
    # Primero hacer un diagnóstico de la página
    print("🔬 Diagnóstico de página:")
    try:
        current_url = driver.current_url
        print(f"   URL actual: {current_url[:100]}...")
        
        # Buscar específicamente los elementos que sabemos que contienen datos
        print("   🎯 Buscando elementos específicos...")
        
        # Buscar el widget de "Volumen" (el que queremos) vs "Volumen global" (el que NO queremos)
        try:
            # Widget de "Volumen" específico
            volume_widget = driver.find_elements(By.CSS_SELECTOR, '.kwo-volume-widget-layout')
            print(f"   📊 Widgets de volumen específico encontrados: {len(volume_widget)}")
            for i, widget in enumerate(volume_widget, 1):
                try:
                    # Buscar kwo-na dentro de este widget específico
                    kwo_na_elements = widget.find_elements(By.CSS_SELECTOR, '.kwo-na')
                    for j, elem in enumerate(kwo_na_elements, 1):
                        text = elem.text.strip()
                        print(f"      Widget {i}, elemento {j}: Texto: '{text}' | Tag: '{elem.tag_name}'")
                except:
                    continue
        except Exception as e:
            print(f"   ❌ Error buscando volume-widget-layout: {e}")
        
        # Buscar el widget de "Volumen global" (para comparación)
        try:
            global_volume_elements = driver.find_elements(By.CSS_SELECTOR, 'span[data-testid="global-volume-total"]')
            print(f"   📊 Elementos de volumen GLOBAL (NO queremos estos): {len(global_volume_elements)}")
            for i, elem in enumerate(global_volume_elements, 1):
                try:
                    text = elem.text.strip()
                    print(f"      Global {i}: Texto: '{text}' (ESTE NO ES EL QUE QUEREMOS)")
                except:
                    continue
        except Exception as e:
            print(f"   ❌ Error buscando global-volume-total: {e}")
        
        # Buscar span con data-testid="volume-total" (el específico, no el global)
        try:
            volume_elements = driver.find_elements(By.CSS_SELECTOR, 'span[data-testid="volume-total"]')
            print(f"   📊 Elementos con data-testid='volume-total': {len(volume_elements)}")
            for i, elem in enumerate(volume_elements, 1):
                try:
                    text = elem.text.strip()
                    class_name = elem.get_attribute("class") or ""
                    print(f"      {i}. Texto: '{text}' | Clase: '{class_name}'")
                except:
                    continue
        except Exception as e:
            print(f"   ❌ Error buscando volume-total: {e}")
        
        # Buscar elementos con clase kwo-widget-total (pero filtrar el global)
        try:
            kwo_elements = driver.find_elements(By.CSS_SELECTOR, '.kwo-widget-total')
            print(f"   📊 Elementos con clase 'kwo-widget-total': {len(kwo_elements)}")
            for i, elem in enumerate(kwo_elements, 1):
                try:
                    text = elem.text.strip()
                    testid = elem.get_attribute("data-testid") or ""
                    # Identificar si es el global (que no queremos)
                    es_global = testid == "global-volume-total"
                    marca = "🚫 GLOBAL (NO QUEREMOS)" if es_global else "✅ ESPECÍFICO"
                    print(f"      {i}. Texto: '{text}' | TestID: '{testid}' | {marca}")
                except:
                    continue
        except Exception as e:
            print(f"   ❌ Error buscando kwo-widget-total: {e}")
        
        # Buscar elementos con clase kwo-na
        try:
            kwo_na_elements = driver.find_elements(By.CSS_SELECTOR, '.kwo-na')
            print(f"   📊 Elementos con clase 'kwo-na': {len(kwo_na_elements)}")
            for i, elem in enumerate(kwo_na_elements, 1):
                try:
                    text = elem.text.strip()
                    tag_name = elem.tag_name
                    print(f"      {i}. Texto: '{text}' | Tag: '{tag_name}'")
                except:
                    continue
        except Exception as e:
            print(f"   ❌ Error buscando kwo-na: {e}")
        
        # Búsqueda amplia de todos los elementos que contienen "2,4K" o datos similares
        try:
            all_spans = driver.find_elements(By.CSS_SELECTOR, 'span')
            data_spans = []
            for span in all_spans:
                try:
                    text = span.text.strip()
                    if text and ('K' in text.upper() or any(char.isdigit() for char in text)) and len(text) < 20:
                        class_name = span.get_attribute("class") or ""
                        testid = span.get_attribute("data-testid") or ""
                        data_spans.append({
                            "text": text,
                            "class": class_name,
                            "testid": testid
                        })
                except:
                    continue
            
            if data_spans:
                print(f"   📊 Spans con datos numéricos encontrados: {len(data_spans)}")
                for i, span_data in enumerate(data_spans[:8], 1):  # Mostrar hasta 8
                    print(f"      {i}. Texto: '{span_data['text']}' | Clase: '{span_data['class']}' | TestID: '{span_data['testid']}'")
            else:
                print("   ❌ No se encontraron spans con datos numéricos")
        except Exception as e:
            print(f"   ❌ Error en búsqueda amplia de spans: {e}")
        
        # Buscar todos los elementos que podrían contener datos de volumen
        possible_elements = driver.find_elements(By.CSS_SELECTOR, 'div, span')
        volume_candidates = []
        
        for elem in possible_elements[:50]:  # Revisar los primeros 50 elementos
            try:
                text = elem.text.strip()
                class_name = elem.get_attribute("class") or ""
                testid = elem.get_attribute("data-testid") or ""
                
                # Buscar elementos que puedan contener datos de volumen
                if (text and any(char.isdigit() for char in text) and len(text) < 30 and
                    ("kwo" in class_name.lower() or "volume" in class_name.lower() or 
                     "volume" in testid.lower() or "kwo" in testid.lower())):
                    volume_candidates.append({
                        "text": text,
                        "class": class_name,
                        "testid": testid,
                        "tag": elem.tag_name
                    })
            except:
                continue
        
        if volume_candidates:
            print(f"   🔍 Candidatos encontrados: {len(volume_candidates)}")
            for i, candidate in enumerate(volume_candidates[:5], 1):
                print(f"      {i}. Texto: '{candidate['text']}' | Clase: '{candidate['class']}' | TestID: '{candidate['testid']}' | Tag: '{candidate['tag']}'")
        else:
            print("   ❌ No se encontraron candidatos con datos numéricos")
    except Exception as diag_e:
        print(f"   ❌ Error en diagnóstico: {diag_e}")
    
    # Ahora intentar con los selectores específicos
    for i, selector in enumerate(selectores_vision_general, 1):
        try:
            print(f"  Intentando selector {i}: {selector}")
            
            # Esperar un poco más antes de cada intento
            if i > 1:
                time.sleep(3)
            
            vision_general_element = driver.find_element(By.CSS_SELECTOR, selector)
            vision_general_str = vision_general_element.text.strip()
            
            print(f"  ✅ Elemento encontrado!")
            print(f"  Texto encontrado: '{vision_general_str}'")
            print(f"  Clase del elemento: '{vision_general_element.get_attribute('class')}'")
            print(f"  TestID del elemento: '{vision_general_element.get_attribute('data-testid') or 'Sin testid'}'")
            
            # Validar el contenido del texto
            if not vision_general_str:
                print(f"  ⚠️ Elemento encontrado pero sin texto")
                continue
            
            # Si encuentra "n/d" o similar, significa que no hay datos
            if vision_general_str.lower() in ['n/d', 'n/a', '-', '--', '', 'sin datos', 'no data']:
                vision_general = 0
                print(f"  ✅ Visión General: Sin datos disponibles ('{vision_general_str}') = 0")
                break
            
            # Si contiene números, procesarlo
            elif any(char.isdigit() for char in vision_general_str):
                vision_general = parse_k_notation(vision_general_str)
                print(f"  ✅ Visión General con datos: '{vision_general_str}' = {vision_general}")
                
                # Validación adicional: si el resultado es 0 pero había números, investigar
                if vision_general == 0:
                    print(f"  ⚠️ ADVERTENCIA: Texto tenía números pero parse_k_notation devolvió 0")
                    print(f"  🔍 Texto original: '{vision_general_str}'")
                    print(f"  🔍 Texto después de strip/upper: '{vision_general_str.strip().upper()}'")
                break
            else:
                print(f"  ⚠️ Elemento encontrado pero texto no reconocido como datos: '{vision_general_str}'")
                continue
                
        except Exception as e:
            print(f"  ❌ Selector {i} falló: {str(e)[:80]}...")
            continue
    
    if vision_general == 0:
        print("⚠️ RESULTADO FINAL: No se extrajo Visión General o no hay datos disponibles.")
        print("🔍 Intentando extracción manual de emergencia...")
        
        # Búsqueda de emergencia - buscar cualquier número en la página
        try:
            all_text_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'K') or contains(text(), '0') or contains(text(), '1') or contains(text(), '2') or contains(text(), '3') or contains(text(), '4') or contains(text(), '5') or contains(text(), '6') or contains(text(), '7') or contains(text(), '8') or contains(text(), '9')]")
            emergency_candidates = []
            
            for elem in all_text_elements[:20]:
                try:
                    text = elem.text.strip()
                    if (text and any(char.isdigit() for char in text) and 
                        len(text) < 20 and 'K' in text.upper()):
                        emergency_candidates.append(text)
                except:
                    continue
            
            if emergency_candidates:
                print(f"🚨 Candidatos de emergencia encontrados: {emergency_candidates[:5]}")
            else:
                print("🚨 No se encontraron candidatos de emergencia")
                
        except Exception as emergency_e:
            print(f"🚨 Error en búsqueda de emergencia: {emergency_e}")
    
    print(f"🔢 Visión General final para '{carrera}': {vision_general}")

    # 2. NAVEGACIÓN A KEYWORD MAGIC TOOL
    print("\n🔗 Navegando a Keyword Magic Tool...")
    try:
        # Esperamos a que aparezca el botón con label exacto
        magic_tool_button = driver.find_element(
            By.CSS_SELECTOR, 'srf-sidebar-list-item[label="Keyword Magic Tool"]'
        )
        # Obtenemos el link del atributo href
        magic_tool_href = magic_tool_button.get_attribute("href")

        if magic_tool_href:
            driver.get(magic_tool_href)
            print("➡️ Navegando a Keyword Magic Tool vía href...")
        else:
            raise Exception("No se encontró el atributo href.")
    except Exception as e:
        print(f"❌ No se pudo encontrar/enlazar al 'Keyword Magic Tool': {e}")
        print("⚠️ Continuando con datos parciales...")
        return vision_general, 0, 0

    # Esperar a que cargue Keyword Magic Tool
    print("⏳ Esperando a que cargue Keyword Magic Tool...")
    time.sleep(8)

    # 3. EXTRAER "all-keywords" (PALABRAS) del Magic Tool
    palabras = 0
    selectores_palabras = [
        'div.sm-keywords-table-header__item-value[data-testid="all-keywords"]',
        'div[data-testid="all-keywords"]',
        '[data-testid="all-keywords"]'
    ]
    
    print("🔍 Buscando elemento de Palabras (all-keywords)...")
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

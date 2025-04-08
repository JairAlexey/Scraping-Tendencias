import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time

from scrapers.utils import extraer_datos_tabla


def google_trends_scraper():
    """
    - Toma las palabras desde la tabla "palabrasTrends".
    - Para cada palabra:
      1) Va a https://trends.google.es/trends?geo=EC&hl=es
      2) Ingresa la palabra en el input con id="i4".
      3) Hace clic en "Explorar".
      4) Cambia el periodo a "Últimos 12 meses".
      5) Cambia la categoría a "Empleo y educación".
      6) Comprueba si hay mensaje de "No hay suficientes datos".
      7) Si no hay error, clica en "Export" para descargar CSV.
    """

    # 1) Obtenemos la lista de palabras desde Excel
    palabras = extraer_datos_tabla("palabrasTrends")
    if not palabras or not isinstance(palabras, list):
        print("❌ No se encontraron palabras en la tabla 'palabrasTrends'.")
        return

    # Definir la ruta de descarga en la raíz del proyecto (asumiendo que el script se ejecuta desde allí)
    project_root = os.getcwd()

    # 2) Configurar undetected Chrome con opciones personalizadas
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    prefs = {
        "download.default_directory": project_root,  # Guarda los archivos en la raíz del proyecto
        "download.prompt_for_download": False,
        "download.directory_upgrade": True
    }
    options.add_experimental_option("prefs", prefs)
    driver = uc.Chrome(options=options)

    # URL base de Google Trends para Ecuador en español
    url_base = "https://trends.google.es/trends?geo=EC&hl=es"

    # Por cada palabra en la lista, repetimos el flujo
    for palabra in palabras:
        palabra_str = str(palabra).strip()
        if not palabra_str:
            continue

        print(f"\n=== Procesando palabra: '{palabra_str}' ===")

        # Reiniciar la página base para cada búsqueda
        driver.get(url_base)
        time.sleep(3)

        try:
            # a) Localizar el input con id="i4"
            input_busqueda = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "i4"))
            )
            input_busqueda.clear()
            time.sleep(1)
            input_busqueda.send_keys(palabra_str)
            time.sleep(1)
            # b) Simular Enter (RETURN) para iniciar la búsqueda
            input_busqueda.send_keys(Keys.RETURN)
            print(f"🔎 Explorando (ENTER): {palabra_str}")
            time.sleep(6)
        except Exception as e:
            print(f"❌ Error al ingresar palabra '{palabra_str}' o pulsar 'Explorar': {e}")
            continue

        # c) Cambiar periodo => "Últimos 12 meses"
        try:
            wait = WebDriverWait(driver, 10)
            time_picker = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "custom-date-picker"))
            )
            time_picker.click()
            time.sleep(2)
            opcion_12_meses = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//md-option//div[contains(text(),'Últimos 12 meses')]"))
            )
            opcion_12_meses.click()
            time.sleep(2)
            print("📅 Periodo seleccionado: Últimos 12 meses.")
        except Exception as e:
            print(f"⚠️ No se pudo cambiar el periodo a 'Últimos 12 meses': {e}")
            continue

        # d) Cambiar categoría => "Empleo y educación"
        try:
            # 1) Seleccionar el segundo hierarchy-picker (corresponde a categoría)
            category_picker_div = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "(//hierarchy-picker)[2]//div[contains(@class, 'hierarchy-select')]"))
            )
            category_picker_div.click()
            time.sleep(2)
            # 2) Ubicar el input dentro del autocompletar del picker de categoría
            cat_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "(//hierarchy-picker)[2]//div[contains(@class, 'hierarchy-autocomplete')]//input"))
            )
            cat_input.clear()
            cat_input.send_keys("Empleo y educación")
            time.sleep(2)
            # 3) Usar la flecha abajo para resaltar la opción y pulsar ENTER
            cat_input.send_keys(Keys.ARROW_DOWN)
            time.sleep(1)
            cat_input.send_keys(Keys.RETURN)
            time.sleep(2)
            print("📂 Categoría: Empleo y educación seleccionada.")
        except Exception as e:
            print(f"⚠️ No se pudo cambiar la categoría a 'Empleo y educación': {e}")
            continue

        # Esperar unos segundos para que se refresquen los datos
        time.sleep(4)

        # e) Verificar si hay mensaje de error en el widget (falta de datos)
        try:
            widget_template = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.widget-template"))
            )
            error_elements = widget_template.find_elements(By.CSS_SELECTOR, "div.widget-error")
            if error_elements and error_elements[0].is_displayed():
                print(f"🔴 Error: Tu búsqueda no tiene suficientes datos para '{palabra_str}'. Se omite.")
                continue
        except Exception as e:
            print(f"⚠️ No se pudo verificar el estado del widget para '{palabra_str}': {e}")

        # f) Si no hay error, hacer clic en botón "Export"
        try:
            export_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.widget-actions-item.export"))
            )
            export_btn.click()
            time.sleep(2)
            print(f"📥 Export CSV para '{palabra_str}' => revisa tus descargas.")
        except Exception as e:
            print(f"⚠️ No se encontró o no se pudo clicar en 'Export': {e}")

        time.sleep(3)

    # Encapsular driver.quit() para evitar el error "Controlador no válido"
    try:
        driver.quit()
    except Exception as e:
        print("Error al cerrar el driver:", e)
    print("\n✅ Proceso de Google Trends finalizado.")

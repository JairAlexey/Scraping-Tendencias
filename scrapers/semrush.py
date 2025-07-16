import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from dotenv import load_dotenv
import os
import time

from scrapers.utils import extraer_datos_tabla, guardar_datos_excel


def parse_k_notation(valor_str: str) -> float:
    valor_str = valor_str.strip().upper().replace(".", "").replace(",", ".")
    if "K" in valor_str:
        valor_str = valor_str.replace("K", "")
        try:
            return float(valor_str) * 1000
        except:
            return 0
    else:
        try:
            return float(valor_str)
        except:
            return 0


# Semrush Scraper
def semrush_scraper():
    load_dotenv()
    EMAIL = os.getenv("SEMRUSH_USER")
    PASSWORD = os.getenv("SEMRUSH_PASS")

    carrera = extraer_datos_tabla("carreraSemrush")
    if not carrera:
        print("❌ No se encontró la carrera en la tabla 'carreraSemrush'")
        return
    print(f"🔍 Carrera a buscar: {carrera}")

    user_data_dir = r"C:\Users\User\Documents\TRABAJO - UDLA\Scraping-Tendencias\profile"
    profile_directory = "Default"
    full_profile_path = os.path.join(user_data_dir, profile_directory)
    singleton_lock = os.path.join(full_profile_path, "SingletonLock")
    if os.path.exists(singleton_lock):
        print("🧯 Eliminando archivo de bloqueo previo (SingletonLock)...")
        os.remove(singleton_lock)

    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument(f"--profile-directory={profile_directory}")
    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

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
                driver.quit()
                return
            else:
                print("✅ Sesión iniciada correctamente.")
        except Exception as e:
            print("❌ Error al intentar loguearse:", e)
            driver.quit()
            return

    driver.get("https://es.semrush.com/analytics/keywordoverview/?db=ec")
    time.sleep(1)

    try:
        input_div = driver.find_element(By.CSS_SELECTOR, 'div[data-slate-editor="true"]')
        input_div.click()
        time.sleep(1)
        for ch in carrera:
            input_div.send_keys(ch)
            time.sleep(0.05)
        boton_buscar = driver.find_element(By.XPATH, "//span[contains(text(), 'Buscar')]")
        boton_buscar.click()
        print(f"📤 Buscando información de: {carrera}")
    except Exception as e:
        print("❌ No se pudo enviar la carrera o hacer clic en 'Buscar':", e)
        driver.quit()
        return

    time.sleep(5)

    # --- Extracción de datos con manejo de errores ---

    try:
        vision_general_span = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'span[data-testid="volume-total"]'))
        )
        vision_general_str = vision_general_span.text.strip()
        vision_general = parse_k_notation(vision_general_str)
        print(f"🔢 Volumen para '{carrera}': {vision_general}")
    except Exception as e:
        print("⚠️ No se pudo extraer el volumen general:", e)
        vision_general = 0

    try:
        magic_tool_button = driver.find_element(
            By.CSS_SELECTOR, 'srf-sidebar-list-item[label="Keyword Magic Tool"]'
        )
        magic_tool_href = magic_tool_button.get_attribute("href")
        if magic_tool_href:
            driver.get(magic_tool_href)
            print("➡️ Navegando a Keyword Magic Tool vía href...")
        else:
            raise Exception("No se encontró el atributo href.")
    except Exception as e:
        print("❌ No se pudo encontrar/enlazar al 'Keyword Magic Tool':", e)
        driver.quit()
        return

    time.sleep(5)

    try:
        palabras_div = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="all-keywords"]'))
        )
        palabras_str = palabras_div.text.strip()
        palabras = parse_k_notation(palabras_str)
        print(f"📊 Total de palabras (Keyword Magic Tool): {palabras}")
    except Exception as e:
        print("⚠️ No se pudo extraer 'all-keywords':", e)
        palabras = 0

    try:
        volumen_div = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="total-volume"]'))
        )
        volumen_str = volumen_div.text.strip()
        volumen = parse_k_notation(volumen_str)
        print(f"📊 Volumen total (Keyword Magic Tool): {volumen}")
    except Exception as e:
        print("⚠️ No se pudo extraer 'total-volume':", e)
        volumen = 0

    datos_para_guardar = [
        {
            "vision_general": f"{vision_general}",
            "palabras": f"{palabras}",
            "volumen": f"{volumen}",
        }
    ]

    try:
        guardar_datos_excel(datos_para_guardar, plataforma="semrush")
    except Exception as e:
        print("⚠️ Error guardando datos en Excel:", e)

    driver.quit()
    print("✅ Proceso SEMrush finalizado.")

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import os
import time

from scrapers.utils import extraer_datos_tabla, guardar_datos_excel


def parse_k_notation(valor_str: str) -> float:
    """
    Convierte cadenas como '3,6K' => 3600, '1,3K' => 1300, '9.290' => 9290, etc.
    Retorna un float (puedes cambiarlo a int si prefieres).
    """
    valor_str = valor_str.strip().upper().replace(".", "").replace(",", ".")

    if "K" in valor_str:
        # Ejemplo: '3.6K' => '3.6', multiplicamos *1000
        valor_str = valor_str.replace("K", "")
        try:
            return float(valor_str) * 1000
        except:
            return 0
    else:
        # Sin K, solo convertir directamente
        try:
            return float(valor_str)
        except:
            return 0


def semrush_scraper():
    load_dotenv()
    EMAIL = os.getenv("SEMRUSH_USER")
    PASSWORD = os.getenv("SEMRUSH_PASS")

    # 1. OBTENER "CARRERA" DESDE EXCEL
    carrera = extraer_datos_tabla("carreraSemrush")
    if not carrera:
        print("❌ No se encontró la carrera en la tabla 'carreraSemrush'")
        return
    print(f"🔍 Carrera a buscar: {carrera}")

    # 2. CONFIGURACIÓN DEL NAVEGADOR
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument(
        r"--user-data-dir=C:\Users\andrei.flores\AppData\Local\Google\Chrome\User Data"
    )
    options.add_argument("--profile-directory=Default")
    driver = uc.Chrome(options=options)

    # 3. IR A LA PÁGINA DE LOGIN
    driver.get("https://es.semrush.com/login/?src=header&redirect_to=%2F")
    time.sleep(1.5)

    # 4. VERIFICAR SI YA HAY SESIÓN
    if "login" not in driver.current_url:
        print("✅ Sesión ya iniciada (no hace falta login).")
    else:
        # Se asume que se requiere login con email y password
        print("🔐 Iniciando sesión en Semrush...")
        try:
            input_email = driver.find_element(By.ID, "email")
            input_password = driver.find_element(By.ID, "password")

            input_email.clear()
            input_email.send_keys(EMAIL)
            input_password.clear()
            input_password.send_keys(PASSWORD)

            # Hacer Enter o buscar un botón de login, si existe:
            input_password.send_keys(Keys.RETURN)
            time.sleep(3)

            # Verificar si salimos de la pantalla de login
            if "login" in driver.current_url:
                print(
                    "⚠️ Parece que no se pudo iniciar sesión. Revisa tus credenciales."
                )
                driver.quit()
                return
            else:
                print("✅ Sesión iniciada correctamente.")
        except Exception as e:
            print("❌ Error al intentar loguearse:", e)
            driver.quit()
            return

    # 5. IR A LA PÁGINA DE KEYWORD OVERVIEW (DB=ec => Ecuador)
    driver.get("https://es.semrush.com/analytics/keywordoverview/?db=ec")
    time.sleep(1)

    # 6. ENVIAR LA CARRERA AL INPUT DE KEYWORD Y HACER CLIC EN "Buscar"
    try:
        # Localizar el div con contenteditable
        input_div = driver.find_element(
            By.CSS_SELECTOR, 'div[data-slate-editor="true"]'
        )
        input_div.click()
        time.sleep(1)
        # Borramos contenido (opcional, si lo hay)
        # Podemos simular selec all + backspace
        # input_div.send_keys(Keys.CONTROL + 'a', Keys.BACK_SPACE)

        for ch in carrera:
            input_div.send_keys(ch)
            time.sleep(0.05)  # pequeño delay para cada caracter

        # Clic en el botón "Buscar" (usamos XPATH con su texto)
        boton_buscar = driver.find_element(
            By.XPATH, "//span[contains(text(), 'Buscar')]"
        )
        boton_buscar.click()
        print(f"📤 Buscando información de: {carrera}")
    except Exception as e:
        print("❌ No se pudo enviar la carrera o hacer clic en 'Buscar':", e)
        driver.quit()
        return

    # 7. ESPERAR A QUE APAREZCA EL VOLUMEN => <span data-testid="volume-total">
    time.sleep(5)  # Ajusta si la carga es más lenta

    # 8. EXTRAER VOLUMEN (kwo-widget-total => data-testid="volume-total")
    try:
        vision_general_span = driver.find_element(
            By.CSS_SELECTOR, 'span[data-testid="volume-total"]'
        )
        vision_general_str = vision_general_span.text.strip()
        vision_general = parse_k_notation(vision_general_str)
        print(f"🔢 Volumen para '{carrera}': {vision_general}")
    except Exception as e:
        print("⚠️ No se pudo extraer el volumen general:", e)
        vision_general = 0

    # 9. HACER CLIC EN "Keyword Magic Tool"
    try:
        # localizamos el link que contiene: "analytics.keywordmagic" (por ejemplo)
        # o XPATH con "Keyword Magic Tool"
        magic_link = driver.find_element(
            By.XPATH, '//span[contains(text(), "Keyword Magic Tool")]/..'
        )
        # Ese /.. sube al <a> contenedor
        magic_link.click()
        print("➡️ Navegando a Keyword Magic Tool...")
    except Exception as e:
        print("❌ No se pudo encontrar/enlazar al 'Keyword Magic Tool':", e)
        driver.quit()
        return

    time.sleep(5)

    # 10. EXTRAER "all-keywords" => 1,3K => parse => # de "palabras"
    try:
        palabras_div = driver.find_element(
            By.CSS_SELECTOR, 'div[data-testid="all-keywords"]'
        )
        palabras_str = palabras_div.text.strip()
        palabras = parse_k_notation(palabras_str)
        print(f"📊 Total de palabras (Keyword Magic Tool): {palabras}")
    except Exception as e:
        print("⚠️ No se pudo extraer 'all-keywords':", e)
        palabras = 0

    # 11. EXTRAER "total-volume" => 9.290 => parse => # => volumen
    try:
        volumen_div = driver.find_element(
            By.CSS_SELECTOR, 'div[data-testid="total-volume"]'
        )
        volumen_str = volumen_div.text.strip()
        volumen = parse_k_notation(volumen_str)
        print(f"📊 Volumen total (Keyword Magic Tool): {volumen}")
    except Exception as e:
        print("⚠️ No se pudo extraer 'total-volume':", e)
        volumen = 0

    # 12. GUARDAR LOS DATOS O MANEJARLOS
    # Supongamos que quieres guardarlo en la tabla "LinkedIn" con la estructura actual,
    # o que tienes otra tabla "datoSemrush". Ajusta según tu necesidad.

    # Ejemplo de "datos" con tu actual formato "LinkedIn"
    # (Solo a modo de ejemplo; seguramente querrás otra tabla/hoja para SEMrush)

    datos_para_guardar = [
        {
            "vision_general": f"{vision_general}",
            "palabras": f"{palabras}",
            "volumen": f"{volumen}",
        }
    ]

    # Llamamos a la función (asegúrate de que distinga "semrush" para guardarlo en la tabla que quieras)
    try:
        guardar_datos_excel(datos_para_guardar, plataforma="semrush")
    except Exception as e:
        print("⚠️ Error guardando datos en Excel:", e)

    driver.quit()
    print("✅ Proceso SEMrush finalizado.")

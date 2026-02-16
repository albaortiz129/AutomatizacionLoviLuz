import uvicorn
import os
import asyncio
from fastapi import FastAPI, Request
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Importamos la lógica del Socio B (Asegúrate de que el archivo se llame cerebro.py)
try:
    from cerebro import analizar_contrato_con_mistral
except ImportError:
    print("❌ Error: No se encuentra cerebro.py o la función analizar_contrato_con_mistral")

# Cargamos las variables del archivo .env (WOLF_USER, WOLF_PASS, MISTRAL_API_KEY)
load_dotenv()

app = FastAPI()

@app.post("/webhook-local")
async def recibir_contrato(request: Request):
    try:
        # 1. Recibir datos del contrato (desde WolfCRM o simulación)
        datos_raw = await request.json()
        print("📩 Datos recibidos. Procesando con Mistral AI...")

        # 2. El Socio B procesa el texto y devuelve el JSON mapeado
        datos_ia = analizar_contrato_con_mistral(datos_raw)
        print(f"🧠 IA ha generado el mapeo: {datos_ia}")

        # 3. Lanzar el robot Playwright
        await ejecutar_robot_local(datos_ia)
        
        return {"status": "success", "message": "Robot ejecutado correctamente"}
    except Exception as e:
        print(f" Error en el servidor: {e}")
        return {"status": "error", "message": str(e)}

async def ejecutar_robot_local(datos):
    async with async_playwright() as p:
        # Lanzamos navegador visible (headless=False) para supervisar
        # slow_mo añade una pequeña pausa entre acciones para que sea humano y no falle
        browser = await p.chromium.launch(headless=False, slow_mo=600)
        context = await browser.new_context()
        page = await context.new_page()
        
        print(f"Accediendo a WolfCRM...")
        
        # --- PASO 1: LOGIN ---
        await page.goto("https://loviluz.v3.wolfcrm.es/index.php")
        
        # Intentamos los selectores estándar de WolfCRM para Login
        try:
            await page.wait_for_selector('input[name="user_name"]', timeout=5000)
            await page.fill('input[name="user_name"]', os.getenv("WOLF_USER")) 
            await page.fill('input[name="user_password"]', os.getenv("WOLF_PASS")) 
            await page.click('#submitButton') # O el selector del botón de entrar
        except:
            print("⚠️ Selector de login estándar no encontrado. Intentando alternativos...")
            await page.fill("#usuario", os.getenv("WOLF_USER"))
            await page.fill("#password", os.getenv("WOLF_PASS"))
            await page.click("text=Entrar")

        await page.wait_for_load_state("networkidle")
        print("🔓 Login completado.")

        # --- PASO 2: NAVEGACIÓN AL FORMULARIO ---
        # Usamos la ruta que me pasaste
        url_formulario = "https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/#wolfWindowInFramePopupContainer"
        await page.goto(url_formulario)
        
        # Esperamos a que el contenedor del formulario sea visible
        await page.wait_for_selector("#wolfWindowInFramePopupContainer", timeout=10000)
        print("📝 Formulario de contrato detectado.")

        # --- PASO 3: RELLENADO DE CAMPOS ---
        
        # A. Campos de Texto
        campos_texto = {
            "#Customer__NAME": "Customer__NAME",
            "#EnergyContract__NAME": "EnergyContract__NAME",
            "#EnergyContract__CUPS_CITY": "EnergyContract__CUPS_CITY",
            "#EnergyContract__CUPS_COUNTY": "EnergyContract__CUPS_COUNTY",
            "#EnergyContract__DESCRIPTION": "EnergyContract__DESCRIPTION"
        }
        
        for selector, llave in campos_texto.items():
            if llave in datos and datos[llave]:
                try:
                    await page.fill(selector, str(datos[llave]))
                except:
                    print(f"⚠️ No se pudo rellenar el campo: {selector}")

        # B. Desplegables (Selects por etiqueta/label)
        desplegables = {
            "#EnergyContract__TIPO_ALTA": "EnergyContract__TIPO_ALTA",
            "#EnergyContract__STATUS": "EnergyContract__STATUS",
            "#EnergyContract__CF_1724317367388": "EnergyContract__CF_1724317367388",
            "#EnergyContract__CF_1724317580239": "EnergyContract__CF_1724317580239",
            "#EnergyContract__SUMINISTRO": "EnergyContract__SUMINISTRO"
        }

        for selector, llave in desplegables.items():
            if llave in datos and datos[llave]:
                try:
                    # select_option con label elige el texto que ve el humano ("Nueva", "Sí", etc.)
                    await page.select_option(selector, label=str(datos[llave]))
                except Exception as e:
                    print(f" Error al seleccionar {llave}: {e}")

        # C. Campo Fijo (Comercial)
        try:
            await page.select_option("#EnergyContract__USER_ID", value="00411")
        except:
            pass

        print("✅ Robot: Tarea de rellenado finalizada.")
        
        # Mantenemos el navegador abierto 2 minutos para que revises antes de cerrar
        print("👀 Esperando 120 segundos para revisión manual...")
        await asyncio.sleep(120) 
        await browser.close()

if __name__ == "__main__":
    # Ejecutamos el servidor en el puerto 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
import uvicorn
import os
import asyncio
from fastapi import FastAPI, Request
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from cerebro import analizar_contrato_con_mistral 

load_dotenv()

app = FastAPI()

@app.post("/webhook-local")
async def recibir_contrato(request: Request):
    try:
        datos_raw = await request.json()
        print("¡Datos recibidos! Procesando con Mistral...")

        datos_ia = analizar_contrato_con_mistral(datos_raw)
        print(f"Mistral ha generado el mapeo: {datos_ia}")

        await ejecutar_robot_local(datos_ia)
        
        return {"status": "success", "message": "Robot ejecutado"}
    except Exception as e:
        print(f"❌ Error en el servidor: {e}")
        return {"status": "error", "message": str(e)}

async def ejecutar_robot_local(datos):
    async with async_playwright() as p:
        # Abrimos navegador visible
        browser = await p.chromium.launch(headless=False, slow_mo=600)
        page = await browser.new_page()
        
        print(f"🤖 Accediendo a WolfCRM en: https://loviluz.v3.wolfcrm.es/index.php")
        
        # 1. Login
        await page.goto("https://loviluz.v3.wolfcrm.es/index.php")
        
        # Esperamos a que los campos de login sean visibles
        # NOTA: Si estos IDs fallan, inspecciona el campo en Chrome y dime el 'id' o 'name'
        try:
            await page.wait_for_selector('input[name="user_name"]') # Selector común en WolfCRM
            await page.fill('input[name="user_name"]', os.getenv("WOLF_USER")) 
            await page.fill('input[name="user_password"]', os.getenv("WOLF_PASS")) 
            await page.click('#submitButton') # O el ID del botón de entrar
        except:
            # Plan B: Intento por IDs genéricos si el name falla
            await page.fill("#usuario", os.getenv("WOLF_USER"))
            await page.fill("#password", os.getenv("WOLF_PASS"))
            await page.click("text=Entrar")

        await page.wait_for_load_state("networkidle")
        print("🔓 Login completado.")
        
        # 2. Ir al formulario de contrato nuevo
        await page.goto("https://loviluz.v3.wolfcrm.es/index.php?module=EnergyContract&action=EditView") 
        await page.wait_for_load_state("domcontentloaded")

        # 3. Rellenado de campos (Mapeo Socio B)
        
        # Campos de texto
        campos_texto = {
            "#Customer__NAME": "Customer__NAME",
            "#EnergyContract__NAME": "EnergyContract__NAME",
            "#EnergyContract__CUPS_CITY": "EnergyContract__CUPS_CITY",
            "#EnergyContract__CUPS_COUNTY": "EnergyContract__CUPS_COUNTY",
            "#EnergyContract__DESCRIPTION": "EnergyContract__DESCRIPTION"
        }
        
        for selector, llave in campos_texto.items():
            if llave in datos and datos[llave]:
                await page.fill(selector, str(datos[llave]))

        # Desplegables
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
                    await page.select_option(selector, label=str(datos[llave]))
                except Exception as e:
                    print(f"⚠️ No se pudo seleccionar {llave}: {e}")

        # Campo fijo Comercial
        try:
            await page.select_option("#EnergyContract__USER_ID", value="00411")
        except:
            pass

        print("✅ Robot: Tarea finalizada. Revisa el resultado.")
        await asyncio.sleep(60) 

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
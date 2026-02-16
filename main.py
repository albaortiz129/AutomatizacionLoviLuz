import os
import json
import traceback
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from cerebro import analizar_consulta_loviluz

load_dotenv()
app = FastAPI()

def ejecutar_robot_sincrono(datos):
    print("🤖 Robot: Iniciando proceso...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=600)
            page = browser.new_page()
            
            # 1. LOGIN
            page.goto("https://loviluz.v3.wolfcrm.es/index.php", timeout=60000)
            page.fill("#userLogin", os.getenv("WOLF_USER") or "")
            page.fill("#userPassword", os.getenv("WOLF_PASS") or "")
            page.click('input[type="submit"].btn-primary')
            page.wait_for_load_state("networkidle")
            print("🔓 Login exitoso.")

            # 2. IR A CONTRATOS Y PULSAR NUEVO
            page.goto("https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/")
            page.wait_for_selector("span.btn-creation:has-text('Nuevo')", timeout=10000).click()
            print("✨ Pulsado 'Nuevo'. Esperando formulario...")
            page.wait_for_timeout(4000)

            # 3. DETECTAR EL MARCO (IFRAME)
            target = page
            cups_id = "#EnergyContract__NAME"
            for frame in page.frames:
                if frame.query_selector(cups_id):
                    target = frame
                    print(f"📦 Formulario detectado en marco: {frame.url}")
                    break

            # 4. MAPEO COMPLETO DE CAMPOS (Tu lista actualizada)
            mapeo_total = {
                "#Customer__NAME": "Customer__NAME",
                "#EnergyContract__NAME": "EnergyContract__NAME",
                "#EnergyContract__FIRMANTE_DNI": "EnergyContract__FIRMANTE_DNI",
                "#EnergyContract__CUPS_ADDRESS": "EnergyContract__CUPS_ADDRESS",
                "#EnergyContract__CUPS_POSTAL_CODE": "EnergyContract__CUPS_POSTAL_CODE",
                "#EnergyContract__CUPS_CITY": "EnergyContract__CUPS_CITY",
                "#EnergyContract__CUPS_COUNTY": "EnergyContract__CUPS_COUNTY",
                "#EnergyContract__TIPO_ALTA": "EnergyContract__TIPO_ALTA",
                "#EnergyContract__STATUS": "EnergyContract__STATUS",
                "#EnergyContract__SUMINISTRO": "EnergyContract__SUMINISTRO",
                "#EnergyContract__USER_ID": "EnergyContract__USER_ID"
            }

            for selector, clave in mapeo_total.items():
                valor = datos.get(clave)
                if valor and valor != "PENDIENTE":
                    try:
                        elemento = target.wait_for_selector(selector, timeout=3000)
                        tag = elemento.evaluate("el => el.tagName")
                        if tag == "SELECT":
                            target.select_option(selector, value=str(valor))
                        else:
                            target.fill(selector, str(valor))
                        print(f"✅ Rellenado: {clave}")
                    except:
                        print(f"⚠️ No se encontró el ID: {selector}")

            print("✅ Robot: Volcado finalizado.")
            page.wait_for_timeout(60000) 
            browser.close()
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        traceback.print_exc()

@app.post("/webhook-local")
async def recibir_contrato(request: Request, background_tasks: BackgroundTasks):
    try:
        datos_raw = await request.json()
        texto = datos_raw.get("mensaje", str(datos_raw))
        print("📩 Webhook recibido.")
        
        datos_ia = json.loads(analizar_consulta_loviluz(texto))
        print(f"🧠 Datos extraídos: {datos_ia}")
        
        background_tasks.add_task(ejecutar_robot_sincrono, datos_ia)
        return {"status": "success", "extraido": datos_ia}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
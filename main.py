import os
import json
import traceback
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# Importar cerebro
try:
    from cerebro import analizar_consulta_loviluz
except ImportError:
    print("❌ ERROR: No se encuentra cerebro.py")

load_dotenv()
app = FastAPI()

def ejecutar_robot_sincrono(datos):
    """Esta función ahora se ejecuta como una tarea de fondo pura"""
    print("🤖 Robot: Iniciando proceso...")
    try:
        with sync_playwright() as p:
            # Usamos chromium
            browser = p.chromium.launch(headless=False, slow_mo=1000)
            page = browser.new_page()
            
            print(f"🌐 Robot: Entrando a WolfCRM...")
            page.goto("https://loviluz.v3.wolfcrm.es/index.php", timeout=60000)
            
            # --- LOGIN ---
            print("🔐 Robot: Intentando login...")
            try:
                page.wait_for_selector('input[name="user_name"]', timeout=10000)
                page.fill('input[name="user_name"]', os.getenv("WOLF_USER") or "") 
                page.fill('input[name="user_password"]', os.getenv("WOLF_PASS") or "") 
                page.click('#submitButton')
            except:
                page.fill("#usuario", os.getenv("WOLF_USER") or "")
                page.fill("#password", os.getenv("WOLF_PASS") or "")
                page.click("text=Entrar")

            page.wait_for_load_state("networkidle")
            print("🔓 Robot: Login completado.")

            # --- FORMULARIO ---
            url_form = "https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/#wolfWindowInFramePopupContainer"
            page.goto(url_form)
            
            # --- RELLENAR (Ejemplos básicos) ---
            if "Customer__NAME" in datos and datos["Customer__NAME"] != "PENDIENTE":
                page.fill("#Customer__NAME", str(datos["Customer__NAME"]))
            
            if "EnergyContract__NAME" in datos:
                page.fill("#EnergyContract__NAME", str(datos["EnergyContract__NAME"]))

            print("✅ Robot: Tarea finalizada. Cerrando en 60 segundos...")
            page.wait_for_timeout(60000) 
            browser.close()
            
    except Exception as e:
        print(f"❌ ERROR DENTRO DEL ROBOT: {e}")
        traceback.print_exc()

@app.post("/webhook-local")
async def recibir_contrato(request: Request, background_tasks: BackgroundTasks):
    try:
        datos_raw = await request.json()
        texto_para_ia = datos_raw.get("mensaje", str(datos_raw))
        print(f"📩 Datos recibidos. Consultando a Mistral...")

        # 1. IA analiza el texto (esto es rápido)
        resultado_ia_string = analizar_consulta_loviluz(texto_para_ia)
        limpio = resultado_ia_string.replace("```json", "").replace("```", "").strip()
        datos_ia = json.loads(limpio)
        
        print(f"🧠 IA generó mapeo: {datos_ia}")

        # 2. ENVIAR AL ROBOT COMO TAREA DE FONDO
        # Esto libera a FastAPI y permite que Playwright Sync funcione
        background_tasks.add_task(ejecutar_robot_sincrono, datos_ia)
        
        return {"status": "success", "message": "Robot en marcha"}

    except Exception as e:
        print("--- 🚨 ERROR EN WEBHOOK 🚨 ---")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
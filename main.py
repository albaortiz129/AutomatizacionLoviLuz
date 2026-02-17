import os
import json
import traceback
import uvicorn
import fitz  # PyMuPDF
from fastapi import FastAPI, BackgroundTasks, File, UploadFile, Form
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from cerebro import analizar_consulta_loviluz

load_dotenv()
app = FastAPI()

def rellenar_campo_ultra(target, selector, valor, clave_log):
    if not valor or str(valor).upper() in ["PENDIENTE", "NONE", "", "NULL"]:
        return False
    
    try:
        # Espera a que el elemento sea visible
        elemento = target.wait_for_selector(selector, timeout=5000, state="visible")
        tag = elemento.evaluate("el => el.tagName")
        clases = elemento.get_attribute("class") or ""

        # --- CASO 1: AUTOCOMPLETE (Cliente) ---
        if "ui-autocomplete-input" in clases:
            elemento.click()
            elemento.click(click_count=3) # Seleccionar todo
            target.keyboard.press("Backspace")
            elemento.press_sequentially(str(valor), delay=150)
            target.wait_for_timeout(2500) # Tiempo para que aparezca la lista
            
            target.keyboard.press("ArrowDown")
            target.wait_for_timeout(200)
            target.keyboard.press("Enter")
            print(f"⚡ {clave_log}: Autocompletado -> {valor}")
            return True

        # --- CASO 2: SELECT (Suministro, Alta, Provincia) ---
        elif tag == "SELECT":
            try:
                elemento.select_option(value=str(valor))
            except:
                target.evaluate(f"""
                    (sel, val) => {{
                        const el = document.querySelector(sel);
                        const opt = [...el.options].find(o => o.text.toUpperCase().includes(val.toUpperCase()) || o.value === val);
                        if (opt) {{ 
                            el.value = opt.value; 
                            el.dispatchEvent(new Event('change', {{ bubbles: true }})); 
                        }}
                    }}
                """, selector, str(valor))
            print(f"✅ {clave_log}: Seleccionado -> {valor}")

        # --- CASO 3: INPUTS ESTÁNDAR Y DNI ---
        else:
            elemento.fill(str(valor))
            target.evaluate(f"""
                const el = document.querySelector('{selector}');
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                el.dispatchEvent(new Event('blur', {{ bubbles: true }}));
            """)
            print(f"✅ {clave_log}: Escrito -> {valor}")
        
        return True
    except Exception:
        return False

def ejecutar_robot_sincrono(datos):
    print("🤖 Robot: Iniciando volcado integral...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False) 
            context = browser.new_context(viewport={'width': 1280, 'height': 800})
            page = context.new_page()
            
            # Login
            page.goto("https://loviluz.v3.wolfcrm.es/index.php", wait_until="domcontentloaded")
            page.fill("#userLogin", os.getenv("WOLF_USER") or "")
            page.fill("#userPassword", os.getenv("WOLF_PASS") or "")
            page.click('input[type="submit"]')
            
            # Navegar a creación
            page.goto("https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/", wait_until="networkidle")
            page.click("span.btn-creation")
            
            # Localizar el frame object.php
            target = page
            page.wait_for_timeout(4000) 
            for frame in page.frames:
                if "object.php" in frame.url:
                    target = frame
                    break

            # ORDEN DE LLENADO CRÍTICO
            mapeo = [
                ("#Customer__CODE", "Customer__CODE", "Código Cliente"),
                ("#EnergyContract__SUMINISTRO", "EnergyContract__SUMINISTRO", "Suministro"),
                ("#EnergyContract__CUPS_COUNTY", "EnergyContract__CUPS_COUNTY", "Provincia"),
                ("#EnergyContract__TIPO_ALTA", "EnergyContract__TIPO_ALTA", "Tipo Alta"),
                ("#EnergyContract__STATUS", "EnergyContract__STATUS", "Estado"),
                ("#EnergyContract__NAME", "EnergyContract__NAME", "CUPS"),
                ("#EnergyContract__FIRMANTE", "EnergyContract__FIRMANTE", "Firmante"),
                ("#EnergyContract__DNI_FIRMANTE", "EnergyContract__DNI_FIRMANTE", "DNI"),
                ("#EnergyContract__CUPS_ADDRESS", "EnergyContract__CUPS_ADDRESS", "Dirección"),
                ("#EnergyContract__CUPS_CITY", "EnergyContract__CUPS_CITY", "Ciudad"),
                ("#EnergyContract__CUPS_POSTAL_CODE", "EnergyContract__CUPS_POSTAL_CODE", "CP"),
                ("#EnergyContract__IBAN", "EnergyContract__IBAN", "IBAN"),
                ("#EnergyContract__CNAE", "EnergyContract__CNAE", "CNAE"),
                ("#EnergyContract__TARIFA", "EnergyContract__TARIFA", "Tarifa")
            ]

            for selector, clave, log in mapeo:
                valor = datos.get(clave)
                if rellenar_campo_ultra(target, selector, valor, log):
                    if clave in ["Customer__CODE", "EnergyContract__SUMINISTRO", "EnergyContract__CUPS_COUNTY"]:
                        page.wait_for_timeout(2000)
            
            print("🏁 Robot: Volcado terminado. Tienes 5 minutos para revisar antes del cierre.")
            
            # PAUSA DE 5 MINUTOS (300.000 milisegundos)
            page.wait_for_timeout(300000) 
            
            browser.close()
    except Exception as e:
        print(f"❌ ERROR ROBOT: {e}")
        traceback.print_exc()

@app.post("/webhook-local")
async def recibir_contrato(
    background_tasks: BackgroundTasks,
    mensaje: str = Form(...), 
    archivo_pdf: UploadFile = File(None) 
):
    try:
        texto_unificado = f"MENSAJE: {mensaje}\n"
        if archivo_pdf:
            pdf_content = await archivo_pdf.read()
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            texto_pdf = " ".join([pag.get_text() for pag in doc])
            texto_unificado += f"PDF: {texto_pdf}"

        datos_ia = json.loads(analizar_consulta_loviluz(texto_unificado))
        print(f"🧠 Datos extraídos: {json.dumps(datos_ia, indent=2)}")
        
        background_tasks.add_task(ejecutar_robot_sincrono, datos_ia)
        return {"status": "success", "datos": datos_ia}
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8005)
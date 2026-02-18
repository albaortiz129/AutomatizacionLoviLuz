import os
import re
import unicodedata
import traceback
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN DE ESTADOS ---
MAPEO_ESTADOS = {
    "PENDIENTE FIRMA": "159",
    "PENDIENTE FIRMA PAPEL": "189",
    "PENDIENTE DE VALIDACION": "202",
    "VALIDADO": "202",
    "TRAMITE": "202",
    "CONTRATO": "161"
}

TEXTO_WOLF_POR_ID = {
    "159": "PENDIENTE FIRMA",
    "189": "PENDIENTE FIRMA MANUAL",
    "202": "VALIDADO",
    "161": "EN TRAMITE"
}

def normalizar(texto):
    if not texto: return ""
    texto = texto.upper().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def calcular_vencimiento(fecha_str):
    try:
        fecha_dt = datetime.strptime(fecha_str, "%d/%m/%Y")
        fecha_vencimiento = fecha_dt.replace(year=fecha_dt.year + 1)
        return fecha_vencimiento.strftime("%d/%m/%Y")
    except Exception as e:
        print(f"❌ Error al calcular fecha: {e}")
        return None

def sincronizar():
    with sync_playwright() as p:
        # He quitado un poco de slow_mo para que no sea eterno, ya que tú validarás al final
        browser = p.chromium.launch(headless=False, slow_mo=200)
        context = browser.new_context(viewport={'width': 1366, 'height': 768})
        
        page_wolf = context.new_page()
        page_ignis = context.new_page()

        try:
            # --- 1. LOGIN IGNIS ---
            print("🔑 Accediendo a Ignis...")
            page_ignis.goto("https://agentes.ignisluz.es/#/login")
            page_ignis.click("md-select[name='empresaLogin']")
            page_ignis.click("md-option:has-text('LOOP ELECTRICIDAD Y GAS')")
            page_ignis.fill("input[name='usuario']", os.getenv("IGNIS_USER") or "")
            page_ignis.fill("input[name='password']", os.getenv("IGNIS_PASS") or "")
            page_ignis.click("button:has-text('Entrar')")
            page_ignis.wait_for_timeout(3000)
            page_ignis.goto("https://agentes.ignisluz.es/#/contratos")
            page_ignis.wait_for_selector('.ui-grid-render-container-body')

            # --- 2. LOGIN WOLF ---
            print("🔑 Accediendo a Wolf CRM...")
            page_wolf.goto("https://loviluz.v3.wolfcrm.es/index.php")
            page_wolf.fill("#userLogin", os.getenv("WOLF_USER") or "")
            page_wolf.fill("#userPassword", os.getenv("WOLF_PASS") or "")
            page_wolf.click('input[type="submit"]')
            
            url_filtros = "https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/index.php?Q_COMERCIALIZADORA[]=IGNIS_ENERGIA&Q_STATUS[]=159&Q_STATUS[]=189&Q_STATUS[]=202&Q_STATUS[]=161"
            page_wolf.goto(url_filtros)
            page_wolf.wait_for_selector("select#dt-length-0")
            page_wolf.select_option("select#dt-length-0", value="500")
            page_wolf.wait_for_timeout(4000)

            # --- 3. PROCESO ---
            filas_wolf = page_wolf.locator("table.data-table tbody tr").all()

            for fila in filas_wolf:
                cups = "S/N"
                try:
                    texto_fila = fila.inner_text()
                    match_cups = re.search(r'ES00[A-Z0-9]{16,18}', texto_fila.upper())
                    if not match_cups: continue
                    cups = match_cups.group(0)
                    
                    estado_wolf_txt = "DESCONOCIDO"
                    for id_w, txt_w in TEXTO_WOLF_POR_ID.items():
                        if normalizar(txt_w) in normalizar(texto_fila):
                            estado_wolf_txt = txt_w
                            break

                    # --- BUSQUEDA EN IGNIS ---
                    page_ignis.bring_to_front()
                    page_ignis.evaluate("document.querySelector('.ui-grid-render-container-body .ui-grid-viewport').scrollLeft = 0")
                    page_ignis.wait_for_timeout(500)

                    encontrado_input = False
                    for desplazamiento in range(0, 4500, 600):
                        page_ignis.evaluate(f"document.querySelector('.ui-grid-render-container-body .ui-grid-viewport').scrollLeft = {desplazamiento}")
                        input_cups = page_ignis.locator('input[placeholder="Cups..."]')
                        if input_cups.count() > 0 and input_cups.is_visible():
                            input_cups.click(click_count=3)
                            page_ignis.keyboard.press("Control+A")
                            page_ignis.keyboard.press("Backspace")
                            input_cups.fill(cups)
                            page_ignis.keyboard.press("Enter")
                            encontrado_input = True
                            break
                        page_ignis.wait_for_timeout(100)
                    
                    if not encontrado_input: continue

                    page_ignis.locator("button.aplicarFiltros").first.click()
                    page_ignis.wait_for_timeout(2500)
                    fila_target = page_ignis.locator(f".ui-grid-row:has-text('{cups}')").first
                    
                    try:
                        fila_target.wait_for(state="visible", timeout=10000)
                        texto_ignis = fila_target.inner_text()
                        
                        match_fecha = re.search(r'(\d{2}/\d{2}/\d{4})', texto_ignis)
                        fecha_alta_ignis = match_fecha.group(1) if match_fecha else None
                        
                        nombre_estado_ignis = next((k for k in MAPEO_ESTADOS if normalizar(k) in normalizar(texto_ignis)), None)
                        
                        if nombre_estado_ignis:
                            id_objetivo = MAPEO_ESTADOS[nombre_estado_ignis]
                            texto_objetivo_wolf = TEXTO_WOLF_POR_ID.get(id_objetivo, "CONTRATO")

                            # Cambiamos si el estado es distinto O si es CONTRATO (para validar fechas)
                            if normalizar(estado_wolf_txt) != normalizar(texto_objetivo_wolf) or normalizar(nombre_estado_ignis) == "CONTRATO":
                                print(f"👀 Preparando {cups} para revisión...")
                                page_wolf.bring_to_front()
                                
                                lupa = fila.locator("span.edit-icon, i.fa-search-plus").first
                                lupa.evaluate("el => el.click()")

                                frame = page_wolf.frame_locator("#wolfWindowInFrameFrame")
                                selector_status = frame.locator("select#EnergyContract__STATUS")
                                selector_status.wait_for(state="visible", timeout=12000)
                                
                                # 1. Cambiar Estado
                                selector_status.select_option(value=id_objetivo)
                                selector_status.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")

                                # 2. Lógica de Fechas
                                if nombre_estado_ignis == "CONTRATO" and fecha_alta_ignis:
                                    fecha_venc = calcular_vencimiento(fecha_alta_ignis)
                                    
                                    input_alta = frame.locator("#EnergyContract__START_DATE")
                                    input_alta.fill(fecha_alta_ignis)
                                    
                                    if fecha_venc:
                                        input_venc = frame.locator("#EnergyContract__DUE_DATE")
                                        input_venc.fill(fecha_venc)
                                
                                # --- MODIFICACIÓN AQUÍ: NO GUARDA ---
                                print(f"⚠️ DATOS RELLENADOS PARA {cups}. Por favor, revisa Wolf y dale a Guardar si es correcto.")
                                print("Siguiente contrato en 10 segundos o cuando cierres el modal...")
                                
                                # Esperamos a que tú hagas algo o pasen unos segundos para que te dé tiempo
                                page_wolf.bring_to_front()
                                # Esta espera es para que no salte al siguiente Cups inmediatamente
                                page_wolf.wait_for_timeout(8000) 
                                
                        else:
                            print(f"👌 {cups} parece estar correcto.")
                            
                    except Exception as e:
                        print(f"⚠️ Error al procesar fila de {cups}: {e}")

                except Exception as e:
                    print(f"⚠️ Error general: {e}")
                    page_wolf.keyboard.press("Escape")

        except Exception as e:
            traceback.print_exc()
        finally:
            print("\n🏁 Proceso detenido para revisión manual.")

if __name__ == "__main__":
    sincronizar()
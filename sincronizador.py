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

def escribir_log(mensaje):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{timestamp}] {mensaje}"
    print(linea)
    with open("historial_sincronizacion.txt", "a", encoding="utf-8") as f:
        f.write(linea + "\n")

def normalizar(texto):
    if not texto: return ""
    texto = texto.upper().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def calcular_vencimiento(fecha_str):
    try:
        fecha_str = re.search(r'\d{2}/\d{2}/\d{4}', fecha_str).group(0)
        fecha_dt = datetime.strptime(fecha_str, "%d/%m/%Y")
        fecha_vencimiento = fecha_dt.replace(year=fecha_dt.year + 1)
        return fecha_vencimiento.strftime("%d/%m/%Y")
    except: return None

def sincronizar():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=150)
        context = browser.new_context(viewport={'width': 1366, 'height': 768})
        page_wolf = context.new_page()
        page_ignis = context.new_page()

        try:
            # --- LOGINS ---
            escribir_log("🔑 Accediendo a Ignis...")
            page_ignis.goto("https://agentes.ignisluz.es/#/login")
            page_ignis.click("md-select[name='empresaLogin']")
            page_ignis.click("md-option:has-text('LOOP ELECTRICIDAD Y GAS')")
            page_ignis.fill("input[name='usuario']", os.getenv("IGNIS_USER") or "")
            page_ignis.fill("input[name='password']", os.getenv("IGNIS_PASS") or "")
            page_ignis.click("button:has-text('Entrar')")
            page_ignis.wait_for_timeout(3000)
            page_ignis.goto("https://agentes.ignisluz.es/#/contratos")
            
            escribir_log("🔑 Accediendo a Wolf CRM...")
            page_wolf.goto("https://loviluz.v3.wolfcrm.es/index.php")
            page_wolf.fill("#userLogin", os.getenv("WOLF_USER") or "")
            page_wolf.fill("#userPassword", os.getenv("WOLF_PASS") or "")
            page_wolf.click('input[type="submit"]')
            
            url_filtros = "https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/index.php?Q_COMERCIALIZADORA[]=IGNIS_ENERGIA&Q_STATUS[]=159&Q_STATUS[]=189&Q_STATUS[]=202&Q_STATUS[]=161"
            page_wolf.goto(url_filtros)
            page_wolf.wait_for_selector("select#dt-length-0")
            page_wolf.select_option("select#dt-length-0", value="500")
            page_wolf.wait_for_timeout(4000)

            filas_wolf = page_wolf.locator("table.data-table tbody tr").all()

            for fila in filas_wolf:
                cups = "S/N"
                try:
                    texto_fila = fila.inner_text()
                    match_cups = re.search(r'ES00[A-Z0-9]{16,18}', texto_fila.upper())
                    if not match_cups: continue
                    cups = match_cups.group(0)
                    
                    # --- ACCIÓN EN IGNIS ---
                    page_ignis.bring_to_front()
                    
                    # 💡 Esperar a que la tabla de Ignis no esté cargando
                    escribir_log(f"⏳ Esperando carga para {cups}...")
                    page_ignis.wait_for_selector(".ui-grid-render-container-body", state="visible")

                    # RESET SCROLL para buscar buscador
                    page_ignis.evaluate("document.querySelector('.ui-grid-render-container-body .ui-grid-viewport').scrollLeft = 0")
                    page_ignis.wait_for_timeout(800)

                    encontrado_input = False
                    for d in [0, 800, 1600, 2400, 3200]:
                        page_ignis.evaluate(f"document.querySelector('.ui-grid-render-container-body .ui-grid-viewport').scrollLeft = {d}")
                        page_ignis.wait_for_timeout(400) # Espera renderizado
                        
                        input_cups = page_ignis.locator('input[placeholder="Cups..."]')
                        if input_cups.count() > 0 and input_cups.is_visible():
                            input_cups.click(click_count=3)
                            page_ignis.keyboard.press("Control+A")
                            page_ignis.keyboard.press("Backspace")
                            input_cups.fill(cups)
                            page_ignis.keyboard.press("Enter")
                            encontrado_input = True
                            break
                    
                    if not encontrado_input:
                        escribir_log(f"⚠️ No se encontró el buscador para {cups}")
                        continue

                    # Clic en Aplicar y ESPERAR RESULTADOS
                    page_ignis.locator("button.aplicarFiltros").first.click()
                    
                    # 💡 ESPERA CLAVE: Esperar a que la fila con el CUPS específico aparezca
                    # Esto evita que el bot lea la fila del CUPS anterior
                    fila_target = page_ignis.locator(f".ui-grid-row:has-text('{cups}')").first
                    try:
                        fila_target.wait_for(state="visible", timeout=8000)
                    except:
                        escribir_log(f"ℹ️ {cups} no aparece en Ignis tras filtrar (posiblemente no existe)")
                        continue

                    # BUSCAR FECHA CON SCROLL
                    fecha_alta_ignis = None
                    for d in range(0, 5000, 800):
                        page_ignis.evaluate(f"document.querySelector('.ui-grid-render-container-body .ui-grid-viewport').scrollLeft = {d}")
                        page_ignis.wait_for_timeout(400)
                        
                        columna = page_ignis.locator(".ui-grid-header-cell").filter(has_text=re.compile(r"F\. Alta|Fecha Alta", re.I)).first
                        if columna.count() > 0:
                            idx = columna.evaluate("el => Array.from(el.parentNode.children).indexOf(el)")
                            fecha_alta_ignis = fila_target.locator(".ui-grid-cell").nth(idx).inner_text().strip()
                            if re.search(r'\d{2}/\d{2}/\d{4}', fecha_alta_ignis): break

                    nombre_estado = next((k for k in MAPEO_ESTADOS if normalizar(k) in normalizar(fila_target.inner_text())), None)
                    
                    if nombre_estado:
                        # --- ACTUALIZAR WOLF ---
                        page_wolf.bring_to_front()
                        fila.locator("span.edit-icon, i.fa-search-plus").first.click()

                        frame = page_wolf.frame_locator("#wolfWindowInFrameFrame")
                        selector_status = frame.locator("select#EnergyContract__STATUS")
                        selector_status.wait_for(state="visible", timeout=10000)
                        
                        selector_status.select_option(value=MAPEO_ESTADOS[nombre_estado])
                        selector_status.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")

                        if nombre_estado == "CONTRATO" and fecha_alta_ignis:
                            venc = calcular_vencimiento(fecha_alta_ignis)
                            frame.locator("#EnergyContract__START_DATE").fill(fecha_alta_ignis)
                            if venc: frame.locator("#EnergyContract__DUE_DATE").fill(venc)
                        
                        escribir_log(f"💾 Guardando {cups}...")
                        frame.locator(".save-object-btn").first.click()
                        
                        # Esperar a que Wolf procese y cierre el modal
                        page_wolf.locator("#wolfWindowInFrame").wait_for(state="hidden", timeout=15000)
                        escribir_log(f"✅ {cups}: Sincronizado")

                except Exception as e:
                    escribir_log(f"⚠️ Error en {cups}: {e}")
                    try: page_wolf.keyboard.press("Escape")
                    except: pass

        except Exception as e:
            escribir_log(f"🔴 ERROR CRÍTICO: {traceback.format_exc()}")
        finally:
            escribir_log("--- FIN DEL PROCESO ---")
            browser.close()

if __name__ == "__main__":
    sincronizar()
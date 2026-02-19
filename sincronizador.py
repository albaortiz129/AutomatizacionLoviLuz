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
# Estados que consideramos iguales para no perder tiempo editando
EQUIVALENTES = ["VALIDADO", "TRAMITE", "PENDIENTE DE VALIDACION"]

def escribir_log(mensaje, tipo="INFO"):
    """
    Muestra el log en consola y guarda en un .txt.
    Tipos: INFO, OK, ADVERTENCIA, ERROR, SISTEMA
    """
    carpeta_logs = "LOGS"
    if not os.path.exists(carpeta_logs):
        os.makedirs(carpeta_logs)
    
    ahora = datetime.now()
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    timestamp = ahora.strftime("%Y-%m-%d %H:%M:%S")
    
    iconos = {
        "INFO": "🔹",
        "OK": "✅",
        "ADVERTENCIA": "⚠️",
        "ERROR": "❌",
        "SISTEMA": "⚙️"
    }
    
    icono = iconos.get(tipo, "🔹")
    nombre_archivo = os.path.join(carpeta_logs, f"registro_{fecha_hoy}.txt")
    linea = f"[{timestamp}] {icono} {mensaje}"
    
    print(linea)
    with open(nombre_archivo, "a", encoding="utf-8") as f:
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

        escribir_log("="*60, "SISTEMA")
        escribir_log("EMPEZANDO A REVISAR CONTRATOS", "SISTEMA")
        escribir_log("="*60, "SISTEMA")

        try:
            # --- 1. LOGIN IGNIS ---
            escribir_log("Entrando en Ignis Energía...", "INFO")
            page_ignis.goto("https://agentes.ignisluz.es/#/login")
            page_ignis.click("md-select[name='empresaLogin']")
            page_ignis.click("md-option:has-text('LOOP ELECTRICIDAD Y GAS')")
            page_ignis.fill("input[name='usuario']", os.getenv("IGNIS_USER") or "")
            page_ignis.fill("input[name='password']", os.getenv("IGNIS_PASS") or "")
            page_ignis.click("button:has-text('Entrar')")
            page_ignis.wait_for_timeout(3000)
            page_ignis.goto("https://agentes.ignisluz.es/#/contratos")
            
            # --- 2. LOGIN WOLF ---
            escribir_log("Entrando en Wolf CRM...", "INFO")
            page_wolf.goto("https://loviluz.v3.wolfcrm.es/index.php")
            page_wolf.fill("#userLogin", os.getenv("WOLF_USER") or "")
            page_wolf.fill("#userPassword", os.getenv("WOLF_PASS") or "")
            page_wolf.click('input[type="submit"]')
            
            escribir_log("Buscando contratos en Wolf...", "INFO")
            # 💡 AQUÍ ESTÁ EL CAMBIO: Se ha quitado &Q_STATUS[]=161 de la URL
            url_wolf = "https://loviluz.v3.wolfcrm.es/custom/energymodule/energy-contracts/index.php?Q_COMERCIALIZADORA[]=IGNIS_ENERGIA&Q_STATUS[]=159&Q_STATUS[]=189&Q_STATUS[]=202"
            
            page_wolf.goto(url_wolf)
            page_wolf.wait_for_selector("select#dt-length-0")
            page_wolf.select_option("select#dt-length-0", value="500")
            page_wolf.wait_for_timeout(4000)

            filas_wolf = page_wolf.locator("table.data-table tbody tr").all()
            escribir_log(f"Tengo {len(filas_wolf)} contratos para mirar hoy.", "SISTEMA")

            # 💡 CONTADOR PARA LIMPIEZA CADA 50
            contador_cups = 0

            page_ignis.bring_to_front()
            page_ignis.wait_for_selector(".ui-grid-render-container-body", state="visible")
            page_ignis.wait_for_timeout(5000) 

            for fila in filas_wolf:
                contador_cups += 1
                
                # REFUERZO: Limpiar memoria cada 50 contratos
                if contador_cups % 50 == 0:
                    escribir_log(f"Llevo {contador_cups} contratos. Limpiando memoria de Ignis...", "SISTEMA")
                    page_ignis.bring_to_front()
                    page_ignis.reload()
                    page_ignis.wait_for_timeout(5000)

                cups = "S/N"
                try:
                    texto_fila_wolf = fila.inner_text().upper()
                    estado_en_wolf = next((k for k in MAPEO_ESTADOS if normalizar(k) in normalizar(texto_fila_wolf)), "DESCONOCIDO")
                    
                    match_cups = re.search(r'ES00[A-Z0-9]{16,18}', texto_fila_wolf)
                    if not match_cups: continue
                    cups = match_cups.group(0)
                    
                    # --- ACCIÓN EN IGNIS ---
                    page_ignis.bring_to_front()
                    page_ignis.evaluate("document.querySelector('.ui-grid-render-container-body .ui-grid-viewport').scrollLeft = 0")
                    page_ignis.wait_for_timeout(600)

                    encontrado_input = False
                    for d in [0, 800, 1600, 2400, 3200]:
                        page_ignis.evaluate(f"document.querySelector('.ui-grid-render-container-body .ui-grid-viewport').scrollLeft = {d}")
                        page_ignis.wait_for_timeout(300)
                        input_cups = page_ignis.locator('input[placeholder="Cups..."]')
                        if input_cups.count() > 0 and input_cups.is_visible():
                            input_cups.click(click_count=3)
                            page_ignis.keyboard.press("Backspace")
                            input_cups.fill(cups)
                            page_ignis.keyboard.press("Enter")
                            encontrado_input = True
                            break
                    
                    if not encontrado_input:
                        escribir_log(f"CUPS {cups}: No encuentro buscador.", "ADVERTENCIA")
                        continue

                    page_ignis.locator("button.aplicarFiltros").first.click()
                    fila_target = page_ignis.locator(f".ui-grid-row:has-text('{cups}')").first
                    
                    try:
                        fila_target.wait_for(state="visible", timeout=12000)
                    except:
                        escribir_log(f"CUPS {cups}: No aparece en Ignis.", "ADVERTENCIA")
                        continue

                    estado_en_ignis = next((k for k in MAPEO_ESTADOS if normalizar(k) in normalizar(fila_target.inner_text())), "OTRO")

                    # LÓGICA EQUIVALENTES
                    mismo_nombre = normalizar(estado_en_wolf) == normalizar(estado_en_ignis)
                    ambos_son_tramite = estado_en_wolf in EQUIVALENTES and estado_en_ignis in EQUIVALENTES

                    if (mismo_nombre or ambos_son_tramite) and estado_en_ignis != "CONTRATO":
                        escribir_log(f"CUPS {cups} | Wolf: {estado_en_wolf} | Ignis: {estado_en_ignis} | Resultado: Sin cambios.")
                        page_ignis.wait_for_timeout(2000)
                        continue

                    if estado_en_ignis == "OTRO":
                        escribir_log(f"CUPS {cups} | Wolf: {estado_en_wolf} | Ignis: {estado_en_ignis} | Resultado: Estado no válido para modificar.")
                        page_ignis.wait_for_timeout(2000)
                        continue

                    # --- CAMBIAR EN WOLF ---
                    fecha_alta_ignis = None
                    if estado_en_ignis == "CONTRATO":
                        for d in range(0, 5000, 800):
                            page_ignis.evaluate(f"document.querySelector('.ui-grid-render-container-body .ui-grid-viewport').scrollLeft = {d}")
                            page_ignis.wait_for_timeout(300)
                            columna = page_ignis.locator(".ui-grid-header-cell").filter(has_text=re.compile(r"F\. Alta|Fecha Alta", re.I)).first
                            if columna.count() > 0:
                                idx = columna.evaluate("el => Array.from(el.parentNode.children).indexOf(el)")
                                fecha_alta_ignis = fila_target.locator(".ui-grid-cell").nth(idx).inner_text().strip()
                                if re.search(r'\d{2}/\d{2}/\d{4}', fecha_alta_ignis): break

                    page_wolf.bring_to_front()
                    fila.locator("span.edit-icon, i.fa-search-plus").first.click()

                    frame = page_wolf.frame_locator("#wolfWindowInFrameFrame")
                    selector_status = frame.locator("select#EnergyContract__STATUS")
                    selector_status.wait_for(state="visible", timeout=12000)
                    
                    selector_status.select_option(value=MAPEO_ESTADOS[estado_en_ignis])
                    selector_status.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")

                    # FLECHITA ➔
                    detalles_registro = f"CUPS {cups} | Wolf: {estado_en_wolf} ➔ Ignis: {estado_en_ignis}"
                    
                    if estado_en_ignis == "CONTRATO" and fecha_alta_ignis:
                        venc = calcular_vencimiento(fecha_alta_ignis)
                        frame.locator("#EnergyContract__START_DATE").fill(fecha_alta_ignis)
                        if venc: 
                            frame.locator("#EnergyContract__DUE_DATE").fill(venc)
                            detalles_registro += f" | Alta: {fecha_alta_ignis} y Vencimiento: {venc}"
                    
                    frame.locator(".save-object-btn").first.click()
                    page_wolf.locator("#wolfWindowInFrame").wait_for(state="hidden", timeout=12000)
                    
                    escribir_log(detalles_registro, "OK")
                    page_ignis.wait_for_timeout(4000)

                except Exception as e:
                    escribir_log(f"Error con el CUPS {cups}: algo ha fallado.", "ERROR")
                    try: page_wolf.keyboard.press("Escape")
                    except: pass

        except Exception as e:
            escribir_log("¡ERROR GORDO! El programa se ha parado.", "ERROR")
            print(traceback.format_exc())
        finally:
            escribir_log("="*60, "SISTEMA")
            escribir_log("COMPROBACIÓN FINALIZADA")
            escribir_log("="*60, "SISTEMA")
            browser.close()

if __name__ == "__main__":
    sincronizar()